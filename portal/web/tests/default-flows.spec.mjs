// Copyright (c) Microsoft. All rights reserved.
import { test as base, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";

const config = JSON.parse(await readFile(new URL("../../templates.config.json", import.meta.url), "utf8"));
const templates = config.templates.filter((template) => template.enabled !== false);
const reply = "Fixture response from the simulated Foundry service.";
const test = base.extend({
  browserErrors: [async ({ page }, use) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await use(errors);
    expect(errors).toEqual([]);
  }, { auto: true }],
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("voice-agent-playground-welcome-v1", "dismissed"));
  await page.route("**/*", (route) => new URL(route.request().url()).hostname === "127.0.0.1"
    ? route.continue() : route.abort());
});

async function configureMode(page, playground) {
  await page.route("**/config", async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, json: {
      ...await response.json(),
      playground,
      ...(playground ? { realtimeTranscriptionModels: ["azure-speech"], defaultStore: false } : {}),
    } });
  });
}

async function publishWorkingCopy(page) {
  const publication = page.waitForResponse((response) =>
    response.request().method() === "POST" && new URL(response.url()).pathname.endsWith("/versions"));
  await page.getByRole("button", { name: "Try it now", exact: true }).click();
  await page.getByRole("button", { name: "Publish and try it", exact: true }).click();
  const response = await publication;
  expect(response.ok(), await response.text()).toBe(true);
  const body = response.request().postDataJSON();
  expect(body.draft).toBe(false);
  expect(body.definition.model_type).toBe("managed");
  if (body.definition.handoff) {
    expect(body.definition.handoff.edges.length).toBeGreaterThan(0);
    expect(body.definition.handoff.edges.length).toBeLessThanOrEqual(128);
  }
  await expect(page).toHaveURL(/\/runtime\/\?agent=[^&]+&view=handoff$/);
  const name = new URL(page.url()).searchParams.get("agent");
  const readback = await page.request.get(`/agents/${encodeURIComponent(name)}?api-version=v1`);
  expect(readback.ok()).toBe(true);
  expect((await readback.json()).versions.latest.definition).toEqual(body.definition);
  return { name, definition: body.definition };
}

async function expectConversation(page, { start = true } = {}) {
  if (start) {
    await page.getByRole("button", { name: "Connect & start session", exact: true }).click();
  }
  await expect(page.locator(".connection-status")).toContainText("listening");
  await page.getByRole("textbox", { name: "Message your agent", exact: true }).fill("Hello");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByText(reply, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Stop session", exact: true }).click();
  await expect(page.getByRole("button", { name: "Connect & start session", exact: true })).toBeEnabled();
}

for (const playground of [false, true]) {
  const mode = playground ? "playground" : "local";

  test(`default blank -> publish -> reply -> reopen without republishing (${mode})`, async ({ page }) => {
    await configureMode(page, playground);
    const publications = [];
    page.on("request", (request) => {
      if (request.method() === "POST" && new URL(request.url()).pathname.endsWith("/versions")) {
        publications.push(request.url());
      }
    });
    await page.goto("/editor/", { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Create blank", exact: true }).click();
    const published = await publishWorkingCopy(page);
    if (playground) expect(published.definition.store).toBe(false);
    await expectConversation(page);
    await page.goto("/editor/", { waitUntil: "networkidle" });
    await page.getByRole("option", { name: published.name, exact: true }).click();
    await expect(page.locator("#agent-title")).toHaveText(published.name);
    await expect(page.locator("#dirty-badge")).toHaveText("Clean");
    await page.getByRole("button", { name: "Try it now", exact: true }).click();
    await expect(page).toHaveURL(/\/runtime\/\?agent=[^&]+&view=handoff$/);
    await expectConversation(page, { start: false });
    expect(publications).toHaveLength(1);
  });

  test(`default blank JSON export -> import -> publish without saving settings (${mode})`, async ({ page }) => {
    await configureMode(page, playground);
    await page.goto("/editor/", { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Create blank", exact: true }).click();
    await page.locator("#view-agent-yaml").click();
    await page.getByRole("tab", { name: "JSON", exact: true }).click();
    const json = await page.locator("#definition-output").innerText();
    const exported = JSON.parse(json);
    await page.getByRole("button", { name: "Import from agent", exact: true }).click();
    await page.locator("#agent-import-file").setInputFiles({
      name: "exported-agent.json", mimeType: "application/json", buffer: Buffer.from(json),
    });
    await expect(page.locator("#agent-import-status")).toContainText("Local validation passed");
    await page.getByRole("checkbox", {
      name: "Replace my current working copy, including unsaved edits.", exact: true,
    }).check();
    await page.getByRole("button", { name: "Import working copy", exact: true }).click();
    const published = await publishWorkingCopy(page);
    expect(published.definition).toEqual(exported);
    await expectConversation(page);
  });

  test(`flat Agent JSON import publishes without an empty handoff graph (${mode})`, async ({ page }) => {
    await configureMode(page, playground);
    const definition = {
      kind: "voice",
      model_type: "managed",
      model: "gpt-realtime",
      instructions: "Greet the caller and answer briefly.",
      store: false,
      audio: {
        input: { transcription: { model: "azure-speech" } },
        output: { voice: "en-US-AvaNeural", voice_type: "azure-standard" },
      },
    };
    await page.goto("/editor/", { waitUntil: "networkidle" });
    await page.locator("#view-agent-yaml").click();
    await page.getByRole("button", { name: "Import from agent", exact: true }).click();
    await page.locator("#agent-import-file").setInputFiles({
      name: "flat-agent.json", mimeType: "application/json",
      buffer: Buffer.from(JSON.stringify(definition)),
    });
    await expect(page.locator("#agent-import-status")).toContainText("Local validation passed");
    await page.getByRole("button", { name: "Import working copy", exact: true }).click();
    const published = await publishWorkingCopy(page);
    expect(published.definition).toEqual(definition);
    expect(published.definition).not.toHaveProperty("handoff");
    await expectConversation(page);
  });

  for (const failure of ["permission denied", "network failure"]) {
    test(`default blank still publishes and replies when voice discovery has ${failure} (${mode})`, async ({ page }) => {
      await configureMode(page, playground);
      await page.route("**/api/voices*", (route) => failure === "permission denied"
        ? route.fulfill({ status: 403, json: { error: "Synthetic voice discovery permission denied" } })
        : route.abort("failed"));
      await page.goto("/editor/", { waitUntil: "networkidle" });
      await expect(page.locator("#voice-catalog-status")).not.toBeEmpty();
      await page.getByRole("button", { name: "Create blank", exact: true }).click();
      const published = await publishWorkingCopy(page);
      expect(published.definition.audio.output.voice).toBeTruthy();
      await expectConversation(page);
    });
  }

  test(`default publication failure is visible, preserves edits and can be retried (${mode})`, async ({ page }) => {
    await configureMode(page, playground);
    await page.goto("/editor/", { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Create blank", exact: true }).click();
    const name = await page.locator("#agent-title").innerText();
    await page.route("**/agents/*/versions?*", (route) => {
      const body = route.request().postDataJSON();
      body.definition.handoff = { nodes: [], edges: [] };
      return route.continue({ postData: JSON.stringify(body) });
    }, { times: 1 });
    const failed = page.waitForResponse((response) =>
      response.request().method() === "POST" && new URL(response.url()).pathname.endsWith("/versions"));
    await page.getByRole("button", { name: "Try it now", exact: true }).click();
    await page.getByRole("button", { name: "Publish and try it", exact: true }).click();
    expect((await failed).status()).toBe(400);
    const progress = page.getByRole("dialog", { name: "Try it now", exact: true });
    await expect(progress.getByRole("alert")).toContainText("between 1 and 128 edges");
    await expect(page).toHaveURL(/\/editor\/$/);
    await expect(page.locator("#agent-title")).toHaveText(name);
    await expect(page.locator("#dirty-badge")).toHaveText("Unsaved");
    await progress.getByRole("button", { name: "Close", exact: true }).click();
    const published = await publishWorkingCopy(page);
    expect(published.definition.handoff.edges.length).toBeGreaterThan(0);
    await expectConversation(page);
  });
}

for (const template of templates) {
  test(`untouched default template publishes and replies: ${template.id}`, async ({ page }) => {
    await page.goto("/editor/", { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Load from templates", exact: true }).click();
    const card = page.locator(`[data-template-id="${template.id}"]`);
    const group = card.locator("xpath=ancestor::details[1]");
    if (!await group.evaluate((element) => element.open)) {
      await group.locator(":scope > summary").click();
    }
    const loaded = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.pathname === `/api/templates/${template.id}` && url.searchParams.get("version") === ".";
    });
    await card.click();
    const detailResponse = await loaded;
    expect(detailResponse.ok()).toBe(true);
    const detail = await detailResponse.json();
    await expect(page.locator("#template-picker")).toBeHidden();
    const published = await publishWorkingCopy(page);
    expect(published.definition).toEqual(detail.definition);
    await expectConversation(page);
  });
}
