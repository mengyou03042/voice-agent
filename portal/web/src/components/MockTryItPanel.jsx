// Copyright (c) Microsoft. All rights reserved.
import { useEffect, useState } from "react";

const MOCK_TOOL_PREFIX = "mock_tool_call_";

// A Template published from the Editor carries its id in the version metadata; its tools
// still point at the shared mock MCP server until the user connects real systems.
export function mockTemplateId(agent) {
  const templateId = String(agent?.metadata?.source_template_id || "").trim();
  if (!templateId) return "";
  return JSON.stringify(agent?.definition || {}).includes(MOCK_TOOL_PREFIX) ? templateId : "";
}

function renderInline(text) {
  return text.split("`").map((part, index) => (index % 2 ? <code key={index}>{part}</code> : part));
}

export function MockTryItPanel({ agent }) {
  const templateId = mockTemplateId(agent);
  const [turns, setTurns] = useState([]);

  useEffect(() => {
    setTurns([]);
    if (!templateId) return undefined;
    const controller = new AbortController();
    fetch(`/api/templates/${encodeURIComponent(templateId)}/try-it`, { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => setTurns(Array.isArray(payload?.turns) ? payload.turns : []))
      .catch(() => {});
    return () => controller.abort();
  }, [templateId]);

  if (!templateId || !turns.length) return null;
  return (
    <details className="mock-try-it" open>
      <summary>Test data for mock tools</summary>
      <p>
        This Agent uses mock tools with fixed, fictional test data. Use the names, numbers, and
        answers below; other values are treated as unknown records.
      </p>
      <ol>
        {turns.map((turn, index) => <li key={index}>{renderInline(turn)}</li>)}
      </ol>
    </details>
  );
}
