# Copyright (c) Microsoft. All rights reserved.
"""Deployment-owned entry point, loaded inside the staged Portal image package."""
from __future__ import annotations

import os
from pathlib import Path

from aiohttp import web

try:
    from . import demo_server
    from .playground import HOSTING_ROOT, PlaygroundPolicy
    from .playground_usage import install_usage_telemetry
    from .template_portal import CATALOG_KEY, materialize_template
except ImportError:
    import demo_server
    from playground import HOSTING_ROOT, PlaygroundPolicy
    from playground_usage import install_usage_telemetry
    from template_portal import CATALOG_KEY, materialize_template


def main() -> None:
    os.umask(0o077)
    try:
        configured = PlaygroundPolicy(
            origin=os.environ["VOICE_PLAYGROUND_ORIGIN"],
            mcp_url=os.getenv("VOICE_PLAYGROUND_MCP_URL", ""),
            auth_mode=os.getenv("VOICE_PLAYGROUND_AUTH_MODE", "tenant"),
            tenant_id=os.getenv("VOICE_PLAYGROUND_TENANT_ID", ""),
            cookie_key=os.getenv("VOICE_PLAYGROUND_COOKIE_KEY", ""),
            invitation_hash=os.getenv("VOICE_PLAYGROUND_INVITE_HASH", ""),
            invitation_expires_at=int(os.getenv("VOICE_PLAYGROUND_INVITE_EXPIRES_AT", "0")),
            session_seconds=int(os.getenv("VOICE_PLAYGROUND_SESSION_SECONDS", "300")),
            access_cookie_days=int(os.getenv("VOICE_PLAYGROUND_ACCESS_COOKIE_DAYS", "365")),
            allow_custom_mcp=os.getenv("VOICE_PLAYGROUND_ALLOW_CUSTOM_MCP", "true") != "false",
            enabled=os.getenv("VOICE_PLAYGROUND_ENABLED") == "true",
        )
        args = demo_server.parse_args([
            "--project-endpoint", os.environ["AZURE_VOICE_AGENTS_ENDPOINT"],
            "--credential-mode", "default", "--no-record-sessions",
            "--data-dir", os.getenv("VOICE_PORTAL_DATA_DIR", "/tmp/voice-agent-playground"),
            "--template-profile", str(HOSTING_ROOT / "profile.json"),
            "--model", configured.model,
        ])
        app = demo_server.build_app(args, playground=configured)
        catalog = app[CATALOG_KEY]
        if catalog.errors:
            raise ValueError(f"Invalid hosted template catalog: {catalog.errors}")
        if not any(card["requires_mcp"] for card in catalog.cards()):
            raise ValueError("Hosted playground requires the shared MCP template.")
        configured.configure_catalog(catalog)
        for card in catalog.cards():
            document = catalog.document(card["id"])
            source = catalog.source(card["id"])
            definition = materialize_template(
                document,
                model="",
                voice="",
                mcp_server_url=source.mcp_server_url,
                mcp_connection_id=source.mcp_connection_id,
                mcp_public=source.connection_mode == "public",
            )
            configured.validate_definition(definition)
        install_usage_telemetry(
            app,
            request_id_key=demo_server.REQUEST_ID_KEY,
            template_ids=[card["id"] for card in catalog.cards()],
        )
    except (KeyError, ValueError, web.HTTPException) as error:
        raise SystemExit(f"Playground configuration error: {error}") from None
    demo_server.configure_file_logging(Path(args.data_dir))
    demo_server.LOGGER.info("%s playground: %s", configured.auth_mode, configured.origin)
    web.run_app(app, host="0.0.0.0", port=args.port, print=None, access_log=None)


if __name__ == "__main__":
    main()
