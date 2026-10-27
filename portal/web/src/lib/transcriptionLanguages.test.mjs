// Copyright (c) Microsoft. All rights reserved.
import assert from "node:assert/strict";
import test from "node:test";
import {
  VOICE_LIVE_INPUT_LOCALES,
  buildInputTranscription,
  normalizeTranscriptionLanguage,
  transcriptionLanguageError,
  transcriptionLanguageOptions,
} from "../../../static/handoff/transcription-languages.mjs";
import { createBlankDefinition, validateDefinition } from "../../../static/handoff/handoff-core.mjs";

test("the input dropdown offers exactly Auto and Voice Live's 15 locales, including hi-IN", () => {
  assert.equal(VOICE_LIVE_INPUT_LOCALES.length, 15);
  assert.equal(new Set(VOICE_LIVE_INPUT_LOCALES).size, 15);
  const azure = transcriptionLanguageOptions("azure-speech");
  assert.equal(azure.length, 16);
  assert.deepEqual(azure[0], { value: "", label: "Auto", disabled: false });
  assert.match(azure.find((option) => option.value === "hi-IN").label, /Hindi/);
  for (const model of ["mai-transcribe", "mai-transcribe-2", "mai-transcribe-2-streaming"]) {
    const options = transcriptionLanguageOptions(model);
    assert.equal(options.length, 16);
    assert.ok(options.some((option) => option.value === "hi-IN"));
  }
  assert.equal(transcriptionLanguageOptions("whisper-1").length, 16);
  assert.equal(transcriptionLanguageOptions("azure-llm-speech").length, 16);
});

test("Auto omits language and an explicit locale is sent unchanged", () => {
  assert.deepEqual(buildInputTranscription(), { model: "azure-speech" });
  assert.deepEqual(buildInputTranscription("azure-speech", "  "), { model: "azure-speech" });
  assert.deepEqual(buildInputTranscription("azure-speech", "hi-IN"), { model: "azure-speech", language: "hi-IN" });
  assert.equal(buildInputTranscription("azure-speech", "en-IN,hi-IN").language, "en-IN,hi-IN");
  assert.equal(buildInputTranscription("mai-transcribe-2", "hi").language, "hi");
  assert.equal(buildInputTranscription("gpt-4o-transcribe", "hi").language, "hi");
});

test("loading existing language candidates preserves their value and ordering", () => {
  const current = "en-IN,hi-IN";
  assert.equal(transcriptionLanguageOptions("azure-speech", current).length, 16);
  assert.equal(transcriptionLanguageError("azure-speech", current), "");
  assert.equal(transcriptionLanguageError("mai-transcribe-2", "hi-IN"), "");
  assert.equal(transcriptionLanguageError("azure-speech", "en"), "");
  assert.equal(transcriptionLanguageError("azure-speech", "HI-in"), "");
});

test("editable input accepts Auto, language names and loosely formatted locale codes", () => {
  for (const text of ["Auto", "auto", "  AUTO  ", ""]) {
    assert.deepEqual(buildInputTranscription("azure-speech", text), { model: "azure-speech" });
  }
  for (const text of ["Hindi", "Hindi (India)", "hi-IN", "HI_in", "hi in"]) {
    assert.equal(normalizeTranscriptionLanguage("azure-speech", text), "hi-IN");
    assert.equal(buildInputTranscription("azure-speech", text).language, "hi-IN");
  }
  assert.equal(buildInputTranscription("mai-transcribe-2", "Hindi").language, "hi");
  assert.equal(buildInputTranscription("gpt-4o-transcribe", "Hindi").language, "hi");
  assert.equal(buildInputTranscription("azure-speech", "en in, Hindi").language, "en-IN,hi-IN");
  assert.match(transcriptionLanguageError("azure-speech", "English"), /published Voice Live/);
});

test("model-specific invalid input languages are explicit errors, never silently reset", () => {
  assert.match(transcriptionLanguageError("mai-transcribe-2", "en-IN,hi-IN"), /only one/);
  assert.equal(transcriptionLanguageError("gpt-4o-transcribe", "hi-IN"), "");
  assert.match(transcriptionLanguageError("azure-speech", "not-a-locale"), /published Voice Live/);
  assert.match(transcriptionLanguageError("azure-speech", "hi-IN,"), /empty/);
  assert.match(transcriptionLanguageError("azure-speech", VOICE_LIVE_INPUT_LOCALES.slice(0, 11).join(",")), /at most 10/);
  assert.match(transcriptionLanguageError("azure-speech-streaming", ""), /requires an input language/);
  assert.equal(transcriptionLanguageError("azure-speech-streaming", "hi-IN"), "");
  assert.throws(() => buildInputTranscription("mai-transcribe-2", "en,hi"), /only one/);
  const definition = createBlankDefinition();
  definition.audio.input.transcription = { model: "mai-transcribe-2", language: "en,hi" };
  assert.ok(validateDefinition(definition).some((problem) => problem.code === "invalid_transcription_language"));
});
