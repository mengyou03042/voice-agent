// Copyright (c) Microsoft. All rights reserved.
// Voice Live's published input languages, verified 2026-10-27:
// https://learn.microsoft.com/azure/ai-services/speech-service/voice-live-language-support
// The portal intentionally offers only Voice Live's 15 multilingual input locales.
export const INPUT_LANGUAGE_HINT =
  "Auto detects the input language. For more accurate recognition, select the language you expect.";
export const INPUT_LANGUAGE_SOURCE =
  "https://learn.microsoft.com/azure/ai-services/speech-service/voice-live-language-support";

export const VOICE_LIVE_INPUT_LOCALES = Object.freeze(`
zh-CN en-AU en-CA en-IN en-GB en-US fr-CA fr-FR de-DE hi-IN
it-IT ja-JP ko-KR es-MX es-ES
`.trim().split(/\s+/));
const AZURE_MODELS = new Set(["azure-speech", "azure-speech-streaming", "azure-fast-transcription"]);
const languageNames = new Intl.DisplayNames(["en"], { type: "language" });

export function transcriptionLanguageOptions(model) {
  const options = VOICE_LIVE_INPUT_LOCALES.map((value) => ({
    value,
    label: `${languageNames.of(value)} - ${value}`,
  })).sort((left, right) => left.label.localeCompare(right.label));
  return [
    { value: "", label: "Auto", disabled: model === "azure-speech-streaming" },
    ...options,
  ];
}

function foldedLanguage(value) {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}

export function displayTranscriptionLanguage(language = "") {
  if (!language || /^auto$/i.test(language)) return "Auto";
  const exact = VOICE_LIVE_INPUT_LOCALES.find((locale) => foldedLanguage(locale) === foldedLanguage(language));
  if (exact) return exact;
  const defaults = { en: "en-US", fr: "fr-FR", es: "es-ES" };
  return defaults[language] || VOICE_LIVE_INPUT_LOCALES.find((locale) => locale.split("-")[0] === language) || language;
}

export function normalizeTranscriptionLanguage(model, language = "") {
  if (typeof language !== "string") return language;
  if (!language.trim() || /^auto$/i.test(language.trim())) return "";
  const supported = VOICE_LIVE_INPUT_LOCALES;
  return language.split(",").map((part) => {
    const text = part.trim();
    const query = foldedLanguage(text);
    const exact = supported.find((value) => foldedLanguage(value) === query);
    if (exact) return AZURE_MODELS.has(model) ? exact : exact.split("-")[0];
    const named = supported.filter((value) => [
      languageNames.of(value),
      languageNames.of(value.split("-")[0]),
      `${languageNames.of(value)} ${value}`,
    ].some((name) => foldedLanguage(name) === query));
    if (named.length === 1) return AZURE_MODELS.has(model) ? named[0] : named[0].split("-")[0];
    return text;
  }).join(",");
}

export function transcriptionLanguageError(model, language) {
  if (language != null && typeof language !== "string") return "Input language must be a language code.";
  language = normalizeTranscriptionLanguage(model, language);
  if (!language?.trim()) {
    return model === "azure-speech-streaming"
      ? "Streaming Azure Speech requires an input language. Select a locale instead of Auto."
      : "";
  }
  const codes = language.split(",").map((code) => code.trim());
  if (codes.some((code) => !code)) return "Input language contains an empty language code.";
  if (codes.length > (AZURE_MODELS.has(model) || model === "azure-llm-speech" ? 10 : 1)) {
    return AZURE_MODELS.has(model) || model === "azure-llm-speech"
      ? "Select at most 10 input locales."
      : `${model} supports only one input language. Select a language or Auto.`;
  }
  const supported = VOICE_LIVE_INPUT_LOCALES;
  const invalid = codes.find((code) => !supported.some((value) => (
    value.toLowerCase() === code.toLowerCase()
    || (AZURE_MODELS.has(model)
      ? !code.includes("-") && value.split("-")[0] === code.toLowerCase()
      : value.split("-")[0] === code.split("-")[0].toLowerCase())
  )));
  return invalid
    ? `${invalid} is not in the published Voice Live input language list for ${model}. Select a listed language or Auto.`
    : "";
}

export function buildInputTranscription(model = "azure-speech", language = "") {
  language = normalizeTranscriptionLanguage(model, language);
  const error = transcriptionLanguageError(model, language);
  if (error) throw new Error(error);
  return { model, ...(language?.trim() ? { language: language.trim() } : {}) };
}

export function mountInputLanguagePicker({ input, toggle, list, model, value, onChange, onError = () => {} }) {
  const controller = new AbortController();
  const options = transcriptionLanguageOptions(model).filter((option) => !option.disabled);
  let visible = options;
  let active = -1;
  input.value = displayTranscriptionLanguage(value);
  const close = () => {
    list.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  };
  const render = (query = "") => {
    const text = foldedLanguage(query);
    visible = options.filter((option) => foldedLanguage(option.label).includes(text));
    active = -1;
    list.replaceChildren(...visible.map((option, index) => {
      const button = input.ownerDocument.createElement("button");
      button.type = "button";
      button.id = `${list.id}-${index}`;
      button.setAttribute("role", "option");
      button.setAttribute("aria-selected", String((option.value || "Auto") === input.value));
      button.dataset.languageValue = option.value;
      button.textContent = option.label;
      return button;
    }));
    if (!visible.length) {
      const message = input.ownerDocument.createElement("p");
      message.textContent = "No matching language.";
      list.append(message);
    }
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
  };
  const commit = (text) => {
    const language = normalizeTranscriptionLanguage(model, text);
    const error = transcriptionLanguageError(model, language);
    input.setAttribute("aria-invalid", String(Boolean(error)));
    onError(error);
    close();
    input.value = displayTranscriptionLanguage(language);
    if (language !== normalizeTranscriptionLanguage(model, value)) onChange(language);
  };
  const listen = (element, event, handler) => element.addEventListener(event, handler, { signal: controller.signal });
  listen(input, "focus", () => { render(); input.select(); });
  listen(input, "input", () => { render(input.value); onError(""); });
  listen(input, "blur", () => commit(input.value));
  listen(toggle, "mousedown", (event) => event.preventDefault());
  listen(toggle, "click", () => {
    if (list.hidden) { input.focus(); render(); } else close();
  });
  listen(list, "mousedown", (event) => event.preventDefault());
  listen(list, "click", (event) => {
    const button = event.target.closest("[data-language-value]");
    if (button) commit(button.dataset.languageValue);
  });
  listen(input, "keydown", (event) => {
    if (event.key === "Escape") { close(); return; }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (list.hidden) render();
      if (!visible.length) return;
      active = active < 0
        ? (event.key === "ArrowDown" ? 0 : visible.length - 1)
        : (active + (event.key === "ArrowDown" ? 1 : -1) + visible.length) % visible.length;
      [...list.children].forEach((item, index) => item.setAttribute("aria-selected", String(index === active)));
      input.setAttribute("aria-activedescendant", `${list.id}-${active}`);
      list.children[active].scrollIntoView({ block: "nearest" });
    } else if (event.key === "Enter") {
      event.preventDefault();
      commit(active >= 0 ? visible[active].value : input.value);
    }
  });
  return () => controller.abort();
}
