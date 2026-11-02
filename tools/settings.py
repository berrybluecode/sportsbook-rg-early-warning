"""Workspace-specific settings, loaded from the gitignored local.settings.json (see local.settings.example.json).

Committed evidence is passed through redact() so workspace hosts, ids, catalog and user names become placeholders.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "local.settings.json").read_text())
PROFILE = S["profile"]
CATALOG = S["catalog"]
FQ = f"{CATALOG}.sportsbook_rg"
WAREHOUSE_ID = S["warehouse_id"]
LAKEBASE_ENDPOINT = f"projects/{S['lakebase_project']}/branches/production/endpoints/primary"
APP_NAME = S["app_name"]
GENIE_SPACE_ID = S.get("genie_space_id", "")


def redact(text: str) -> str:
    for real, placeholder in sorted(S.get("redact", {}).items(), key=lambda kv: -len(kv[0])):
        text = text.replace(real, placeholder)
    return text
