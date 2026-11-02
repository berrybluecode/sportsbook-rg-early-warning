#!/usr/bin/env python3
"""Create or update the 'Sportsbook RG Early Warning' Genie space and store its id in local.settings.json.

Usage: uv run --with databricks-sdk tools/create_genie_space.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import sys

from databricks.sdk import WorkspaceClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from settings import FQ, PROFILE, ROOT, WAREHOUSE_ID  # noqa: E402
TITLE = "Sportsbook RG Early Warning"
PARENT = "/Shared/sportsbook-rg-early-warning"


def sid(label: str) -> str:
    return uuid5(NAMESPACE_URL, f"sportsbook-rg:{label}").hex


def q(label: str, text: str) -> dict:
    return {"id": sid(f"q:{label}"), "question": [text]}


def ex(label: str, prompt: str, sql: str, guidance: str) -> dict:
    return {"id": sid(f"ex:{label}"), "question": [prompt], "sql": [sql], "usage_guidance": [guidance]}


INSTRUCTIONS = """\
You answer questions for the Responsible Gambling (RG) team and leadership of a multi-market online sportsbook. All data is synthetic.
- Markets are licensed jurisdictions: GR (Greece), CY (Cyprus), RO (Romania), BR (Brazil), MX (Mexico). Amounts are in EUR.
- For turnover, GGR, deposits and harm-outcome KPIs, use the certified metric view rg_kpi_metrics with MEASURE().
- GGR = settled stakes minus payouts. Turnover = total settled stakes.
- A harm outcome is a SELF_EXCLUSION or AFFORDABILITY_CHECK_FAILED event (silver_rg_events.is_harm_outcome).
- player_risk_scores holds today's model score: risk_score is the probability of a harm outcome in the next 28 days; risk_tier HIGH = top 3%, MEDIUM = next 7%.
- reason_codes explain why a player is flagged; rg_case_briefs contains the AI-generated summary and recommended playbook action for HIGH-tier players.
- gold_player_daily is the player x day behaviour table (stakes, net loss, night bets 00:00-05:00, deposits, reversed withdrawals, limit requests).
- Never return names, emails or dates of birth. Refer to players by player_id only.
- RG data is used to protect players. Never suggest marketing, bonuses or retention offers to at-risk players.
- The latest data date is the max activity_date in gold_player_daily; interpret "this week" / "last 28 days" relative to it.
"""

CONFIG = {
    "version": 2,
    "config": {"sample_questions": [
        q("high-by-market", "How many HIGH risk players do we have per market today?"),
        q("ggr-harm", "Show GGR and harm outcomes by market for October 2026"),
        q("top-br", "Which 10 Brazilian players have the highest risk score and why?"),
        q("actions", "What interventions does the AI recommend most often for HIGH risk players?"),
        q("night", "Which market has the highest share of night-time betting among HIGH risk players?"),
    ]},
    "data_sources": {
        "tables": [
            {"identifier": f"{FQ}.gold_market_daily_kpis", "description": ["Market x day business KPIs incl. RG harm outcomes."]},
            {"identifier": f"{FQ}.gold_player_daily", "description": ["Player x day RG behaviour markers (EUR)."]},
            {"identifier": f"{FQ}.player_risk_scores", "description": ["Today's RG harm risk score, tier and reason codes per active player."]},
            {"identifier": f"{FQ}.rg_case_briefs", "description": ["AI-generated case summary and recommended playbook action for HIGH-tier players."]},
            {"identifier": f"{FQ}.silver_rg_events", "description": ["RG control events: limit requests, self-exclusions, affordability fails."]},
        ],
        "metric_views": [
            {"identifier": f"{FQ}.rg_kpi_metrics", "description": ["Certified KPIs: Turnover EUR, GGR EUR, Deposits EUR, Harm Outcomes by Market and date."]},
        ],
    },
    "instructions": {
        "text_instructions": [{"id": sid("instructions"), "content": [l + "\n" for l in INSTRUCTIONS.splitlines()]}],
        "example_question_sqls": [
            ex("high-by-market", "How many HIGH risk players do we have per market today?",
               f"SELECT market, count(*) AS high_risk_players\nFROM {FQ}.player_risk_scores\nWHERE risk_tier = 'HIGH'\nGROUP BY market\nORDER BY high_risk_players DESC",
               "Use player_risk_scores for current risk tiers."),
            ex("ggr-month", "Show GGR and harm outcomes by market for October 2026",
               f"SELECT `Market`, MEASURE(`GGR EUR`) AS ggr_eur, MEASURE(`Harm Outcomes`) AS harm_outcomes\nFROM {FQ}.rg_kpi_metrics\nWHERE `KPI Month` = DATE'2026-10-01'\nGROUP BY `Market`\nORDER BY ggr_eur DESC",
               "Use the certified metric view with MEASURE() for KPIs."),
            ex("top-players", "Which 10 Brazilian players have the highest risk score and why?",
               f"SELECT player_id, round(risk_score, 3) AS risk_score, risk_tier, reason_codes\nFROM {FQ}.player_risk_scores\nWHERE market = 'BR'\nORDER BY risk_score DESC\nLIMIT 10",
               "Explain using reason_codes; never show PII."),
        ],
    },
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=PROFILE)
    args = ap.parse_args()
    w = WorkspaceClient(profile=args.profile)
    w.workspace.mkdirs(PARENT)
    CONFIG["config"]["sample_questions"].sort(key=lambda i: i["id"])
    CONFIG["data_sources"]["tables"].sort(key=lambda i: i["identifier"])
    CONFIG["instructions"]["example_question_sqls"].sort(key=lambda i: i["id"])
    serialized = json.dumps(CONFIG)
    desc = "Ask about Responsible Gambling risk, interventions and market KPIs in plain language. Synthetic data."
    existing = {s.title: s.space_id for s in (w.genie.list_spaces().spaces or [])}
    if TITLE in existing:
        space = w.genie.update_space(existing[TITLE], title=TITLE, description=desc, warehouse_id=WAREHOUSE_ID,
                                     serialized_space=serialized)
    else:
        space = w.genie.create_space(WAREHOUSE_ID, serialized, title=TITLE, description=desc, parent_path=PARENT)
    cfg_path = ROOT / "local.settings.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["genie_space_id"] = space.space_id
    cfg_path.write_text(json.dumps(cfg, indent=2))
    print(f"Genie space {space.space_id} saved to local.settings.json (set BUNDLE_VAR_genie_space_id for the app)")

if __name__ == "__main__":
    main()
