FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHON_DOTENV_DISABLED=1 DEMO_PORT=9527 \
    VOICE_PLAYGROUND_MCP_BASE_URL=https://voice-agent-playground-mcp.example
COPY portal/requirements.txt /app/portal/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade "pip==26.2" \
    && python -m pip install --no-cache-dir -r /app/portal/requirements.txt \
    && rm -r /usr/local/lib/python3.12/ensurepip \
    && useradd --uid 10001 --create-home playground
COPY portal/*.py /app/portal/
COPY portal/static/ /app/portal/static/
COPY portal/templates.config.json /app/portal/templates.config.json
COPY portal/hosting/profile.json /app/portal/hosting/profile.json
COPY samples/ /app/samples/
COPY docs/03_run_samples.md /app/docs/03_run_samples.md
COPY docs/05_connect_real_tools.md /app/docs/05_connect_real_tools.md
COPY docs/06_logic_apps_mcp_servers.md /app/docs/06_logic_apps_mcp_servers.md
USER 10001
RUN python -c "import importlib.metadata, importlib.util; assert importlib.metadata.version('pip') == '26.2'; assert importlib.util.find_spec('ensurepip') is None" \
    && python -m pip check
RUN python -c "import json; from portal.playground import HOSTING_ROOT; from portal.template_portal import DEFAULT_TEMPLATE_CONFIG, TemplateCatalog; import portal.playground_server; catalog = TemplateCatalog(DEFAULT_TEMPLATE_CONFIG, profile_path=HOSTING_ROOT / 'profile.json'); assert not catalog.errors, catalog.errors; expected = {entry['id'] for entry in json.loads(DEFAULT_TEMPLATE_CONFIG.read_text())['templates'] if entry.get('enabled', True)}; assert {card['id'] for card in catalog.cards()} == expected"
EXPOSE 9527
CMD ["python", "-m", "portal.playground_server"]
