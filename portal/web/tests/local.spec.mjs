// Copyright (c) Microsoft. All rights reserved.
// Browser -> production Foundry-only portal -> test-only Azure service fixture.
import { test, expect } from "@playwright/test";
import { openTemplatePicker } from "./template-picker-helpers.mjs";
import { deterministicYaml, PIPELINE_COMPONENTS, PIPELINE_METRICS_DISCLAIMER } from "../../static/handoff/handoff-core.mjs";

test.beforeEach(async ({ page }) => {
  // Exercise normal microphone startup with Playwright's synthetic device.
  await page.addInitScript(() => {
    window.microphoneCalls = 0;
    const getUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async (...args) => {
      window.microphoneCalls += 1;
      return getUserMedia(...args);
    };
  });
  await page.route("**/*", (route) => {
    const url = new URL(route.request().url());
    return url.hostname === "127.0.0.1" ? route.continue() : route.abort();
  });
});

async function readEditorDefinition(page) {
  const editorOpen = await page.locator("#node-editor").isVisible();
  await page.locator(editorOpen ? "#node-editor [data-agent-yaml]" : "#view-agent-yaml").click();
  await page.getByRole("tab", { name: "JSON", exact: true }).click();
  const definition = JSON.parse(await page.locator("#definition-output").innerText());
  await page.getByRole("button", { name: "Close definition drawer", exact: true }).click();
  return definition;
}

for (const failure of ["permission", "network", "malformed"]) {
  test(`optional voice discovery ${failure} failure leaves Editor and full default voices usable`, async ({ page }) => {
    await page.route("**/api/voices*", (route) => failure === "network" ? route.abort("failed") : route.fulfill({
      status: failure === "permission" ? 403 : 200,
      contentType: "application/json",
      body: JSON.stringify(failure === "permission"
        ? { error: "Speech discovery permission denied", request_id: "voice-fixture-request" }
        : { voices: [] }),
    }));
    await page.goto("/editor/");
    await expect(page.locator("#agent-load-state")).toHaveText(/^\d+ loaded$/, { timeout: 5000 });
    const status = page.getByRole("status", { name: "Voice catalog status", exact: true });
    await expect(status).toContainText("Live discovery is unavailable");
    await page.getByRole("button", { name: "Create blank", exact: true }).click();
    await page.locator("#node-outline button").first().click();
    await page.locator('[data-node-component="voice"]').click();
    await page.locator("#component-voice-locale").fill("hi-IN");
    await expect(page.locator('[data-component-value="diya"]')).toBeEnabled();
    await page.locator("#component-voice-search").fill("Swara");
    await page.locator('[data-component-value="hi-IN-SwaraNeural"]').click();
    await expect(page.locator('[data-component-value="hi-IN-SwaraNeural"]')).toHaveAttribute("aria-pressed", "true");
    await page.getByRole("button", { name: "Close component configuration", exact: true }).click();
    await page.getByRole("button", { name: "Save node", exact: true }).click();
    await page.unroute("**/api/voices*");
    await page.getByRole("button", { name: "Retry live voice discovery", exact: true }).click();
    await expect(status).toBeHidden();
    await page.locator("#node-outline button").first().click();
    await page.locator('[data-node-component="voice"]').click();
    await expect(page.locator('[data-component-value="hi-IN-SwaraNeural"]')).toHaveAttribute("aria-pressed", "true");
  });
}

test("pending optional voice discovery cannot delay Editor startup or discard an edited voice", async ({ page }) => {
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  await page.route("**/api/voices*", async (route) => {
    const response = await route.fetch();
    await gate;
    await route.fulfill({ response });
  });
  try {
    await page.goto("/editor/");
    await expect(page.locator("#agent-load-state")).toHaveText(/^\d+ loaded$/, { timeout: 5000 });
    await expect(page.locator("#voice-catalog-status")).toContainText("Checking optional live discovery");
    await page.getByRole("button", { name: "Create blank", exact: true }).click();
    await page.locator("#node-outline button").first().click();
    await page.locator('[data-node-component="voice"]').click();
    await page.locator("#component-voice-search").fill("Swara");
    await page.locator('[data-component-value="hi-IN-SwaraNeural"]').click();
    await page.locator("#component-voice-search").focus();
    release();
    await expect(page.locator("#voice-catalog-status")).toBeHidden();
    await expect(page.locator("#component-voice-search")).toHaveValue("Swara");
    await expect(page.locator("#component-voice-search")).toBeFocused();
    await expect(page.locator('[data-component-value="hi-IN-SwaraNeural"]')).toHaveAttribute("aria-pressed", "true");
  } finally {
    release();
  }
});

test("View Agent YAML opens the complete read-only working copy and always selects YAML", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/editor/");
  await expect(page.locator("#view-agent-yaml")).toBeDisabled();
  await expect(page.locator("#global-settings-action")).toBeDisabled();
  await openTemplatePicker(page);
  await page.locator('[data-template-id="customer-support-example"]').click();
  await expect(page.locator("#template-picker")).toBeHidden();
  const definition = await readEditorDefinition(page);
  expect(definition.handoff.nodes.length).toBeGreaterThan(0);
  expect(definition.handoff.edges.length).toBeGreaterThan(0);
  const dirtyState = await page.locator("#dirty-badge").innerText();
  await page.locator("#view-agent-yaml").click();
  await expect(page.getByRole("dialog", { name: "Entire Agent definition", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "YAML", exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page.locator("#definition-output")).toHaveText(deterministicYaml(definition));
  await expect(page.locator("#definition-output")).not.toHaveAttribute("contenteditable", "true");
  await page.keyboard.press("Escape");
  await expect(page.locator("#definition-drawer")).toBeHidden();
  await expect(page.locator("#view-agent-yaml")).toBeFocused();
  await expect(page.locator("#dirty-badge")).toHaveText(dirtyState);
  expect(errors).toEqual([]);
});

test("Global settings saves shared fields without changing nodes and supports one-step Undo", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/editor/");
  await openTemplatePicker(page);
  await page.locator('[data-template-id="customer-support-example"]').click();
  await expect(page.locator("#template-picker")).toBeHidden();
  const before = await readEditorDefinition(page);
  await page.locator("#global-settings-action").click();
  await expect(page.locator("#node-editor-title")).toHaveText("Agent General Settings");
  await expect(page.locator(".node-editor-form")).toHaveCount(0);
  await expect(page.locator("#delete-node-editor")).toBeHidden();
  const silence = page.getByLabel("Silence duration", { exact: true });
  await silence.fill("400");
  await silence.press("Tab");
  await page.getByLabel("Greeting mode", { exact: true }).selectOption("template");
  const greeting = page.getByLabel("Greeting text", { exact: true });
  await greeting.fill("Hello from the Agent-wide greeting.");
  await greeting.press("Tab");
  await page.getByRole("button", { name: "Save Agent General Settings", exact: true }).click();
  await expect(page.locator("#node-editor")).toBeHidden();
  const after = await readEditorDefinition(page);
  expect(after.audio.input.turn_detection).toEqual({
    ...before.audio.input.turn_detection, silence_duration_ms: 400,
  });
  expect(after.greeting.text).toBe("Hello from the Agent-wide greeting.");
  expect(after.handoff).toEqual(before.handoff);
  expect(after.instructions).toBe(before.instructions);
  expect(after.tools).toEqual(before.tools);
  expect(after.model).toBe(before.model);
  await page.locator("#undo-action").click();
  expect(await readEditorDefinition(page)).toEqual(before);
  await page.locator("#redo-action").click();
  expect(await readEditorDefinition(page)).toEqual(after);
  expect(errors).toEqual([]);
});

test("Global settings is discoverable from a specialist and YAML preview does not save edits", async ({ page }) => {
  await page.goto("/editor/");
  await openTemplatePicker(page);
  await page.locator('[data-template-id="customer-support-example"]').click();
  await expect(page.locator("#template-picker")).toBeHidden();
  const before = await readEditorDefinition(page);
  await page.locator("#node-outline button").nth(1).click();
  await page.locator("#node-global-settings").click();
  await expect(page.locator("#node-editor-title")).toHaveText("Agent General Settings");
  const silence = page.getByLabel("Silence duration", { exact: true });
  await silence.fill("1234");
  await silence.press("Tab");
  await page.locator("#node-editor [data-agent-yaml]").click();
  await expect(page.locator("#definition-output")).toContainText("silence_duration_ms: 1234");
  await page.keyboard.press("Escape");
  await expect(page.locator("#definition-drawer")).toBeHidden();
  await expect(page.locator("#node-editor")).toBeVisible();
  await expect(silence).toHaveValue("1234");
  await page.keyboard.press("Escape");
  await expect(page.locator("#node-editor")).toBeHidden();
  expect(await readEditorDefinition(page)).toEqual(before);
});

for (const width of [1440, 768, 390, 320]) {
  test(`Global settings and Agent YAML are accessible at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/editor/");
    await expect(page.locator(".primary-actions #global-settings-action, .primary-actions #view-agent-yaml")).toHaveCount(0);
    await expect(page.locator("#export-action")).toHaveCount(0);
    await expect(page.locator(".canvas-meta #global-settings-action")).toHaveText("Agent General Settings");
    await expect(page.locator(".canvas-meta #view-agent-yaml")).toHaveText("YAML");
    await page.getByRole("button", { name: "Create blank", exact: true }).click();
    for (const id of ["#global-settings-action", "#view-agent-yaml"]) {
      await expect(page.locator(id)).toBeVisible();
      const bounds = await page.locator(id).boundingBox();
      expect(bounds.x).toBeGreaterThanOrEqual(0);
      expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
    }
    await page.locator("#global-settings-action").focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "Agent General Settings", exact: true })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Input language", exact: true })).toBeVisible();
    const body = page.locator("#node-editor-body");
    expect(await body.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
    await page.locator("#node-editor [data-agent-yaml]").click();
    await expect(page.locator("#definition-output")).toContainText('kind: "voice"');
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: "Save Agent General Settings", exact: true }).click();
    await page.locator("#node-outline button").first().click();
    await expect(page.locator("#node-editor-title")).toHaveText("Start node");
    await expect(page.getByRole("button", { name: "Save node", exact: true })).toBeVisible();
  });
}

test("Editor defaults input language to Auto and clearing a locale omits it", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/editor/");
  await openTemplatePicker(page);
  await page.locator('[data-template-id="customer-support-example"]').click();
  await expect(page.locator("#template-picker")).toBeHidden();
  await page.locator("#node-outline button").first().click();
  const language = page.getByLabel("Input language", { exact: true });
  await expect(language).toHaveValue("Auto");
  await expect(page.locator("#node-editor-body")).toContainText("For more accurate recognition");
  await page.locator('[data-node-component="stt"]').click();
  await page.locator('[data-component-value="azure-speech"]').click();
  await page.getByRole("button", { name: "Open global input language", exact: true }).click();
  await expect(page.locator("#component-stt-languages [role='option']")).toHaveCount(16);
  await language.fill("not-a-language");
  await language.press("Enter");
  await expect(language).toHaveAttribute("aria-invalid", "true");
  await language.fill("Hindi");
  await language.press("Enter");
  await expect(language).toHaveValue("hi-IN");
  await language.fill("Auto");
  await language.press("Enter");
  await page.getByRole("button", { name: "Save Agent General Settings", exact: true }).click();
  await page.locator("#view-agent-yaml").click();
  expect(await page.locator("#definition-output").innerText()).not.toContain("language:");
  expect(errors).toEqual([]);
});

test("Editor preserves a template input language and its candidate order", async ({ page }) => {
  await page.route("**/api/templates/customer-support-example?*", async (route) => {
    const response = await route.fetch();
    const detail = await response.json();
    detail.definition.audio.input.transcription = { model: "azure-speech", language: "en-IN,hi-IN" };
    await route.fulfill({ response, json: detail });
  });
  await page.goto("/editor/");
  await openTemplatePicker(page);
  await page.locator('[data-template-id="customer-support-example"]').click();
  await expect(page.locator("#template-picker")).toBeHidden();
  await page.locator("#node-outline button").first().click();
  await expect(page.getByLabel("Input language", { exact: true })).toHaveValue("en-IN,hi-IN");
  await page.getByRole("button", { name: "Save node", exact: true }).click();
  await page.locator("#view-agent-yaml").click();
  expect(await page.locator("#definition-output").innerText()).toContain('language: "en-IN,hi-IN"');
});

test("Editor publishes the selected input locale and reloads the same service value", async ({ page }) => {
  await page.goto("/editor/");
  await openTemplatePicker(page);
  await page.locator('[data-template-id="customer-support-example"]').click();
  await expect(page.locator("#template-picker")).toBeHidden();
  await page.locator("#node-outline button").first().click();
  await page.locator('[data-node-component="stt"]').click();
  await page.locator('[data-component-value="azure-speech"]').click();
  await page.getByRole("button", { name: "Open global input language", exact: true }).click();
  await page.getByLabel("Input language", { exact: true }).fill("Hindi");
  await page.getByLabel("Input language", { exact: true }).press("Enter");
  await page.getByRole("button", { name: "Save Agent General Settings", exact: true }).click();
  const publication = page.waitForResponse((response) =>
    response.request().method() === "POST" && new URL(response.url()).pathname.endsWith("/versions"));
  await page.locator("#publish-run-action").click();
  await page.getByRole("button", { name: "Publish and try it", exact: true }).click();
  const published = await publication;
  expect(published.ok()).toBe(true);
  const request = published.request();
  expect(request.postDataJSON().definition.audio.input.transcription).toMatchObject({
    model: "azure-speech", language: "hi-IN",
  });
  const resourcePath = new URL(request.url()).pathname.replace(/\/versions$/, "");
  const resource = await (await page.request.get(`${resourcePath}?api-version=v1`)).json();
  expect(resource.versions.latest.definition.audio.input.transcription.language).toBe("hi-IN");
  await page.goto(`/editor/?agent=${encodeURIComponent(resource.name)}`);
  await expect(page.locator("#dirty-badge")).toHaveText("Clean");
  await page.locator("#node-outline button").first().click();
  await expect(page.getByLabel("Input language", { exact: true })).toHaveValue("hi-IN");
  await page.getByRole("button", { name: "Save node", exact: true }).click();
  await page.locator("#node-outline button").nth(1).click();
  await expect(page.getByLabel("Input language", { exact: true })).toHaveCount(0);
  await page.locator('[data-node-component="stt"]').click();
  await expect(page.getByLabel("Input language", { exact: true })).toHaveCount(0);
  await expect(page.locator("#component-panel-kicker")).toHaveText("Agent-level input - all graph nodes");
  await page.getByRole("button", { name: "Open global input language", exact: true }).click();
  await expect(page.getByLabel("Input language", { exact: true })).toHaveValue("hi-IN");
});

test("AgentRuntime creation sends the selected input language through the service proxy", async ({ page }) => {
  await page.goto("/demo/");
  await page.getByRole("tab", { name: "Voice", exact: true }).click();
  const language = page.getByLabel("Input language", { exact: true });
  await expect(language).toHaveValue("Auto");
  await page.getByRole("button", { name: "Show input languages", exact: true }).click();
  await expect(page.getByRole("listbox", { name: "Input languages", exact: true }).getByRole("option")).toHaveCount(16);
  await language.fill("Hindi");
  await page.getByRole("tab", { name: "Agent", exact: true }).click();
  await page.getByRole("textbox", { name: /^Agent name/ }).fill("input-language-runtime");
  const publication = page.waitForRequest((request) =>
    request.method() === "POST" && new URL(request.url()).pathname.endsWith("/versions"));
  await page.getByRole("button", { name: "Create agent", exact: true }).click();
  const request = await publication;
  expect(request.postDataJSON().definition.audio.input.transcription).toEqual({
    model: "azure-speech", language: "hi-IN",
  });
  await expect(page.getByLabel("Session agent", { exact: true })).toHaveValue("input-language-runtime");
  const resource = await (await page.request.get("/agents/input-language-runtime?api-version=v1")).json();
  expect(resource.versions.latest.definition.audio.input.transcription.language).toBe("hi-IN");
});

test("Editor switches to the published MAI language catalog without silently dropping a locale", async ({ page }) => {
  await page.goto("/editor/");
  await openTemplatePicker(page);
  await page.locator('[data-template-id="customer-support-example"]').click();
  await expect(page.locator("#template-picker")).toBeHidden();
  await page.locator("#node-outline button").first().click();
  await page.locator('[data-node-component="stt"]').click();
  await page.locator('[data-component-value="azure-speech"]').click();
  await page.getByRole("button", { name: "Open global input language", exact: true }).click();
  const language = page.getByLabel("Input language", { exact: true });
  await language.fill("hi in");
  await language.press("Enter");
  await page.getByRole("button", { name: "Configure shared STT", exact: true }).click();
  await page.locator('[data-component-value="mai-transcribe-2"]').click();
  await page.getByRole("button", { name: "Open global input language", exact: true }).click();
  await expect(language).toHaveValue("hi-IN");
  await language.fill("Hindi");
  await language.press("Enter");
  await page.getByRole("button", { name: "Show input languages", exact: true }).click();
  await expect(page.locator("#component-stt-languages [role='option']")).toHaveCount(16);
  await expect(language).toHaveValue("hi-IN");
});

for (const playground of [false, true]) {
  for (const touch of [false, true]) {
    test.describe(`Template node pipeline clicks in ${playground ? "playground" : "local"} mode with ${touch ? "touch" : "mouse"}`, () => {
      test.use({ hasTouch: touch, viewport: { width: touch ? 390 : 1440, height: 1000 } });

      test("Editor opens each pipeline card on the first activation after editing a field", async ({ page }) => {
        const errors = [];
        page.on("pageerror", (error) => errors.push(error.message));
        await page.route("**/config", async (route) => {
          const response = await route.fetch();
          await route.fulfill({ response, json: { ...await response.json(), playground } });
        });
        await page.goto("/editor/");
        await openTemplatePicker(page);
        await page.locator('[data-template-id="customer-support-example"]').click();
        await expect(page.locator("#template-picker")).toBeHidden();
        const before = await readEditorDefinition(page);

        for (const nodeIndex of [0, 1]) {
          await page.locator("#node-outline button").nth(nodeIndex).click();
          const title = await page.locator("#node-editor-title").innerText();
          let instructions;
          for (const [kind, panelTitle] of [["stt", "Transcriber"], ["model", "Model"], ["voice", "Voice"]]) {
            instructions = `Updated ${title} instructions before opening ${kind}.`;
            await page.locator("#node-editor-instructions").fill(instructions);
            const target = page.locator(nodeIndex === 0
              ? `[data-node-component="${kind}"]`
              : `[data-component-card="${kind}"] .pipeline-card-heading`);
            if (touch) await target.tap();
            else await target.click();
            await expect(page.locator("#node-component-panel")).toBeVisible();
            await expect(page.locator("#component-panel-title")).toHaveText(panelTitle);
            await expect(page.locator("#node-editor-instructions")).toHaveValue(instructions);
            await page.getByRole("button", { name: "Close component configuration", exact: true }).click();
          }
          await page.getByRole("button", { name: "Save node", exact: true }).click();
          const after = await readEditorDefinition(page);
          const expected = structuredClone(before);
          if (nodeIndex === 0) expected.instructions = instructions;
          else expected.handoff.nodes[0].config.instructions = instructions;
          expect(after).toEqual(expected);
          await page.locator("#undo-action").click();
          expect(await readEditorDefinition(page)).toEqual(before);
        }
        expect(errors).toEqual([]);
      });
    });
  }
}

test("Editor pipeline activation commits runtime fields and retains keyboard and cancel behavior", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/editor/");
  await openTemplatePicker(page);
  await page.locator('[data-template-id="customer-support-example"]').click();
  await expect(page.locator("#template-picker")).toBeHidden();
  const before = await readEditorDefinition(page);
  await page.locator("#node-outline button").first().click();

  await page.getByLabel("Input language", { exact: true }).fill("Hindi");
  await page.locator('[data-node-component="stt"]').click();
  await expect(page.locator("#node-component-panel")).toBeVisible();
  await expect(page.getByLabel("Input language", { exact: true })).toHaveValue("hi-IN");
  await page.getByRole("button", { name: "Close component configuration", exact: true }).click();

  await page.getByLabel("Silence duration", { exact: true }).fill("432");
  await page.locator('[data-component-card="model"] .pipeline-card-heading').click();
  await expect(page.locator("#node-component-panel")).toBeVisible();
  const edited = await readEditorDefinition(page);
  expect(edited.audio.input.transcription.language).toBe("hi-IN");
  expect(edited.audio.input.turn_detection.silence_duration_ms).toBe(432);
  await page.keyboard.press("Escape");
  await expect(page.locator("#node-component-panel")).toBeHidden();

  for (const key of ["Enter", "Space"]) {
    await page.locator('[data-component-card="voice"]').focus();
    await page.keyboard.press(key);
    await expect(page.locator("#node-component-panel")).toBeVisible();
    await expect(page.locator("#component-panel-title")).toHaveText("Voice");
    await page.keyboard.press("Escape");
  }
  await page.getByRole("button", { name: "Back to graph", exact: true }).click();
  expect(await readEditorDefinition(page)).toEqual(before);
  expect(errors).toEqual([]);
});

for (const width of [1440, 390]) {
  test(`Input language accepts text and shows Auto at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/editor/");
    await page.getByRole("button", { name: "Create blank", exact: true }).click();
    await page.locator("#node-outline button").first().click();
    await page.locator('[data-node-component="stt"]').click();
    await page.locator('[data-component-value="azure-speech"]').click();
    await page.getByRole("button", { name: "Open global input language", exact: true }).click();
    const language = page.getByRole("combobox", { name: "Input language", exact: true });
    await expect(language).toHaveValue("Auto");
    await expect(language).toBeVisible();
    await language.fill("Hindi");
    await language.press("Enter");
    await expect(language).toHaveValue("hi-IN");
    await language.fill("");
    await language.press("Enter");
    await expect(language).toHaveValue("Auto");
    const bounds = await language.boundingBox();
    expect(bounds.width).toBeGreaterThan(100);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
  });
}

for (const [scenario, rootModel, nodeModel] of [
  ["realtime", "azure-realtime", "gpt-realtime-2.1"],
  ["mixed", "gpt-5.4", "gpt-realtime-2.1"],
  ["cascaded", "gpt-5.4", "gpt-5.4"],
]) {
  test(`Editor explains ${scenario} STT model restrictions beside the choices`, async ({ page }) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.route("**/api/templates/customer-support-example?*", async (route) => {
      const response = await route.fetch();
      const detail = await response.json();
      detail.definition.model = rootModel;
      detail.definition.audio.input.transcription = { model: "azure-speech" };
      for (const node of detail.definition.handoff.nodes) {
        node.config ||= {};
        node.config.model = nodeModel;
      }
      await route.fulfill({ response, json: detail });
    });
    await page.goto("/editor/");
    await openTemplatePicker(page);
    await page.locator('[data-template-id="customer-support-example"]').click();
    await expect(page.locator("#template-picker")).toBeHidden();
    await page.locator("#node-outline button").first().click();
    await page.locator('[data-node-component="stt"]').click();

    const panel = page.locator("#node-component-panel-body");
    const note = panel.getByRole("note", { name: "Why are STT options limited?" });
    await expect(note).toBeVisible();
    await expect(note).toContainText("All nodes share one STT setting");
    await expect(note).toContainText("Project and region availability still apply");
    if (scenario === "cascaded") {
      await expect(note).not.toContainText("Your graph includes realtime models");
      await expect(note.locator("code")).toHaveCount(0);
    } else {
      await expect(note).toContainText("Your graph includes realtime models");
      await expect(note.locator("code")).toContainText(["gpt-realtime-2.1"]);
      await expect(note.locator("code")).toHaveCount(scenario === "realtime" ? 2 : 1);
      if (scenario === "realtime") {
        await expect(note.locator("code").filter({ hasText: "azure-realtime" })).toBeVisible();
      }
    }
    const choices = await panel.locator("[data-component-kind='stt']").evaluateAll(
      (buttons) => buttons.map((button) => ({
        id: button.dataset.componentValue, disabled: button.disabled,
      })),
    );
    expect(choices.find((choice) => choice.id === "azure-speech").disabled).toBe(false);
    expect(choices.find((choice) => choice.id === "whisper-1").disabled)
      .toBe(scenario !== "realtime");
    await expect(panel.locator('[data-component-value="azure-speech"]'))
      .toHaveAttribute("aria-pressed", "true");
    const mainBounds = await panel.locator(".stt-selection-main").boundingBox();
    const noteBounds = await note.boundingBox();
    expect(noteBounds.x).toBeGreaterThanOrEqual(mainBounds.x + mainBounds.width);

    await note.getByRole("button", { name: "Review this node's model" }).click();
    await expect(page.locator("#component-panel-title")).toHaveText("Model");
    await expect(panel.getByRole("note", { name: "Why are STT options limited?" })).toHaveCount(0);
    await expect(panel.locator(`[data-component-value="${rootModel}"]`))
      .toHaveAttribute("aria-pressed", "true");
    if (scenario === "cascaded") {
      await panel.locator('[data-component-value="gpt-realtime-2.1"]').click();
      await page.locator('[data-node-component="stt"]').click();
      await expect(note).toContainText("Your graph includes realtime models");
      await expect(note.locator("code")).toHaveText(["gpt-realtime-2.1"]);
      await note.getByRole("button", { name: "Review this node's model" }).click();
      await panel.locator(`[data-component-value="${rootModel}"]`).click();
    }
    await page.locator('[data-node-component="stt"]').click();
    if (scenario === "cascaded") {
      await expect(note).not.toContainText("Your graph includes realtime models");
    }
    expect(await panel.locator("[data-component-kind='stt']").evaluateAll(
      (buttons) => buttons.map((button) => ({
        id: button.dataset.componentValue, disabled: button.disabled,
      })),
    )).toEqual(choices);

    for (const width of [768, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      await expect(note).toBeVisible();
      const responsiveNoteBounds = await note.boundingBox();
      const responsiveMainBounds = await panel.locator(".stt-selection-main").boundingBox();
      if (width > 560) {
        expect(responsiveNoteBounds.x)
          .toBeGreaterThanOrEqual(responsiveMainBounds.x + responsiveMainBounds.width);
      } else {
        expect(responsiveNoteBounds.y + responsiveNoteBounds.height)
          .toBeLessThanOrEqual(responsiveMainBounds.y);
      }
      expect(await panel.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
    }
    expect(errors).toEqual([]);
  });
}

test("Editor explains STT restrictions when only Whisper is available in the project", async ({ page }) => {
  const cfg = await (await page.request.get("/config")).json();
  await page.route("**/static/handoff/pipeline-availability.json", (route) => route.fulfill({
    json: {
      project: cfg.project,
      stt: Object.fromEntries(PIPELINE_COMPONENTS.stt.map((component) => [
        component.id, { available: component.id === "whisper-1" },
      ])),
    },
  }));
  await page.route("**/api/templates/customer-support-example?*", async (route) => {
    const response = await route.fetch();
    const detail = await response.json();
    detail.definition.model = "gpt-realtime-2.1";
    detail.definition.audio.input.transcription = { model: "whisper-1" };
    for (const node of detail.definition.handoff.nodes) {
      node.config ||= {};
      node.config.model = "gpt-realtime-2.1";
    }
    await route.fulfill({ response, json: detail });
  });
  await page.goto("/editor/");
  await openTemplatePicker(page);
  await page.locator('[data-template-id="customer-support-example"]').click();
  await expect(page.locator("#template-picker")).toBeHidden();
  await page.locator("#node-outline button").first().click();
  await page.locator('[data-node-component="stt"]').click();
  const panel = page.locator("#node-component-panel-body");
  await expect(panel.locator('[data-component-kind="stt"]')).toHaveCount(1);
  await expect(panel.locator('[data-component-value="whisper-1"]')).toBeEnabled();
  await expect(panel.locator('[data-component-value="whisper-1"]'))
    .toHaveAttribute("aria-pressed", "true");
  const note = panel.getByRole("note", { name: "Why are STT options limited?" });
  await expect(note).toContainText("Your graph includes realtime models");
  await expect(note).toContainText("available in this project");
  await expect(note.locator("code")).toHaveText(["gpt-realtime-2.1"]);
  await note.getByRole("button", { name: "Review this node's model" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#component-panel-title")).toHaveText("Model");
});

for (const [width, height] of [[1440, 1000], [683, 512], [455, 341], [390, 844]]) {
  test(`Voice picker stays above global settings with a scrollable list at ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/editor/");
    await page.getByRole("button", { name: "Create blank", exact: true }).click();
    await page.locator("#node-outline button").first().click();
    await page.locator('[data-node-component="voice"]').click();
    const panel = page.locator("#node-component-panel");
    const table = panel.locator(".component-table-wrap");
    await expect(panel).toBeVisible();
    const bounds = await panel.boundingBox();
    expect(bounds.height).toBeGreaterThan(height * 0.8);
    await expect(table).toHaveCSS("overflow-y", "auto");
    const visibleChoices = await table.evaluate((element) => {
      const bounds = element.getBoundingClientRect();
      return [...element.querySelectorAll("[data-component-value]")].filter((button) => {
        const row = button.getBoundingClientRect();
        if (row.top < bounds.top || row.bottom > bounds.bottom) return false;
        const hit = document.elementFromPoint(row.left + row.width / 2, row.top + row.height / 2);
        return button.contains(hit);
      }).length;
    });
    expect(visibleChoices).toBeGreaterThanOrEqual(height <= 512 ? 2 : 4);
    await page.locator("#component-voice-search").fill("Swara");
    const voice = page.locator('[data-component-value="hi-IN-SwaraNeural"]');
    await expect(voice).toBeVisible();
    await voice.click();
    await expect(voice).toHaveAttribute("aria-pressed", "true");
    await page.getByRole("button", { name: "Close component configuration", exact: true }).click();
    await expect(page.locator("#node-component-panel")).toBeHidden();
  });
}

test("Editor groups voices by locale without model restrictions and publishes automatic input", async ({ page }) => {
  const cfg = await (await page.request.get("/config")).json();
  await page.goto("/editor/");
  await openTemplatePicker(page);
  await page.locator('[data-template-id="customer-support-example"]').click();
  await expect(page.locator("#template-picker")).toBeHidden();
  await page.locator("#node-outline button").first().click();
  await page.locator('[data-node-component="voice"]').click();
  const locale = page.locator("#component-voice-locale");
  await expect(locale).toHaveValue("");
  await expect(page.locator('tbody[data-voice-locale="en-US"]')).toBeVisible();
  expect(await page.locator("#component-voice-locales option").count()).toBeGreaterThan(150);
  await expect(page.locator('[data-component-value="zh-CN-XiaoxiaoNeural"]')).toBeEnabled();
  await locale.fill("hi-IN");
  await expect(page.locator('[data-component-value="hi-IN-SwaraNeural"]')).toBeEnabled();
  await expect(page.locator('[data-component-value="diya"]')).toBeEnabled();
  await locale.fill("zh-CN");
  await expect(page.locator('[data-component-value="zh-CN-XiaoxiaoNeural"]')).toBeEnabled();
  await locale.fill("en-IN");
  await expect(page.locator('[data-component-value="en-IN-Diya:DragonHDLatestNeural"]')).toBeEnabled();
  await locale.fill("All locales");
  for (const voice of cfg.azureVoices) {
    await expect(page.locator(`[data-component-kind="voice"][data-component-value="${voice}"]`)).toBeEnabled();
  }
  const native = page.locator('[data-component-kind="voice"][data-component-value="emma"]');
  await expect(native).toBeEnabled();
  await expect(page.locator('tbody[data-voice-locale=""]')).toContainText("No fixed locale");
  for (const name of ["Brian", "Emma"]) {
    const voice = `en-US-${name}:DragonHDOmniLatestNeural`;
    await page.locator(`[data-component-kind="voice"][data-component-value="${voice}"]`).click();
    await page.getByRole("button", { name: "Close component configuration" }).click();
    await page.getByRole("button", { name: "Save node", exact: true }).click();
    await page.locator("#view-agent-yaml").click();
    await expect(page.locator("#definition-output")).toContainText(`name: "${voice}"`);
    await expect(page.locator("#definition-output")).toContainText('type: "azure-standard"');
    await page.getByRole("button", { name: "Close definition drawer", exact: true }).click();
    await page.locator("#node-outline button").first().click();
    await page.locator('[data-node-component="voice"]').click();
    await expect(page.locator(`[data-component-value="${voice}"]`)).toHaveAttribute("aria-pressed", "true");
  }
  await page.locator('[data-node-component="model"]').click();
  await page.locator('[data-component-value="azure-realtime"]').click();
  await page.locator('[data-node-component="voice"]').click();
  await expect(page.locator('[data-component-value="en-US-Emma:DragonHDOmniLatestNeural"]'))
    .toHaveAttribute("aria-pressed", "true");
  await expect(page.locator('[data-component-value="emma"]')).toBeEnabled();
  await page.locator('[data-node-component="model"]').click();
  await page.locator('[data-component-value="gpt-realtime"]').click();
  await page.getByRole("button", { name: "Close component configuration" }).click();
  await page.getByRole("button", { name: "Save node", exact: true }).click();
  const publication = page.waitForRequest((request) =>
    request.method() === "POST" && new URL(request.url()).pathname.endsWith("/versions"));
  await page.locator("#publish-run-action").click();
  await page.getByRole("button", { name: "Publish and try it", exact: true }).click();
  const request = await publication;
  const definition = request.postDataJSON().definition;
  expect(definition.audio.input.transcription).not.toHaveProperty("language");
  expect(definition.audio.output.voice).toEqual({
    type: "azure-standard", name: "en-US-Emma:DragonHDOmniLatestNeural",
  });
  await expect(page).toHaveURL(/\/demo\/.*agent=local-only-/);
  const published = await (await page.request.get(
    new URL(request.url()).pathname.replace(/\/versions$/, "") + "?api-version=v1",
  )).json();
  expect(published.versions.latest.definition.audio).toEqual(definition.audio);
});

for (const width of [1440, 1280, 390]) {
  test(`Voice search quickly finds Ava and Hindi without changing selection at ${width}px`, async ({ page }) => {
    const publications = [];
    page.on("request", (request) => {
      if (request.method() === "POST" && /\/versions\?/.test(request.url())) publications.push(request.url());
    });
    await page.setViewportSize({ width, height: width === 1280 ? 720 : 1000 });
    await page.goto("/editor/");
    await openTemplatePicker(page);
    await page.locator('[data-template-id="customer-support-example"]').click();
    await page.locator("#node-outline button").first().click();
    await page.locator('[data-node-component="voice"]').click();
    const locale = page.getByRole("combobox", { name: "Voice locale", exact: true });
    const search = page.getByRole("searchbox", { name: "Search voices", exact: true });
    await expect(locale).toHaveAttribute("list", "component-voice-locales");
    for (const input of [locale, search]) {
      await expect(input).toHaveCSS("background-color", "rgb(255, 255, 255)");
      await expect(input).toHaveCSS("border-color", "rgb(113, 135, 124)");
    }
    await expect(page.locator("#node-component-panel-body .component-advanced")).toHaveCount(0);
    await expect(page.locator("#node-component-panel-body")).not.toContainText("Advanced voice controls");
    await locale.fill("en us");
    await expect(locale).toHaveCSS("border-color", "rgb(8, 121, 92)");
    await search.pressSequentially("ava");
    await expect(search).toHaveValue("ava");
    await expect(search).toBeFocused();
    expect(await page.locator('[data-component-kind="voice"]').count()).toBeGreaterThan(1);
    expect(await page.locator('[data-component-kind="voice"]').count()).toBeLessThan(12);
    await expect(page.locator('[data-component-value="en-US-AvaNeural"] .voice-option-id'))
      .toHaveText("en-US-AvaNeural");
    await expect(page.locator(".voice-picker-current")).toContainText("en-US-Emma:DragonHDOmniLatestNeural");
    await search.press("Backspace");
    await expect(search).toHaveValue("av");
    await locale.fill("Hindi");
    await search.fill("Swara");
    await expect(page.locator('[data-component-kind="voice"]')).toHaveCount(1);
    await expect(page.locator('[data-component-value="hi-IN-SwaraNeural"]')).toBeVisible();
    await search.fill("no-such-voice");
    await expect(page.locator(".voice-empty-state")).toContainText("No voices match");
    await expect(page.locator("#component-voice-count")).toContainText("0 /");
    await page.getByRole("button", { name: "Clear filters", exact: true }).click();
    await expect(locale).toHaveValue("");
    await expect(search).toHaveValue("");
    expect(await page.locator('[data-component-kind="voice"]').count()).toBeGreaterThan(900);
    await locale.fill("en-US");
    await search.fill("AvaNeural");
    await page.locator('[data-component-value="en-US-AvaNeural"]').click();
    await page.getByRole("button", { name: "Close component configuration" }).click();
    await page.getByRole("button", { name: "Save node", exact: true }).click();
    await page.locator("#view-agent-yaml").click();
    await expect(page.locator("#definition-output")).toContainText('name: "en-US-AvaNeural"');
    expect(publications).toEqual([]);
    expect(await page.evaluate(() => window.microphoneCalls)).toBe(0);
  });
}

test("Runtime voice override uses the same editable locale and voice search", async ({ page }) => {
  await page.goto("/demo/?agent=fixture-agent");
  await expect(page.getByLabel("Session agent", { exact: true })).toHaveValue("fixture-agent");
  await page.locator(".session-settings summary").click();
  const settings = page.locator(".session-settings");
  const locale = settings.getByRole("combobox", { name: "Voice locale", exact: true });
  const search = settings.getByRole("searchbox", { name: "Search voices", exact: true });
  const voice = settings.getByLabel("Voice override", { exact: true });
  for (const input of [locale, search, voice]) {
    await expect(input).toHaveCSS("background-color", "rgb(255, 255, 255)");
    await expect(input).toHaveCSS("border-color", "rgb(113, 135, 124)");
  }
  await locale.fill("hi in");
  await search.fill("swara");
  await expect(voice.locator("optgroup option")).toHaveCount(1);
  await voice.selectOption("hi-IN-SwaraNeural");
  await locale.fill("en-US");
  await search.fill("ava");
  await expect(voice).toHaveValue("hi-IN-SwaraNeural");
  await expect(voice.locator('option[value="en-US-AvaNeural"]')).toHaveCount(1);
  await settings.getByRole("button", { name: "Clear filters", exact: true }).click();
  await expect(voice).toHaveValue("hi-IN-SwaraNeural");
  expect(await voice.locator("optgroup option").count()).toBeGreaterThan(900);
  expect(await page.evaluate(() => window.microphoneCalls)).toBe(0);
});

test("Editor publishes a non-English voice discovered outside the old shortlist", async ({ page }) => {
  await page.goto("/editor/");
  await openTemplatePicker(page);
  await page.locator('[data-template-id="customer-support-example"]').click();
  await page.locator("#node-outline button").first().click();
  await page.locator('[data-node-component="voice"]').click();
  await page.locator("#component-voice-locale").fill("ta-IN");
  await page.locator('[data-component-value="ta-IN-PallaviNeural"]').click();
  await page.getByRole("button", { name: "Close component configuration" }).click();
  await page.getByRole("button", { name: "Save node", exact: true }).click();
  const publication = page.waitForRequest((request) =>
    request.method() === "POST" && new URL(request.url()).pathname.endsWith("/versions"));
  await page.locator("#publish-run-action").click();
  await page.getByRole("button", { name: "Publish and try it", exact: true }).click();
  expect((await publication).postDataJSON().definition.audio.output.voice).toEqual({
    type: "azure-standard", name: "ta-IN-PallaviNeural",
  });
  await expect(page).toHaveURL(/\/demo\/.*agent=local-only-/);
});

for (const width of [1440, 390]) {
  test(`Editor hides pipeline cost and latency by default at ${width}px`, async ({ page }) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/editor/");
    await expect(page.getByRole("checkbox", { name: "Debug mode", exact: true })).toHaveCount(0);
    await page.getByRole("button", { name: "Create blank", exact: true }).click();
    const dirty = await page.locator("#dirty-badge").innerText();
    await expect(page.locator(".node-card")).toHaveCount(1);
    await expect(page.locator(".node-metric-details")).toHaveCount(0);
    await page.locator("#node-outline button").first().click();
    await expect(page.locator(".pipeline-overview, .component-metrics")).toHaveCount(0);
    const panel = page.locator("#node-component-panel-body");
    for (const kind of ["stt", "model", "voice"]) {
      await page.locator(`[data-node-component="${kind}"]`).click();
      await expect(panel.locator(".component-table th")).toHaveCount(2);
      await expect(panel.locator("tbody tr:not(.voice-locale-heading)").first().locator("td")).toHaveCount(2);
      await expect(panel.getByRole("button", { name: /Sort by (Latency|Cost)/ })).toHaveCount(0);
      await expect(panel.locator(".component-table-metric, .component-estimate-disclaimer")).toHaveCount(0);
      expect((await panel.locator(".component-option-copy").allTextContents()).join(" "))
        .not.toMatch(/Latency source:|Rate source:|Public rate:|¢\/min/);
      await page.getByRole("button", { name: "Close component configuration" }).click();
    }
    await page.getByRole("button", { name: "Save node", exact: true }).click();
    // Debug mode has no visible toggle; it is requested per page load with ?debug=1.
    await page.goto("/editor/?debug=1");
    await page.getByRole("button", { name: "Create blank", exact: true }).click();
    await expect(page.locator(".node-metric-details")).toHaveCount(1);
    await page.locator("#node-outline button").first().click();
    await expect(page.locator(".component-metrics")).toHaveCount(3);
    await expect(page.locator("#node-cost-value")).toContainText("¢/min");
    for (const kind of ["stt", "model", "voice"]) {
      await page.locator(`[data-node-component="${kind}"]`).click();
      await expect(panel.locator(".component-table th")).toHaveCount(4);
      await expect(panel.getByRole("button", { name: "Sort by Cost", exact: true })).toBeVisible();
      await panel.getByRole("button", { name: "Sort by Cost", exact: true }).click();
      await expect(panel.getByRole("note", { name: "Latency and cost disclaimer" })).toBeVisible();
      await page.getByRole("button", { name: "Close component configuration" }).click();
    }
    await page.getByRole("button", { name: "Save node", exact: true }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.reload();
    await expect(page.locator(".node-metric-details")).toHaveCount(0);
    expect(errors).toEqual([]);
  });
}

for (const playground of [false, true]) {
  for (const width of [1440, 390]) {
    test(`Editor controls and complete node ranges at ${width}px in ${playground ? "playground" : "local"} mode`, async ({ page }) => {
      const errors = [];
      page.on("pageerror", (error) => errors.push(error.message));
      await page.setViewportSize({ width, height: 1000 });
      await page.route("**/config", async (route) => {
        const response = await route.fetch();
        const config = await response.json();
        await route.fulfill({ response, json: {
          ...config,
          playground,
          ...(playground ? { realtimeTranscriptionModels: ["azure-speech"] } : {}),
        } });
      });
      await page.goto("/");
      await expect(page).toHaveURL(/\/editor\/$/);
      await expect(page).toHaveTitle("Editor · Voice Agents");
      await expect(page.locator("body")).toHaveClass(playground ? /playground-mode/ : "");
      const rail = page.getByRole("complementary", { name: "Graph outline", includeHidden: true });
      await expect(rail).toBeVisible();
      await expect(rail.getByRole("heading", { name: "Agents", exact: true })).toBeVisible();
      await expect(rail.locator("select, input[type=number], #rail-agent-name, #new-graph, #runtime-settings")).toHaveCount(0);
      await expect(rail.getByRole("button", { name: /blank|New Agent/i })).toHaveCount(0);
      await expect(rail.getByRole("tab", { name: /^Nodes/ })).toBeVisible();
      await expect(rail.getByRole("tab", { name: /^Edges/ })).toBeVisible();
      await expect(rail.getByRole("tab", { name: /^Nodes/ })).toBeInViewport();
      await expect(rail.getByRole("tab", { name: /^Edges/ })).toBeInViewport();
      await expect(page.getByRole("button", { name: "Validate", exact: true })).toHaveCount(0);
      const blank = page.getByRole("button", { name: "Create blank", exact: true });
      const template = page.getByRole("button", { name: "Load from templates", exact: true });
      const tryNow = page.getByRole("button", { name: "Try it now", exact: true });
      const bounds = await Promise.all([blank, template, tryNow].map((button) => button.boundingBox()));
      expect(Math.max(...bounds.map((box) => box.y)) - Math.min(...bounds.map((box) => box.y))).toBeLessThan(2);
      expect(bounds[0].x).toBeLessThan(bounds[1].x);
      expect(bounds[1].x).toBeLessThan(bounds[2].x);
      await expect(page.locator(".canvas-meta #view-agent-yaml")).toBeVisible();
      await expect(page.locator(".canvas-meta #layout-action")).toHaveText("↧ Format view");
      await blank.click();
      await expect(page.locator(".node-card")).toHaveCount(1);
      await expect(tryNow).toBeEnabled();
      await expect(tryNow).toHaveCSS("color", "rgb(255, 255, 255)");
      for (const button of [template, tryNow]) {
        await expect(button).toHaveCSS("animation-name", "template-spectrum");
      }
      await expect(tryNow).toHaveCSS("background-image", /rgb\(25, 170, 128\)/);
      await page.locator("#view-agent-yaml").click();
      await expect(page.locator("#definition-output")).toContainText('kind: "voice"');
      if (playground) {
        await expect(page.locator("#definition-output")).toContainText("store: false");
        await expect(page.locator("#definition-output")).toContainText("azure-speech");
      }
      await page.getByRole("button", { name: "Close definition" }).click();
      await page.goto("/editor/?debug=1");
      await blank.click();
      const details = page.locator(".node-card .node-metric-details").first();
      await details.locator("summary").click();
      await expect(details.locator(".node-metric-breakdown")).toHaveText(
        `Disclaimer ${PIPELINE_METRICS_DISCLAIMER}`,
      );
      await expect(details.locator(".metric-distribution")).toHaveCount(0);
      await template.click();
      await page.locator('[data-template-id="elevator-service-example"]').click();
      const metrics = page.locator(".node-card .node-metrics");
      await expect(metrics).toHaveCount(10);
      for (const metric of await metrics.all()) {
        await expect(metric).not.toContainText(/normalized|estimated|\$|~/i);
        await expect(metric.locator(".metric").first()).toContainText("¢/min");
        const cost = metric.locator(".metric").first().locator("strong");
        expect(await cost.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
        const range = metric.locator(".metric").nth(1).locator("strong");
        await expect(range).toContainText(/\d[\d,.]* (?:ms|s) – \d[\d,.]* (?:ms|s)/);
        await expect(range).toHaveCSS("color", "rgb(37, 99, 235)");
        await expect(range).toHaveCSS("white-space", "nowrap");
        await expect(range.locator("small")).toHaveCount(0);
        const layout = await range.evaluate((element) => {
          const text = document.createRange();
          text.selectNodeContents(element.firstChild);
          return {
            lines: text.getClientRects().length,
            fits: element.scrollWidth <= element.clientWidth,
          };
        });
        expect(layout).toEqual({ lines: 1, fits: true });
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(errors).toEqual([]);
    });
  }
}

for (const playground of [false, true]) {
  test(`Editor Agent cards support search and keyboard navigation in ${playground ? "playground" : "local"} mode`, async ({ page }) => {
    const errors = [];
    const cursors = [];
    let opens = 0;
    page.on("pageerror", (error) => errors.push(error.message));
    await page.route("**/config", async (route) => {
      const response = await route.fetch();
      await route.fulfill({ response, json: {
        ...await response.json(),
        playground,
      } });
    });
    const resource = (name, kind = "voice") => ({
      name,
      versions: { latest: {
        version: "1",
        created_at: name === "fixture-agent" ? 2 : 1,
        definition: { kind },
      } },
    });
    await page.route("**/agents?*", (route) => {
      const params = new URL(route.request().url()).searchParams;
      const after = params.get("after");
      expect(params.get("limit")).toBe("10");
      cursors.push(after);
      return route.fulfill({ json: after ? {
        data: [resource("customer-concierge"), resource("not-a-voice-agent", "prompt")],
        has_more: false,
      } : {
        data: [resource("fixture-agent")],
        has_more: true,
        last_id: "page-two",
      } });
    });
    await page.route("**/agents/fixture-agent?*", (route) => {
      opens += 1;
      return route.continue();
    });

    await page.goto("/editor/");
    const rail = page.getByRole("complementary", { name: "Graph outline" });
    const library = rail.getByRole("listbox", { name: "Voice Agents", exact: true });
    const fixture = library.getByRole("option", { name: "fixture-agent", exact: true });
    const concierge = library.getByRole("option", { name: "customer-concierge", exact: true });
    const search = rail.getByRole("searchbox", { name: "Search Agents" });
    const open = rail.getByRole("button", { name: "Open selected Agent" });
    const more = rail.getByRole("button", { name: "Load more Agents" });
    await expect(library.getByRole("option")).toHaveCount(1);
    await expect(library).toHaveAttribute("aria-busy", "false");
    await expect(rail.locator("#agent-result-count")).toHaveText("1 loaded");
    expect(cursors).toEqual([null]);
    await more.click();
    await expect(library.getByRole("option")).toHaveCount(2);
    await expect(more).toBeHidden();
    await expect(rail.locator("#agent-result-count")).toHaveText("2 available");
    expect(cursors).toEqual([null, "page-two"]);
    await expect(rail.locator(".problems")).toBeHidden();
    await expect(fixture).toHaveAttribute("aria-selected", "true");
    await expect(fixture).toContainText("v1");
    await concierge.click();
    await expect(concierge).toHaveAttribute("aria-selected", "true");
    await concierge.press("ArrowUp");
    await expect(fixture).toBeFocused();
    await fixture.press("End");
    await expect(concierge).toBeFocused();
    await concierge.press("Home");
    await expect(fixture).toBeFocused();
    await fixture.dblclick();
    await expect(page.locator("#agent-title")).toHaveText("fixture-agent");
    await expect.poll(() => opens).toBe(1);
    await expect(page).toHaveURL(/\/editor\/\?agent=fixture-agent$/);

    await search.fill("no-such-agent");
    await expect(library.getByRole("option")).toHaveCount(0);
    await expect(library).toContainText("No matching Agents. Try another name.");
    await expect(open).toBeDisabled();
    await search.fill("FIXTURE");
    await expect(library.getByRole("option")).toHaveCount(1);
    await expect(rail.locator("#agent-result-count")).toHaveText("1 matching · 2 loaded");
    await fixture.press("Enter");
    await expect.poll(() => opens).toBe(2);
    await expect(page.locator("#operation-status")).toContainText("Loaded fixture-agent version 1");
    await expect(fixture).toHaveAttribute("aria-selected", "true");
    await search.clear();
    await expect(library.getByRole("option")).toHaveCount(2);
    await open.click();
    await expect.poll(() => opens).toBe(3);
    await expect(page.locator("#operation-status")).toContainText("Loaded fixture-agent version 1");

    await expect(rail.locator("#add-node")).toBeEnabled();
    await expect(rail.locator("#add-edge")).toBeEnabled();
    await rail.getByRole("tab", { name: /^Edges/ }).click();
    await expect(rail.getByRole("listbox", { name: "Graph edges", exact: true })).toBeVisible();
    await expect(rail.locator("#edge-outline")).toContainText("No routes yet.");
    await expect(rail.getByRole("listbox", { name: "Graph nodes", exact: true })).toBeHidden();
    await rail.getByRole("tab", { name: /^Nodes/ }).click();
    await rail.locator("#node-outline button").first().click();
    await expect(page.locator("#node-editor")).toBeVisible();
    await page.locator("#close-node-editor").click();
    await expect(page.locator("#node-editor")).toBeHidden();
    await page.reload();
    await expect(page.locator("#agent-title")).toHaveText("fixture-agent");
    await expect(library.getByRole("option")).toHaveCount(1);
    await expect(more).toBeVisible();
    await expect(fixture).toHaveAttribute("aria-selected", "true");
    await expect.poll(() => opens).toBe(4);
    await page.setViewportSize({ width: 390, height: 1000 });
    await expect(rail.getByRole("tab", { name: /^Nodes/ })).toBeInViewport();
    await expect(rail.getByRole("tab", { name: /^Edges/ })).toBeInViewport();
    expect(errors).toEqual([]);
  });
}

for (const playground of [false, true]) {
  test(`Try it now runs an existing Agent without publishing in ${playground ? "playground" : "local"} mode`, async ({ page }) => {
    const errors = [];
    const sockets = [];
    const publications = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("websocket", (socket) => sockets.push(socket.url()));
    page.on("request", (request) => {
      if (request.method() === "POST" && /\/versions\?/.test(request.url())) {
        publications.push(request.url());
      }
    });
    await page.route("**/config", async (route) => {
      const response = await route.fetch();
      await route.fulfill({ response, json: { ...await response.json(), playground } });
    });

    await page.goto("/editor/");
    await page.getByRole("option", { name: "fixture-agent", exact: true }).click();
    await page.getByRole("button", { name: "Open selected Agent" }).click();
    await expect(page.locator("#agent-title")).toHaveText("fixture-agent");
    await expect(page.locator("#dirty-badge")).toHaveText("Clean");
    const tryNow = page.getByRole("button", { name: "Try it now", exact: true });
    await expect(tryNow).toBeEnabled();
    await tryNow.click();

    await expect(page).toHaveURL(/\/demo\/\?agent=fixture-agent&view=handoff$/);
    await expect(page.getByLabel("Session agent", { exact: true })).toHaveValue("fixture-agent");
    await expect(page.locator(".connection-status")).toContainText("listening");
    expect(sockets).toHaveLength(1);
    expect(new URL(sockets[0]).pathname).toBe("/agents/fixture-agent/endpoint/protocols/voice");
    expect(publications).toEqual([]);
    await expect.poll(() => page.evaluate(() => window.microphoneCalls)).toBe(1);
    await page.getByRole("textbox", { name: "Message your agent" }).fill("Try this existing Agent");
    await page.getByRole("button", { name: "Send", exact: true }).click();
    await expect(page.getByText("Fixture response from the simulated Foundry service.", { exact: true })).toBeVisible();

    await page.getByRole("button", { name: "Stop session" }).click();
    await expect(page.getByRole("button", { name: "Connect & start session" })).toBeEnabled();
    await page.reload();
    await expect(page.getByRole("button", { name: "Connect & start session" })).toBeEnabled();
    await page.waitForLoadState("networkidle");
    expect(sockets).toHaveLength(1);
    expect(await page.evaluate(() => window.microphoneCalls)).toBe(0);
    expect(errors).toEqual([]);
  });
}

test("Try it now preserves an existing Agent input language when publishing another edit", async ({ page }) => {
  let firstRead = true;
  await page.route("**/agents/fixture-agent?*", async (route) => {
    if (!firstRead) return route.continue();
    firstRead = false;
    const response = await route.fetch();
    const resource = await response.json();
    resource.versions.latest.definition.audio.input = {
      format: { type: "audio/pcm", rate: 24000 },
      transcription: { model: "azure-speech", language: "en-IN,hi-IN", prompt: "Contoso" },
    };
    await route.fulfill({ response, json: resource });
  });
  await page.goto("/editor/?agent=fixture-agent");
  await expect(page.locator("#agent-title")).toHaveText("fixture-agent");
  await expect(page.locator("#dirty-badge")).toHaveText("Clean");
  await page.locator("#node-outline button").first().click();
  await page.locator("#node-editor-instructions").fill("Preserve the caller language configuration.");
  await page.getByRole("button", { name: "Save node", exact: true }).click();
  await expect(page.locator("#dirty-badge")).toHaveText("Unsaved");
  const publication = page.waitForRequest((request) =>
    request.method() === "POST" && new URL(request.url()).pathname.endsWith("/versions"));
  await page.getByRole("button", { name: "Try it now", exact: true }).click();
  const definition = (await publication).postDataJSON().definition;
  expect(definition.audio.input.transcription).toEqual({
    model: "azure-speech", language: "en-IN,hi-IN", prompt: "Contoso",
  });
  await expect(page).toHaveURL(/\/demo\/\?agent=fixture-agent&view=handoff$/);
  await expect(page.locator(".connection-status")).toContainText("listening");
  await page.getByRole("button", { name: "Stop session" }).click();
  await page.locator(".session-settings summary").click();
  const voices = page.getByLabel("Voice override", { exact: true });
  expect(await voices.locator('optgroup[label^="en-US"] option').count()).toBeGreaterThan(10);
  await expect(voices.locator('option[value="emma"]')).toBeEnabled();
});

test("Try it now publishes edited existing Agents before starting their session", async ({ page }) => {
  const publications = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && /\/versions\?/.test(request.url())) {
      publications.push(request.postDataJSON());
    }
  });
  await page.goto("/editor/?agent=fixture-agent");
  await expect(page.locator("#dirty-badge")).toHaveText("Clean");
  await page.locator("#node-outline button").first().click();
  await page.locator("#node-editor-instructions").fill("Existing Agent instructions edited in the browser.");
  await page.locator("#done-node-editor").click();
  await expect(page.locator("#dirty-badge")).toHaveText("Unsaved");
  await page.getByRole("button", { name: "Try it now", exact: true }).click();

  await expect(page).toHaveURL(/\/demo\/\?agent=fixture-agent&view=handoff$/);
  await expect(page.locator(".connection-status")).toContainText("listening");
  await expect(page.getByLabel("Session agent", { exact: true })).toHaveValue("fixture-agent");
  expect(publications).toHaveLength(1);
  expect(publications[0].definition.instructions).toBe("Existing Agent instructions edited in the browser.");
  await expect.poll(() => page.evaluate(() => window.microphoneCalls)).toBe(1);
  await page.getByRole("button", { name: "Stop session" }).click();
});

test("an unavailable Editor run request never starts a different Agent", async ({ page }) => {
  const sockets = [];
  page.on("websocket", (socket) => sockets.push(socket.url()));
  await page.addInitScript(() => {
    window.sessionStorage.setItem("voice-agent-editor-run", "unavailable-agent");
  });
  await page.goto("/demo/?agent=fixture-agent");
  await expect(page.getByLabel("Session agent", { exact: true })).toHaveValue("fixture-agent");
  await expect(page.getByText(
    "Could not start Editor Agent 'unavailable-agent': it is not available in this Project.",
    { exact: true },
  )).toBeVisible();
  await page.waitForLoadState("networkidle");
  expect(sockets).toEqual([]);
  expect(await page.evaluate(() => window.microphoneCalls)).toBe(0);
  expect(await page.evaluate(() => window.sessionStorage.getItem("voice-agent-editor-run"))).toBeNull();
  await expect(page.getByRole("button", { name: "Connect & start session" })).toBeEnabled();
});

test("Editor Agent library reports a failed load and can refresh without losing its layout", async ({ page }) => {
  const errors = [];
  let attempts = 0;
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/agents?*", (route) => {
    attempts += 1;
    return attempts === 1
      ? route.fulfill({ status: 503, json: { error: { message: "Agent catalog unavailable" } } })
      : route.continue();
  });
  await page.goto("/editor/");
  await expect(page.locator("#agent-load-state")).toHaveText("Load failed");
  await expect(page.locator("#operation-error")).toContainText("Agent catalog unavailable");
  await expect(page.locator("#agent-select")).toContainText("Use refresh to try again.");
  await expect(page.locator("#load-agent")).toBeDisabled();
  await page.getByRole("button", { name: "Refresh Agent list" }).click();
  await expect(page.locator("#agent-select [role=option]")).not.toHaveCount(0);
  await expect(page.locator("#agent-select")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator("#agent-load-state")).toHaveClass(/ready/);
  expect(errors).toEqual([]);
});

test("Editor shows configuration failures without relying on removed Project controls", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/config", (route) => route.fulfill({
    status: 503,
    json: { error: { message: "Foundry configuration unavailable" } },
  }));
  await page.goto("/editor/");
  await expect(page.locator("#operation-error")).toContainText("Foundry configuration unavailable");
  await expect(page.locator("#agent-load-state")).toHaveText("Load failed");
  await expect(page.locator("#load-agent")).toBeDisabled();
  await expect(page.getByRole("complementary", { name: "Graph outline" })).toBeVisible();
  expect(errors).toEqual([]);
});

test("playground keeps the graph in view when the canvas is resized", async ({ page }) => {
  await page.route("**/config", async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, json: {
      ...await response.json(),
      playground: true,
      realtimeTranscriptionModels: ["azure-speech"],
    } });
  });
  await page.goto("/");
  await expect(page.locator("body")).toHaveClass("playground-mode");
  await page.getByRole("button", { name: "Create blank", exact: true }).click();
  await expect(page.locator(".node-card")).toHaveCount(1);
  for (const width of [1440, 390, 820, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await expect.poll(async () => {
      const canvas = await page.locator("#canvas").boundingBox();
      const node = await page.locator(".node-card").boundingBox();
      return node.x >= canvas.x
        && node.x + node.width <= canvas.x + canvas.width
        && node.y >= canvas.y
        && node.y + node.height <= canvas.y + canvas.height;
    }).toBe(true);
  }
});

test("Foundry-only portal creates, edits, connects and reads persisted data through the proxy", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/demo/");
  await expect(page.getByRole("heading", { name: "Voice agent studio" })).toBeVisible();
  await expect(page.locator(".portal-notice")).toContainText("Azure Foundry project");
  const config = await (await page.request.get("/config")).json();
  expect(config.host).toBe("https://sample.services.ai.azure.com/api/projects/sample-project");
  expect(config).not.toHaveProperty("mode");
  await expect(page.getByRole("checkbox", { name: /^Save conversations/ })).not.toBeChecked();
  await page.getByRole("textbox", { name: /^Agent name/ }).fill("local-browser-agent");
  await page.getByRole("checkbox", { name: /^Save conversations/ }).check();
  await page.getByRole("button", { name: "Create agent", exact: true }).click();
  await expect(page.getByLabel("Session agent", { exact: true })).toHaveValue("local-browser-agent");
  await page.getByRole("button", { name: "Edit definition" }).click();
  const editor = page.getByLabel("Agent definition YAML");
  await expect(editor).toHaveValue(/Respond naturally and concisely\./);
  const yaml = await editor.inputValue();
  await editor.fill(yaml.replace("Respond naturally and concisely.", "Browser-tested local instructions."));
  await page.getByRole("button", { name: "Save as new version" }).click();
  await expect(page.locator(".definition-save-state")).toContainText("Version 2 created");
  await page.getByRole("button", { name: "Close definition editor" }).click();
  await expect(page.locator(".selected-agent-meta")).toContainText("v2");
  await expect(page.getByRole("button", { name: "View trace" })).toBeDisabled();
  await page.getByRole("button", { name: "Connect & start session" }).click();
  await expect(page.locator(".connection-status")).toContainText("listening");
  await page.getByRole("textbox", { name: "Message your agent" }).fill("Hello from the real local browser");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByText("Fixture response from the simulated Foundry service.", { exact: true })).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.microphoneCalls)).toBeGreaterThan(0);
  const popupPromise = page.waitForEvent("popup");
  await page.getByRole("button", { name: "View persisted" }).click();
  const popup = await popupPromise;
  await expect(popup.getByRole("heading", { name: "Persisted conversation" })).toBeVisible();
  await expect(popup.getByText("Fixture response from the simulated Foundry service.", { exact: true })).toBeVisible();
  await popup.close();
  await page.screenshot({ path: "../.run/portal-local.png", fullPage: true });
  await page.getByRole("button", { name: "Stop session" }).click();
  await expect(page.getByRole("button", { name: "Connect & start session" })).toBeEnabled();
  expect(errors).toEqual([]);
});

test("guided authoring uses the configured Foundry service response", async ({ page }) => {
  await page.goto("/demo/");
  await page.getByRole("button", { name: "Generate", exact: true }).click();
  await page.getByRole("textbox", { name: /^Generated agent name/ }).fill("local-template-agent");
  await page.getByRole("textbox", { name: /^Goal/ }).fill("Answer questions about this sample.");
  await page.getByRole("button", { name: "Generate agent", exact: true }).click();
  await expect(page.locator(".review-definition")).toContainText("Generated definition from the test fixture.");
});

test("Template data remains available without exposing a Templates navigation item", async ({ page }) => {
  await page.route("**/api/templates/*/mcp/probe", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      ok: false,
      reached: false,
      error: "Synthetic browser test: local MCP is not running.",
      start_command: "cd VoiceAgent/shared_mcp && ./scripts/e2e-local.sh",
      guide_url: "/guide/run-samples",
    }),
  }));

  await page.goto("/");
  const navigation = page.getByRole("navigation", { name: "Portal pages" });
  await expect(navigation).toBeVisible();
  await expect(navigation.getByText("AgentRuntime", { exact: true })).toBeVisible();
  await expect(navigation.getByRole("link", { name: "Templates", exact: true })).toHaveCount(0);

  await page.goto("/templates/");
  await expect(page.getByText("37 available", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Example 1: Finance with Handoff — Realtime/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Example 1: Finance with Handoff — Cascade/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Example 2: Finance with OTP and Officer Search/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Example 3: Elevator Service with Safety, Zendesk, and Handoff/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Example 4: Front Desk with Fluency and Handoff/ })).toBeVisible();
  await expect(page.locator("#detail-name")).toHaveText("Example 1: Finance with Handoff — Realtime");
  await expect(page.locator("#graph-wrap svg")).toBeVisible();
  await expect(page.locator("#mcp-token-config")).toBeHidden();
  await expect(page.getByRole("link", { name: "Templates", exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "AgentRuntime", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Voice agent studio" })).toBeVisible();
});

for (const [architecture, model] of [
  ["Realtime", "gpt-realtime-2.1"],
  ["Cascaded", "gpt-5.4"],
]) {
  test(`${architecture} node selectors display a short disclaimer and plain column titles`, async ({ page }) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto("/editor/?debug=1");
    await openTemplatePicker(page);
    await page.locator('[data-template-id="elevator-service-example"]').click();
    await page.locator("#node-outline button").first().click();
    await page.locator('[data-node-component="model"]').click();
    await page.locator(`[data-component-kind="model"][data-component-value="${model}"]`).click();

    const panel = page.locator("#node-component-panel-body");
    const disclaimer = panel.getByRole("note", { name: "Latency and cost disclaimer" });
    for (const kind of ["stt", "voice", "model"]) {
      await page.locator(`[data-node-component="${kind}"]`).click();
      await expect(disclaimer).toBeVisible();
      await expect(panel.locator(":scope > :first-child")).toHaveAttribute("role", "note");
      await expect(disclaimer.locator("strong")).toHaveText("Disclaimer");
      await expect(disclaimer.locator("p")).toHaveText(
        PIPELINE_METRICS_DISCLAIMER,
      );
      await expect(panel.locator(".component-panel-context")).toHaveCount(0);
      await expect(panel.locator(".component-table th").nth(2).locator(".component-sort-label"))
        .toHaveText("Latency");
      await expect(panel.locator(".component-table th").nth(3).locator(".component-sort-label"))
        .toHaveText("Cost");
      await expect(panel.getByRole("button", { name: "Sort by Cost", exact: true }))
        .toBeVisible();
      await panel.getByRole("button", { name: "Sort by Latency", exact: true }).click();
      await expect(disclaimer).toBeVisible();
    }
    expect(errors).toEqual([]);
  });
}

test("Editor loads the fluency-improved Front Desk template and complete graph", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/editor/");
  await openTemplatePicker(page);
  await expect(page.locator(".template-choice")).toHaveCount(37);
  const frontdesk = page.locator('[data-template-id="frontdesk-receptionist-example"]');
  await expect(frontdesk).toContainText("Example 4: Front Desk with Fluency and Handoff");
  await frontdesk.click();
  await expect(page.locator("#agent-title")).toContainText(
    "local-only-frontdesk-receptionist-example-",
  );
  await expect(page.locator(".node-card")).toHaveCount(9);
  await expect(page.locator("#node-outline button")).toHaveCount(9);
  await page.locator("#view-agent-yaml").click();
  const output = page.locator("#definition-output");
  await expect(output).toContainText("Hard conversational response contract");
  await expect(output).toContainText("frontdesk_search_zendesk_articles");
  await expect(output).toContainText("frontdesk_record_message");
  await expect(output).toContainText("caller_confirmed=true");
  await expect(output).toContainText("store: false");
  await expect(output).not.toContainText("echo_cancellation");
  await expect(output).not.toContainText("static_interim_response");
  expect(errors).toEqual([]);
});

test("Handoff Graph loads a Portal template, publishes it, and opens the runtime graph", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto("/");
  await expect(page).toHaveURL(/\/editor\/$/);
  await expect(page.getByRole("heading", { name: "Agents", exact: true })).toBeVisible();
  await page.goto("/editor/?debug=1");

  await openTemplatePicker(page);
  const choices = page.locator(".template-choice");
  await expect(choices).toHaveCount(37);
  await page.locator('[data-template-id="elevator-service-example"]').click();

  await expect(page.locator("#agent-title")).toContainText(
    "local-only-elevator-service-example-",
  );
  await expect(page.locator(".node-card")).toHaveCount(10);
  await page.locator("#node-outline button").first().click();
  await page.locator('[data-node-component="model"]').click();
  await expect(page.locator('[data-component-kind="model"]')).toHaveCount(14);
  await expect(page.locator(".component-table")).toBeVisible();
  await expect(page.getByRole("button", { name: "Sort by Latency" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sort by Cost" })).toBeVisible();
  await page.getByRole("button", { name: "Explain Latency" }).click();
  await expect(page.locator('[data-component-header-popup="latency"]')).toBeVisible();
  await expect(page.locator('[data-component-header-popup="latency"]')).toContainText(
    "60s input + 60s output audio",
  );
  await page.getByRole("button", { name: "Explain Cost" }).click();
  await expect(page.locator('[data-component-header-popup="cost"]')).toBeVisible();
  await expect(page.locator('[data-component-header-popup="cost"]')).toContainText(
    "Actual charges may be higher",
  );
  await expect(
    page.locator('[data-component-kind="model"][data-component-value="gpt-realtime"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("~0.8 s");
  await expect(
    page.locator('[data-component-kind="model"][data-component-value="gpt-6.1-sol"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("~1.6 s");
  await expect(
    page.locator('[data-component-kind="model"][data-component-value="gpt-realtime"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("3.2¢/min");
  await expect(
    page.locator('[data-component-kind="model"][data-component-value="gpt-realtime"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("Public rate: $32 audio input + $4 text input + $16 text output / 1M tokens");
  await page.getByRole("button", { name: "Sort by Latency" }).click();
  await expect(
    page.locator('.component-table tbody [data-component-kind="model"]').first(),
  ).toHaveAttribute("data-component-value", "gpt-realtime-mini");
  await page.getByRole("button", { name: "Sort by Latency" }).click();
  await expect(
    page.locator('.component-table tbody [data-component-kind="model"]').first(),
  ).toHaveAttribute("data-component-value", "gpt-6.1-sol");

  await page.locator('[data-component-kind="model"][data-component-value="gpt-6-luna"]').click();
  await expect(page.locator(".model-card .component-metrics")).toContainText(
    "2.96¢/min",
  );
  await expect(page.locator("#node-cost-value")).toContainText("7.7¢/min");
  await expect(page.locator(".transcriber-card .component-metrics")).toContainText(
    "1,016 ms",
  );
  await expect(page.locator(".voice-card .component-metrics")).toContainText(
    "307 ms",
  );
  await page.locator('[data-node-component="model"]').click();
  await expect(
    page.locator('[data-component-kind="model"][data-component-value="gpt-6-luna"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("Conservative model allowance");
  await expect(
    page.locator('[data-component-kind="model"][data-component-value="gpt-6-luna"]')
      .locator("xpath=ancestor::tr"),
  ).not.toContainText("Public rate:");

  await page.locator('[data-component-kind="model"][data-component-value="gpt-5.4"]').click();
  await page.locator('[data-node-component="stt"]').click();
  await expect(page.locator('[data-component-kind="stt"]')).toHaveCount(12);
  await expect(page.getByRole("button", { name: "Sort by Latency" })).toBeVisible();
  await expect(
    page.locator('[data-component-kind="stt"][data-component-value="azure-speech"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("~1.016 s");
  await expect(
    page.locator('[data-component-kind="stt"][data-component-value="mai-transcribe-2"]'),
  ).toBeEnabled();
  await expect(
    page.locator('[data-component-kind="stt"][data-component-value="mai-transcribe-2"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("Public rate: $17 / 1M Voice Live speech-input tokens");
  await expect(
    page.locator('[data-component-kind="stt"][data-component-value="azure-speech"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("Public rate: $17 / 1M Voice Live speech-input tokens");
  await expect(
    page.locator('[data-component-kind="stt"][data-component-value="whisper-1"]'),
  ).toBeDisabled();

  await page.locator('[data-node-component="model"]').click();
  await page.locator('[data-component-kind="model"][data-component-value="gpt-realtime-2.1"]').click();
  await page.locator('[data-node-component="stt"]').click();
  await expect(page.locator('[data-component-kind="stt"]')).toHaveCount(12);
  await expect(
    page.locator('[data-component-kind="stt"][data-component-value="whisper-1"]'),
  ).toBeEnabled();
  await expect(
    page.locator('[data-component-kind="stt"][data-component-value="whisper-1"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("~1.507 s");
  await expect(
    page.locator('[data-component-kind="stt"][data-component-value="whisper-1"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("2¢/min");
  await expect(
    page.locator('[data-component-kind="stt"][data-component-value="whisper-1"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("Conservative transcription allowance");
  await expect(
    page.locator('[data-component-kind="stt"][data-component-value="whisper-1"]')
      .locator("xpath=ancestor::tr"),
  ).not.toContainText("Public rate:");
  await expect(
    page.locator('[data-component-kind="stt"][data-component-value="native-realtime-audio"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("No extra STT cost");
  await expect(page.locator(".transcriber-card .component-metrics")).toContainText(
    "STT-only cost 1.02¢/min",
  );
  await expect(page.locator(".model-card .component-metrics")).toContainText(
    "Model-only cost 3.31¢/min",
  );
  await expect(page.locator(".voice-card .component-metrics")).toContainText(
    "TTS-only cost 3.72¢/min",
  );
  await expect(page.locator("#node-cost-value")).toContainText("8.05¢/min");
  await page.locator('[data-node-component="voice"]').click();
  await page.locator("#component-voice-locale").fill("All locales");
  await expect(page.getByRole("button", { name: "Sort by Latency" })).toBeVisible();
  await expect(
    page.locator('[data-component-kind="voice"][data-component-value="alloy"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("Included in model");
  await expect(
    page.locator('[data-component-kind="voice"][data-component-value="en-US-Ava:DragonHDLatestNeural"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("~0.307 s");
  await expect(
    page.locator('[data-component-kind="voice"][data-component-value="en-US-Ava:DragonHDLatestNeural"]')
      .locator("xpath=ancestor::tr"),
  ).toContainText("Public rate: $31 / 1M Voice Live speech-output tokens");
  await expect(page.locator(".component-provider", { hasText: "GPT native" }).first()).toBeVisible();
  await expect(page.locator(".component-provider", { hasText: "Azure Speech" }).first()).toBeVisible();
  await expect(page.locator(".component-table td:nth-child(4) .component-table-bar").first()).toBeVisible();
  await expect(page.locator("#node-cost-value")).toContainText("¢/min");
  await expect(page.locator("#node-latency-value")).toContainText("1.3 s – 3.7 s");
  await expect(page.locator(".overview-metric .pipeline-segment.model").last()).toHaveAttribute(
    "title",
    "1.3 s – 3.7 s",
  );
  await page.locator("#done-node-editor").click();

  await expect(page.locator("#publish-run-action")).toBeEnabled();
  let releaseReadback;
  const readbackGate = new Promise((resolve) => { releaseReadback = resolve; });
  await page.route("**/agents/*/versions/*?*", async (route) => {
    const response = await route.fetch();
    await readbackGate;
    await route.fulfill({ response });
  }, { times: 1 });
  const verified = page.waitForFunction(
    () => document.querySelector('[data-publish-step="verify"]')?.dataset.status === "complete",
  );
  try {
    await page.locator("#publish-run-action").click();
    await page.getByRole("button", { name: "Publish and try it", exact: true }).click();
    const progress = page.getByRole("dialog", { name: "Try it now" });
    await expect(progress).toBeVisible();
    await expect(progress).toContainText("Validate working copy");
    await expect(progress).toContainText("Refresh MCP connection");
    await expect(progress).toContainText("Publish Agent version");
    await expect(progress).toContainText("Verify published version");
    await expect(progress).toContainText("Open AgentRuntime");
  } finally {
    releaseReadback();
  }
  await verified;

  await expect(page).toHaveURL(/\/demo\/\?agent=local-only-elevator-service-example-[^&]+&view=handoff$/);
  await expect(page.getByRole("heading", { name: "Voice agent studio" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Agent Debug/ })).toHaveAttribute(
    "aria-expanded",
    "true",
  );
  await expect(page.locator(".handoff-graph")).toBeVisible();
  await expect(page.getByRole("button", { name: "Connect & start session" })).toBeEnabled();
  expect(await page.evaluate(() => window.microphoneCalls)).toBe(0);
  expect(errors).toEqual([]);
});

test("Handoff Graph progress stops on publication failure and preserves the working copy", async ({ page }) => {
  await page.goto("/editor/");
  await openTemplatePicker(page);
  await page.locator('[data-template-id="elevator-service-example"]').click();
  await page.route("**/agents/*/versions?*", (route) => route.fulfill({
    status: 502,
    contentType: "application/json",
    body: JSON.stringify({ error: { message: "Synthetic publication failure" } }),
  }));

  await page.locator("#publish-run-action").click();
  await page.getByRole("button", { name: "Publish and try it", exact: true }).click();
  const progress = page.getByRole("dialog", { name: "Try it now" });
  await expect(progress.locator('[data-publish-step="publish"]')).toHaveAttribute(
    "data-status",
    "failed",
  );
  await expect(progress.getByRole("alert")).toContainText("Synthetic publication failure");
  await expect(progress.getByRole("button", { name: "Close", exact: true })).toBeVisible();
  await expect(page.locator("#agent-title")).toContainText("local-only-elevator-service-example-");
  await expect(page).toHaveURL(/\/editor\/$/);
});

test("WebRTC uses the Foundry project directly and session logs can be disabled", async ({ page }) => {
  await page.goto("/webrtc");
  await expect(page.getByRole("heading", { name: "Start a voice session" })).toBeVisible();
  await page.getByLabel("Agent", { exact: true }).fill("fixture-agent");
  await expect(page.getByRole("button", { name: "Start WebRTC session" })).toBeEnabled();
  expect(await page.evaluate(() => window.microphoneCalls)).toBe(0);
  await page.getByRole("link", { name: "Return to studio" }).click();
  await page.goto("/demo/?debug=1");
  await page.getByRole("link", { name: "Local session logs" }).click();
  await expect(page.getByRole("heading", { name: "Demo session log" })).toBeVisible();
  await expect(page.getByText("session recording is disabled", { exact: true })).toBeVisible();
  const response = await page.request.get("/api/demo/sessions");
  expect(response.ok()).toBe(true);
  expect((await response.json()).sessions).toEqual([]);
});

test("actual HTTP server rejects cross-origin requests and never serves configuration files", async ({ request }) => {
  const crossOrigin = await request.get("/config", { headers: { Origin: "https://example.invalid" } });
  expect(crossOrigin.status()).toBe(403);
  const secrets = await request.get("/static/demo/.env");
  expect(secrets.status()).toBe(404);
});

test("legacy autostart URLs only select an agent; Connect remains an explicit action", async ({ page }) => {
  const sockets = [];
  page.on("websocket", (socket) => sockets.push(socket.url()));
  await page.goto("/?agent=fixture-agent&autostart=1");
  await expect(page.getByLabel("Session agent", { exact: true })).toHaveValue("fixture-agent");
  await page.waitForLoadState("networkidle");
  expect(sockets).toEqual([]);
  expect(await page.evaluate(() => window.microphoneCalls)).toBe(0);
  await expect(page.getByRole("button", { name: "Connect & start session" })).toBeEnabled();
});
