# Derived image for the shared no-auth MCP service: the verified base image plus
# the mock-tool-call pack. Build context: shared_mcp/ (see noauth/README.md).
FROM vaportall3hddama.azurecr.io/voice-agent-noauth-mcp@sha256:88cf811adcf862883473d729cacbb6d8d0d116825726b46acca095863a8cdd57

COPY app/shared_mcp/mock_tool_call /app/shared_mcp/mock_tool_call
COPY noauth/contracts.json /app/contracts.json
COPY tests/test_mock_tool_call.py /app/tests/test_mock_tool_call.py

# The base image ran its self-check as root; as the non-root runtime user the
# interview pack's default OTP directory is not writable, so point it at /tmp.
RUN python -m unittest discover -s /app/tests -v \
    && VA_MCP_OTP_STATE_DIR=/tmp/va-mcp-selfcheck python -m noauth_mcp.selfcheck \
    && rm -rf /tmp/va-mcp-selfcheck
