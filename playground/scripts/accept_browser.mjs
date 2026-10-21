// Browser acceptance reads the shared token from an ignored local file.
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const portalWeb = process.env.VOICE_PLAYGROUND_PORTAL_WEB
  || join(root, "../../../voice-agent/portal/web");
const portalStatic = process.env.VOICE_PLAYGROUND_PORTAL_STATIC
  || join(portalWeb, "../static");
const { PIPELINE_METRICS_DISCLAIMER } = await import(
  pathToFileURL(join(portalStatic, "handoff/handoff-core.mjs")).href
);
const require = createRequire(join(portalWeb, "package.json"));
const { chromium, expect } = require("@playwright/test");
const baseURL = process.env.VOICE_PLAYGROUND_BASE_URL
  || "https://voice-agent-playground.blackground-c889ecc7.westus2.azurecontainerapps.io";
const invitationFile = process.env.VOICE_PLAYGROUND_INVITATION_FILE
  || join(root, ".run/access/invitation.local.json");
const invitation = JSON.parse(await readFile(invitationFile, "utf8"));
const email = process.env.VOICE_PLAYGROUND_EMAIL;
if (!email) throw new Error("VOICE_PLAYGROUND_EMAIL is required.");
const browser = await chromium.launch({ headless: true });
const errors = [];
try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    permissions: ["microphone"],
    extraHTTPHeaders: { "X-MS-Synthetic-Source": "playground-acceptance" },
  });
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  const firstResponse = await page.goto(baseURL, {
    waitUntil: "networkidle",
    timeout: 90_000,
  });
  if (!firstResponse || !page.url().startsWith(`${baseURL}/login?`)) {
    throw new Error(`Expected custom login page, got ${page.url()}`);
  }
  for (const viewport of [{ width: 390, height: 844 }, { width: 1440, height: 1000 }]) {
    await page.setViewportSize(viewport);
    for (const label of ["Access token", "Email address"]) {
      if (!(await page.getByLabel(label).isVisible())) {
        throw new Error(`${label} is not visible at viewport width ${viewport.width}.`);
      }
    }
    const contact = page.getByRole("link", { name: "yiwenrong@microsoft.com", exact: true });
    if (!(await contact.isVisible())
        || await contact.getAttribute("href") !== "mailto:yiwenrong@microsoft.com") {
      throw new Error("The login contact link is missing or incorrect.");
    }
  }
  if (await page.getByRole("button", { name: "Continue", exact: true }).count()) {
    throw new Error("Login must show token and email in one step.");
  }
  await page.screenshot({
    path: join(root, ".run/hosted-login.png"),
    fullPage: true,
  });
  await page.getByLabel("Access token").fill(invitation.invitationCode);
  await page.getByLabel("Email address").fill(email);
  const loginResponsePromise = page.waitForResponse(
    (response) => response.request().method() === "POST"
      && response.url() === `${baseURL}/login`,
  );
  await page.getByRole("button", { name: "Sign in" }).click();
  const loginResponse = await loginResponsePromise;
  if (loginResponse.status() !== 303) {
    throw new Error(`Login HTTP ${loginResponse.status()}`);
  }
  await page.waitForLoadState("networkidle");
  const response = await page.goto(baseURL, { waitUntil: "networkidle", timeout: 90_000 });
  if (!response || response.status() !== 200) throw new Error(`Editor HTTP ${response?.status()}`);
  await expect(page).toHaveURL(`${baseURL}/editor/`);
  await expect(page).toHaveTitle("Editor · Voice Agents");
  await expect(page.locator("body")).toHaveClass("playground-mode");
  for (const [source, target, status] of [
    ["/", "/editor/", 302],
    ["/handoff", "/editor/", 308],
    ["/handoff/?view=handoff", "/editor/?view=handoff", 308],
  ]) {
    const redirect = await context.request.get(`${baseURL}${source}`, { maxRedirects: 0 });
    expect(redirect.status(), `${source} redirect status`).toBe(status);
    expect(redirect.headers().location, `${source} redirect target`).toBe(target);
  }
  const rail = page.getByRole("complementary", { name: "Graph outline" });
  await expect(rail).toBeVisible();
  await expect(rail.getByRole("heading", { name: "Agents", exact: true })).toBeVisible();
  await expect(rail.locator("select, input[type=number], #rail-agent-name, #new-graph, #runtime-settings")).toHaveCount(0);
  const deployedAssetHashes = {};
  for (const [name, route, source] of [
    ["editorPage", "/editor/", "handoff/handoff.html"],
    ["editorModule", "/static/handoff/handoff-app.js", "handoff/handoff-app.js"],
    ["editorCore", "/static/handoff/handoff-core.mjs", "handoff/handoff-core.mjs"],
    ["editorStyles", "/static/handoff/handoff.css", "handoff/handoff.css"],
    ["runtimeBundle", "/static/demo/bundle.js", "bundle.js"],
    ["runtimeBundleStyles", "/static/demo/bundle.css", "bundle.css"],
    ["runtimeStyles", "/static/demo/styles.css", "styles.css"],
    ["webrtcBundle", "/static/demo/webrtc-bundle.js", "webrtc-bundle.js"],
    ["templatesPage", "/templates/", "templates.html"],
    ["templatesModule", "/static/template-app.js", "template-app.js"],
    ["templatesStyles", "/static/template-styles.css", "template-styles.css"],
  ]) {
    const asset = await context.request.get(`${baseURL}${route}`);
    expect(asset.status(), `${name} HTTP status`).toBe(200);
    const actual = createHash("sha256").update(await asset.body()).digest("hex");
    const expected = createHash("sha256")
      .update(await readFile(join(portalStatic, source))).digest("hex");
    expect(actual, `${name} must match the current Portal source`).toBe(expected);
    deployedAssetHashes[name] = actual;
  }
  const catalogResponse = await context.request.get(`${baseURL}/api/templates`);
  expect(catalogResponse.status()).toBe(200);
  const catalog = await catalogResponse.json();
  expect(catalog.errors).toEqual([]);
  const versionChecks = [];
  await expect(page.locator("#validate-action")).toHaveCount(0);
  await expect(page.locator(".canvas-meta #export-action")).toBeVisible();
  await expect(page.locator("#layout-action")).toBeVisible();
  await expect(page.locator("#layout-action")).toContainText("Format view");
  await page.getByRole("button", { name: "Create blank", exact: true }).click();
  await expect(page.locator(".node-card")).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Try it now", exact: true })).toBeEnabled();
  await expect(page.getByRole("checkbox", { name: "Debug mode", exact: true })).toHaveCount(0);
  await expect(page.locator(".node-metric-details")).toHaveCount(0);
  // Debug mode has no visible toggle; it is requested per page load with ?debug=1.
  await page.goto(`${baseURL}/editor/?debug=1`, { waitUntil: "networkidle", timeout: 90_000 });
  await page.getByRole("button", { name: "Create blank", exact: true }).click();
  await expect(page.locator(".node-card")).toHaveCount(1);
  await page.locator(".node-metrics").click();
  await expect(page.locator(".node-metric-breakdown")).toHaveText(
    `Disclaimer ${PIPELINE_METRICS_DISCLAIMER}`,
  );
  await page.getByRole("button", { name: "Load from templates", exact: true }).click();
  await page.locator('[data-template-id="elevator-service-example"]').click();
  await expect(page.locator(".node-card")).toHaveCount(10);
  await page.locator("#layout-action").click();
  await expect(page.locator('.node-card[data-node="$entrypoint"] .metric').first())
    .toContainText("8.92¢/min");
  await page.locator('.node-card[data-node="$entrypoint"] [data-node-pipeline="stt"]').click();
  const whisper = page.locator('[data-component-kind="stt"][data-component-value="whisper-1"]')
    .locator("xpath=ancestor::tr");
  await expect(whisper).toContainText("2¢/min");
  await expect(whisper).toContainText("Conservative transcription allowance");
  await expect(whisper).not.toContainText("Public rate:");
  await page.locator('[data-node-component="model"]').click();
  const realtime = page.locator('[data-component-kind="model"][data-component-value="gpt-realtime"]')
    .locator("xpath=ancestor::tr");
  await expect(realtime).toContainText("3.2¢/min");
  await expect(realtime).toContainText("Temporary model budget /150");
  await page.locator("#done-node-editor").click();
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await expect(rail).toBeVisible();
    await expect(rail.getByRole("tab", { name: /^Nodes/ })).toBeInViewport();
    await expect(rail.getByRole("tab", { name: /^Edges/ })).toBeInViewport();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect.poll(() => page.locator(".node-card").evaluateAll((nodes) => {
      const canvas = document.querySelector("#canvas").getBoundingClientRect();
      return nodes.some((node) => {
        const rect = node.getBoundingClientRect();
        return rect.right > canvas.left && rect.left < canvas.right
          && rect.bottom > canvas.top && rect.top < canvas.bottom;
      });
    })).toBe(true);
    const buttons = ["#create-blank-action", "#template-action", "#publish-run-action"];
    const boxes = await Promise.all(buttons.map((selector) => page.locator(selector).boundingBox()));
    expect(Math.max(...boxes.map((box) => box.y)) - Math.min(...boxes.map((box) => box.y))).toBeLessThan(2);
    for (const metrics of await page.locator(".node-metrics").all()) {
      await expect(metrics).not.toContainText(/\$|normalized|estimated|~/i);
      await expect(metrics.locator(".metric").first()).toContainText("¢/min");
      const range = metrics.locator(".metric").nth(1).locator("strong");
      await expect(range).toContainText(/\d[\d,.]* (?:ms|s) – \d[\d,.]* (?:ms|s)/);
      await expect(range).toHaveCSS("color", "rgb(37, 99, 235)");
      await expect(range).toHaveCSS("white-space", "nowrap");
      await expect(range.locator("small")).toHaveCount(0);
      expect(await range.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
    }
    await page.screenshot({
      path: join(root, `.run/hosted-editor-${width}.png`),
      fullPage: true,
    });
  }
  await page.goto(`${baseURL}/editor/`, { waitUntil: "networkidle", timeout: 90_000 });
  await page.getByRole("button", { name: "Create blank", exact: true }).click();
  await expect(page.locator(".node-metric-details")).toHaveCount(0);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("button", { name: "Load from templates", exact: true }).click();
  await expect(page.locator(".template-choice")).toHaveCount(catalog.templates.length);
  for (const template of catalog.templates) {
    const selector = page.getByRole("combobox", {
      name: `Version for ${template.name}`, exact: true,
    });
    expect(await selector.locator("option").evaluateAll((options) =>
      options.map((option) => option.value))).toEqual(template.versions.map((version) => version.id));
    if (template.versions.length === 1) {
      await expect(selector).toBeDisabled();
    }
  }
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    const template = catalog.templates.find((item) => item.versions.length > 1);
    if (!template) throw new Error("The deployed catalog contains no template backup versions.");
    const version = template.versions.find((item) => item.id !== template.default_version);
    await page.getByRole("combobox", {
      name: `Version for ${template.name}`, exact: true,
    }).selectOption(version.id);
    const detailResponse = await context.request.get(
      `${baseURL}/api/templates/${template.id}?version=${encodeURIComponent(version.id)}`,
    );
    expect(detailResponse.status()).toBe(200);
    const detail = await detailResponse.json();
    await page.locator(`[data-template-id="${template.id}"]`).click();
    await expect(page.locator("#template-picker")).toBeHidden();
    await page.locator("#export-action").click();
    await page.getByRole("tab", { name: "JSON", exact: true }).click();
    const exported = JSON.parse(await page.locator("#definition-output").innerText());
    expect(exported.instructions).toBe(detail.definition.instructions);
    versionChecks.push({ width, template: template.id, version: version.id });
    await page.getByRole("button", { name: "Close definition drawer", exact: true }).click();
    await page.getByRole("button", { name: "Load from templates", exact: true }).click();
  }
  await page.getByRole("button", { name: "Close template picker", exact: true }).click();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("link", { name: "AgentRuntime", exact: true }).click();
  await page.getByRole("heading", { name: "Voice agent studio" }).waitFor();
  await expect(page.getByRole("checkbox", { name: "Debug mode", exact: true })).toHaveCount(0);
  await expect(page.locator(".runtime-node-breakdown, .turn-metrics")).toHaveCount(0);
  const runtimeSplitChecks = [];
  for (const width of [1440, 1920]) {
    await page.setViewportSize({ width, height: 1000 });
    await expect.poll(async () => Math.abs(
      (await page.locator(".studio-side-column").boundingBox()).width
        - (await page.locator(".playground-column").boundingBox()).width,
    )).toBeLessThan(1);
    runtimeSplitChecks.push(width);
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  const sessionAgent = page.getByRole("combobox", { name: "Session agent", exact: true });
  await sessionAgent.click();
  await expect(sessionAgent).not.toHaveAttribute("list");
  await expect(page.getByRole("listbox", { name: "Session agents", exact: true })).toBeVisible();
  await expect(page.locator(".session-agent-menu")).toHaveCSS("border-radius", "13px");
  await sessionAgent.press("Escape");
  const notice = await page.locator(".portal-notice").innerText();
  if (!notice.includes("shared playground")) throw new Error(`Unexpected notice: ${notice}`);
  const cookies = await context.cookies(baseURL);
  for (const name of ["__Host-voice_playground_access"]) {
    const cookie = cookies.find((item) => item.name === name);
    if (!cookie?.secure || !cookie?.httpOnly || cookie.sameSite !== "Lax") {
      throw new Error(`Unsafe or missing cookie: ${name}`);
    }
  }
  const templatesResponse = await page.goto(`${baseURL}/templates/`, {
    waitUntil: "networkidle",
    timeout: 90_000,
  });
  if (!templatesResponse || templatesResponse.status() !== 200) {
    throw new Error(`Templates HTTP ${templatesResponse?.status()}`);
  }
  await page.getByText(`${catalog.templates.length} available`, { exact: true }).waitFor();
  const cards = await page.locator(".template-card, .template-choice").count();
  expect(cards).toBe(catalog.templates.length);
  await page.locator("#mcp-test-state.good").waitFor();
  if (!(await page.locator("#mcp-start-guide").isHidden())) {
    throw new Error("The local-MCP recovery guide is visible for a ready public MCP.");
  }
  for (const template of catalog.templates.filter((item) => item.versions.length > 1)) {
    await page.locator(`[data-template-id="${template.id}"]`).click();
    for (const version of template.versions) {
      await expect(page.locator("#template-version")).toBeEnabled();
      await page.getByLabel("Version", { exact: true }).selectOption(version.id);
      await page.getByRole("button", { name: "definition.json", exact: true }).click();
      await expect(page.locator("#template-version")).toHaveValue(version.id);
      const detailResponse = await context.request.get(
        `${baseURL}/api/templates/${template.id}?version=${encodeURIComponent(version.id)}`,
      );
      expect(detailResponse.status()).toBe(200);
      const detail = await detailResponse.json();
      await expect.poll(async () =>
        JSON.parse(await page.locator("#yaml-body").innerText()).definition.instructions,
      ).toBe(detail.definition.instructions);
      versionChecks.push({ template: template.id, version: version.id });
    }
  }
  await page.screenshot({
    path: join(root, ".run/hosted-templates.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "Editor", exact: true }).click();
  await expect(page).toHaveTitle("Editor · Voice Agents");
  await expect(rail).toBeVisible();
  const report = {
    baseURL,
    loginStatus: loginResponse.status(),
    singleStepLogin: true,
    mobileLoginFieldsVisible: true,
    contactLinkPresent: true,
    studioStatus: response.status(),
    templatesStatus: templatesResponse.status(),
    title: await page.title(),
    secureCookies: 1,
    templateCards: cards,
    templateVersions: catalog.templates.reduce((sum, template) => sum + template.versions.length, 0),
    templateVersionChecks: versionChecks,
    publicMcpReady: true,
    localMcpRecoveryGuideHidden: true,
    handoffGraphLoaded: true,
    editorIsLandingPage: true,
    canonicalAndLegacyRedirectsVerified: true,
    simplifiedSidebarVisible: true,
    projectAndParameterControlsRemoved: true,
    deployedAssetHashes,
    metricsHiddenByDefault: true,
    debugModeRevealsEstimates: true,
    disablingDebugModeHidesEstimates: true,
    runtimeDebugModeDefaultsOff: true,
    compactCentsAndFullBlueRanges: true,
    conservativeMultiTurnBudgetChecked: true,
    runtimeCardPickerChecked: true,
    desktopAndMobileToolbarChecked: true,
    graphRemainsVisibleAfterResize: true,
    conservativeWhisperAllowanceVerified: true,
    auditedElevatorTotalVerified: true,
    runtimeSplitChecks,
    pageErrors: errors,
  };
  if (errors.length) throw new Error(JSON.stringify(errors));
  await writeFile(
    join(root, ".run/browser-acceptance.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(JSON.stringify(report, null, 2));
  await context.close();
} finally {
  await browser.close();
}
