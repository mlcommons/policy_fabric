"""MkDocs hook: put the policy catalog and the composer app into the docs site at build time.

Enable it in docs/mkdocs.yml (the path is relative to that file):

    hooks:
      - hooks/policy_catalog.py

On every build it runs tools/policy_catalog/build_catalog.py over the repo and adds, as site files:

    composer/app/...                 the composer app, from docs/composer/
    composer/app/policy_ui/...       the shared renderer, from tools/pdo_client/webapp/static/policy_ui/
    composer/app/catalog.json        the catalog (credentials, components, cards), generated

The page docs/docs/composer.md is served at composer/ and frames composer/app/. Nothing generated is committed.
The files are added in on_files, not copied after the build, so Markdown links to them pass `mkdocs build --strict`.
Any catalog problem fails the build.
"""
import importlib.util
import json
from pathlib import Path

from mkdocs.exceptions import PluginError
from mkdocs.structure.files import File

REPO = Path(__file__).resolve().parents[2]  # docs/hooks/ -> the repo root
APP = REPO / "docs" / "composer"
RENDERER = REPO / "tools" / "pdo_client" / "webapp" / "static" / "policy_ui"
BUILDER = REPO / "tools" / "policy_catalog" / "build_catalog.py"
SITE_PREFIX = "composer/app"
WATCH = [APP, RENDERER, BUILDER, REPO / "credentials", REPO / "policy_components", REPO / "policy_cards"]


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_catalog", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _add_tree(files, config, src_dir, prefix):
    if not src_dir.is_dir():
        raise PluginError(f"policy_catalog hook: {src_dir.relative_to(REPO)} is missing")
    for path in sorted(p for p in src_dir.rglob("*") if p.is_file()):
        uri = f"{prefix}/{path.relative_to(src_dir).as_posix()}"
        files.append(File.generated(config, uri, abs_src_path=str(path)))


def on_files(files, config, **_):
    catalog, problems = _load_builder().build(REPO / "credentials", REPO / "policy_components", REPO / "policy_cards")
    if problems:
        raise PluginError("policy catalog:\n  " + "\n  ".join(problems))
    _add_tree(files, config, APP, SITE_PREFIX)
    _add_tree(files, config, RENDERER, f"{SITE_PREFIX}/policy_ui")
    files.append(File.generated(config, f"{SITE_PREFIX}/catalog.json",
                                content=json.dumps(catalog, ensure_ascii=False, separators=(",", ":"))))
    return files


def on_serve(server, config, builder, **_):
    for path in WATCH:
        if path.exists():
            server.watch(str(path))
    return server
