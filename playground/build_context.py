# Copyright (c) Microsoft. All rights reserved.
"""Stage the public Portal and deployment-owned adapters without local state."""
from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_PORTAL_SOURCE = ROOT.parent
ADAPTER = ROOT / "patches" / "portal-hosting.patch"
PORTAL_BASELINE = "native public-MCP support and template versions"


def stage(
    destination: Path,
    *,
    portal_source: Path = DEFAULT_PORTAL_SOURCE,
) -> list[str]:
    destination = destination.resolve()
    portal_source = portal_source.resolve()
    if destination.exists():
        raise ValueError("Build context destination must not already exist.")
    required = [
        portal_source / "portal/requirements.txt",
        portal_source / "portal/demo_server.py",
        portal_source / "portal/template_portal.py",
        portal_source / "portal/templates.config.json",
        portal_source / "shared_mcp/requirements.txt",
        portal_source / "samples/voice_agent_definition.py",
        portal_source / "docs/03_run_samples.md",
        portal_source / "docs/05_connect_real_tools.md",
        portal_source / "docs/06_logic_apps_mcp_servers.md",
    ]
    deployment_files = {
        ROOT / "Dockerfile": Path("portal/hosting/Dockerfile"),
        ROOT / "shared_mcp.Dockerfile": Path("portal/hosting/shared_mcp.Dockerfile"),
        ROOT / "profile.json": Path("portal/hosting/profile.json"),
        ROOT / "runtime/playground.py": Path("portal/playground.py"),
        ROOT / "runtime/playground_server.py": Path("portal/playground_server.py"),
        ROOT / "runtime/playground_usage.py": Path("portal/playground_usage.py"),
    }
    for path in [*required, *deployment_files, ADAPTER]:
        if not path.is_file():
            raise FileNotFoundError(f"Required build input is missing: {path}")
    template_module = ast.parse(
        (portal_source / "portal/template_portal.py").read_text(encoding="utf-8"),
    )
    materializer = next(
        (node for node in template_module.body
         if isinstance(node, ast.FunctionDef) and node.name == "materialize_template"),
        None,
    )
    if materializer is None or "mcp_public" not in {
        argument.arg for argument in (
            *materializer.args.posonlyargs,
            *materializer.args.args,
            *materializer.args.kwonlyargs,
        )
    }:
        raise ValueError("Portal source must include native public-MCP support (mcp_public).")
    config = portal_source / "portal/templates.config.json"
    sample_paths: list[Path] = []
    for entry in json.loads(config.read_text(encoding="utf-8"))["templates"]:
        if entry.get("enabled", True) is False:
            continue
        folder = (config.parent / entry["folder"]).resolve()
        if not folder.is_relative_to(portal_source / "samples"):
            raise ValueError(f"Template folder escapes the samples directory: {folder}")
        agent = folder / (entry.get("agent_file") or "agent.json")
        if not agent.is_file():
            raise FileNotFoundError(f"Required build input is missing: {agent}")
        for path in [agent, *sorted(folder.rglob(agent.name))]:
            if path.is_symlink() or not path.resolve().is_relative_to(folder):
                raise ValueError(f"Template definition escapes its sample folder: {path}")
            sample_paths.append(path)
    paths = [
        *required,
        *sample_paths,
        *sorted((portal_source / "portal").glob("*.py")),
        *sorted((portal_source / "portal").glob("templates.local.config.json")),
        *sorted((portal_source / "portal/static").rglob("*")),
        *sorted((portal_source / "shared_mcp/app").rglob("*.py")),
        *sorted((portal_source / "shared_mcp/data").rglob("*")),
        *sorted((portal_source / "shared_mcp/tests").rglob("*.py")),
    ]
    files = sorted({path for path in paths if path.is_file() and path.suffix != ".map"})
    inputs = []
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(portal_source):
            raise ValueError(f"Build input escapes the Portal source: {path}")
        relative = path.relative_to(portal_source)
        if relative in deployment_files.values():
            raise ValueError(
                f"Portal source still contains deployment-owned input: {relative}"
            )
        inputs.append((path, relative))
    for path, relative in deployment_files.items():
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f"Build input escapes the playground source: {path}")
        inputs.append((path, relative))
    if ADAPTER.is_symlink() or not ADAPTER.resolve().is_relative_to(ROOT):
        raise ValueError(f"Build adapter escapes the playground source: {ADAPTER}")

    destination.mkdir(parents=True, mode=0o700)
    names = []
    for source, relative in inputs:
        target = destination / relative
        if not target.resolve().is_relative_to(destination):
            raise ValueError(f"Build input escapes the build context: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o644)
        for parent in target.parents:
            if parent == destination:
                break
            parent.chmod(0o755)
        names.append(relative.as_posix())
    environment = {
        **os.environ,
        "GIT_CEILING_DIRECTORIES": str(destination.parent),
    }
    try:
        for options in (["--check"], []):
            subprocess.run(
                ["git", "apply", *options, "--", str(ADAPTER)],
                cwd=destination,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
    except FileNotFoundError as error:
        raise RuntimeError("Git is required to apply the hosted Portal adapter.") from error
    except subprocess.CalledProcessError as error:
        raise ValueError(
            "Portal source is incompatible with the hosted adapter "
            f"(verified baseline {PORTAL_BASELINE}): {error.stderr.strip()}"
        ) from error
    for name in names:
        (destination / name).chmod(0o644)
    return sorted(names)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--portal-source",
        type=Path,
        default=DEFAULT_PORTAL_SOURCE,
        help="Public voice-agent repository checkout; never modified by staging.",
    )
    args = parser.parse_args()
    try:
        names = stage(args.destination, portal_source=args.portal_source)
    except (OSError, ValueError, RuntimeError, SyntaxError) as error:
        parser.exit(1, f"Build context failed: {error}\n")
    print(f"Staged {len(names)} allowlisted files in {args.destination.resolve()}")


if __name__ == "__main__":
    main()
