// Copyright (c) Microsoft. All rights reserved.
import { useEffect, useRef } from "react";
import {
  displayTranscriptionLanguage,
  mountInputLanguagePicker,
} from "../../../static/handoff/transcription-languages.mjs";

export function InputLanguagePicker({ id, model, value, onChange, disabled, ...props }) {
  const root = useRef(null);
  const change = useRef(onChange);
  change.current = onChange;
  useEffect(() => mountInputLanguagePicker({
    input: root.current.querySelector("input"),
    toggle: root.current.querySelector("button"),
    list: root.current.querySelector('[role="listbox"]'),
    model,
    value,
    onChange: (language) => change.current(language),
  }), [model, value]);
  return (
    <div ref={root} className="input-language-combobox">
      <input {...props} id={id} type="text" role="combobox" disabled={disabled}
        defaultValue={displayTranscriptionLanguage(value)} autoComplete="off" spellCheck={false}
        aria-autocomplete="list" aria-expanded="false" aria-controls={`${id}-languages`}
        placeholder="Search language or locale" />
      <button type="button" className="input-language-toggle" disabled={disabled}
        aria-label="Show input languages">▾</button>
      <div id={`${id}-languages`} className="input-language-options" role="listbox"
        aria-label="Input languages" hidden />
    </div>
  );
}
