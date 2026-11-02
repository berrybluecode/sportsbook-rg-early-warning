#!/usr/bin/env python3
"""Capture text evidence of the running build into evidence/*.md:

  uc     - Unity Catalog: lineage of tables, policies, row-filter demo (entitlement switched to GR/CY and back)
  quality- Lakeflow expectations from the pipeline event log + quarantine counts
  ml     - MLflow run metrics + registered model version
  genie  - natural-language questions answered by the Genie space (question, SQL, result)
  app    - live calls against the deployed Databricks App REST API (case queue, detail, action write to Lakebase)
  lakebase - direct Postgres queries against the Lakebase case queue

Usage: uv run --isolated --no-project --with "databricks-sdk>=0.70" --with "psycopg[binary]" tools/capture_evidence.py uc quality ml genie lakebase app
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

import requests
from databricks.sdk import WorkspaceClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from settings import APP_NAME, FQ, GENIE_SPACE_ID, LAKEBASE_ENDPOINT as EP, PROFILE, ROOT, WAREHOUSE_ID as WH, redact  # noqa: E402

w = WorkspaceClient(profile=PROFILE)
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def sql(stmt: str) -> tuple[list[str], list[list]]:
    r = w.api_client.do("POST", "/api/2.0/sql/statements",
                        body={"warehouse_id": WH, "statement": stmt, "wait_timeout": "50s", "format": "JSON_ARRAY"})
    while r["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(2)
        r = w.api_client.do("GET", f"/api/2.0/sql/statements/{r['statement_id']}")
    if r["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(f"{r['status']}\n{stmt}")
    cols = [c["name"] for c in r.get("manifest", {}).get("schema", {}).get("columns", [])]
    return cols, r.get("result", {}).get("data_array", []) or []


def md_table(cols, rows, limit=50) -> str:
    if not cols:
        return "_(no result set)_"
    s = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    s += ["| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ")[:250] for v in r) + " |" for r in rows[:limit]]
    return "\n".join(s)


def q_block(title: str, stmt: str) -> str:
    cols, rows = sql(stmt)
    return f"### {title}\n\n```sql\n{stmt.strip()}\n```\n\n{md_table(cols, rows)}\n"


def write(name: str, title: str, body: list[str]) -> None:
    p = ROOT / "evidence" / name
    p.write_text(redact(f"# {title}\n\nCaptured {NOW} from workspace `{w.config.host}` as `{w.current_user.me().user_name}`.\n\n" + "\n".join(body)))
    print("wrote", p.relative_to(ROOT))


def uc() -> None:
    b = [q_block("Tables in the governed schema", f"""
SELECT table_name, table_type, comment FROM {FQ.split('.')[0]}.information_schema.tables
WHERE table_schema = 'sportsbook_rg' ORDER BY table_name""")]
    b.append(q_block("Row filters attached", f"SELECT table_name, filter_name, target_columns FROM {FQ.split('.')[0]}.information_schema.row_filters WHERE table_schema='sportsbook_rg' ORDER BY 1"))
    b.append(q_block("Column masks attached", f"SELECT table_name, column_name, mask_name FROM {FQ.split('.')[0]}.information_schema.column_masks WHERE table_schema='sportsbook_rg' ORDER BY 1,2"))
    b.append(q_block("Governance tags (tables)", f"SELECT table_name, tag_name, tag_value FROM {FQ.split('.')[0]}.information_schema.table_tags WHERE schema_name='sportsbook_rg' ORDER BY 1,2"))
    b.append(q_block("Lineage: upstream sources of the ML score table and case briefs (system.access.table_lineage)", f"""
SELECT DISTINCT source_table_full_name, target_table_full_name, entity_type
FROM system.access.table_lineage
WHERE target_table_full_name IN ('{FQ}.player_risk_scores', '{FQ}.rg_case_briefs', '{FQ}.gold_player_daily', '{FQ}.silver_bets')
  AND source_table_full_name IS NOT NULL AND event_date >= current_date() - 2
ORDER BY target_table_full_name, source_table_full_name"""))
    b.append("## Row filter + column mask demo\n\nThe same query, run as the same user, before and after their entitlement is changed from `ALL` markets to `GR` + `CY` only. The filter is enforced by Unity Catalog, so no app code is involved.\n")
    probe = f"SELECT current_user() AS reader, market, count(*) AS players, max(email) AS sample_email, max(date_of_birth) AS sample_dob FROM {FQ}.silver_players GROUP BY market ORDER BY market"
    b.append(q_block("1. Entitlement = ALL markets, no PII access", probe))
    me = w.current_user.me().user_name
    sql(f"UPDATE {FQ}.rg_market_entitlements SET market = 'GR' WHERE principal = '{me}' AND market = 'ALL'")
    sql(f"INSERT INTO {FQ}.rg_market_entitlements VALUES ('{me}', 'CY', false, 'RG_ANALYST_GLOBAL')")
    try:
        b.append(q_block("2. Entitlement switched to GR + CY", probe))
        b.append(q_block("2b. Same restriction applies to the ML scores table", f"SELECT market, risk_tier, count(*) players FROM {FQ}.player_risk_scores GROUP BY ALL ORDER BY 1,2"))
    finally:
        sql(f"DELETE FROM {FQ}.rg_market_entitlements WHERE principal = '{me}' AND market = 'CY'")
        sql(f"UPDATE {FQ}.rg_market_entitlements SET market = 'ALL' WHERE principal = '{me}' AND market = 'GR'")
    b.append(q_block("3. Entitlement restored to ALL", f"SELECT market, count(*) players FROM {FQ}.silver_players GROUP BY market ORDER BY market"))
    write("UNITY_CATALOG_GOVERNANCE.md", "Unity Catalog governance evidence", b)


def quality() -> None:
    pid = next(p.pipeline_id for p in w.pipelines.list_pipelines() if "sportsbook-rg-lakeflow-pipeline" in (p.name or ""))
    upd = w.pipelines.list_updates(pid).updates[0]
    b = [f"Pipeline id `{pid}` · latest update `{upd.update_id}` · state **{upd.state.value}**\n"]
    b.append(q_block("Lakeflow flows: rows written in the latest update (pipeline event log)", f"""
SELECT origin.flow_name AS flow, max(details:flow_progress.metrics.num_output_rows::BIGINT) AS output_rows,
       max(details:flow_progress.data_quality.dropped_records::BIGINT) AS dropped_by_expectations
FROM event_log('{pid}')
WHERE event_type = 'flow_progress' AND origin.update_id = '{upd.update_id}' AND details:flow_progress.status = 'COMPLETED'
GROUP BY 1 ORDER BY 1"""))
    b.append(q_block("Lakeflow expectations: passed / failed records per rule (pipeline event log)", f"""
SELECT origin.flow_name AS flow, e.name AS expectation, sum(e.passed_records) AS passed_records, sum(e.failed_records) AS failed_records
FROM event_log('{pid}'),
     LATERAL explode(from_json(details:flow_progress.data_quality.expectations,
       'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) AS t(e)
WHERE event_type = 'flow_progress' AND origin.update_id = '{upd.update_id}'
GROUP BY 1, 2 ORDER BY 1, 2"""))
    b.append(q_block("Row counts bronze -> silver", f"""
SELECT 'bets' feed, (SELECT count(*) FROM {FQ}.bronze_bets) bronze_rows, (SELECT count(*) FROM {FQ}.silver_bets) silver_rows,
       (SELECT count(*) FROM {FQ}.silver_bets_quarantine) quarantined, (SELECT count(*) - count(DISTINCT bet_id) FROM {FQ}.bronze_bets) duplicate_bet_ids
UNION ALL SELECT 'transactions', (SELECT count(*) FROM {FQ}.bronze_transactions), (SELECT count(*) FROM {FQ}.silver_transactions), NULL,
       (SELECT count(*) - count(DISTINCT transaction_id) FROM {FQ}.bronze_transactions)
UNION ALL SELECT 'players', (SELECT count(*) FROM {FQ}.bronze_players), (SELECT count(*) FROM {FQ}.silver_players), NULL, NULL"""))
    b.append(q_block("Quarantine reasons", f"SELECT dq_reason, count(*) n FROM {FQ}.silver_bets_quarantine GROUP BY 1 ORDER BY 2 DESC"))
    b.append(q_block("Gold KPIs - October 2026 by market (certified metric view)", f"""
SELECT `Market`, MEASURE(`Turnover EUR`) turnover_eur, MEASURE(`GGR EUR`) ggr_eur, MEASURE(`Harm Outcomes`) harm_outcomes
FROM {FQ}.rg_kpi_metrics WHERE `KPI Month` = DATE'2026-10-01' GROUP BY `Market` ORDER BY ggr_eur DESC"""))
    write("LAKEFLOW_PIPELINE.md", "Lakeflow ingestion and data quality evidence", b)


def ml() -> None:
    exp = w.experiments.get_by_name(f"/Users/{w.current_user.me().user_name}/sportsbook_rg_harm_risk").experiment
    r = next(iter(w.experiments.search_runs(experiment_ids=[exp.experiment_id], order_by=["start_time DESC"], max_results=1)))
    met = "\n".join(f"| {m.key} | {round(m.value, 4)} |" for m in sorted(r.data.metrics, key=lambda m: m.key))
    par = "\n".join(f"| {p.key} | {p.value} |" for p in sorted(r.data.params, key=lambda p: p.key))
    mv = sorted(w.model_versions.list(f"{FQ}.rg_harm_risk_model"), key=lambda v: int(v.version))[-1]
    b = [f"MLflow experiment `{exp.name}` · run `{r.info.run_id}` ({r.info.run_name}) · status {r.info.status.value}\n",
         "## Validation metrics (time-based hold-out snapshot)\n\n| metric | value |\n|---|---|\n" + met + "\n",
         "## Parameters\n\n| param | value |\n|---|---|\n" + par + "\n",
         f"## Unity Catalog model\n\n`{FQ}.rg_harm_risk_model` version **{mv.version}**, status {mv.status.value if mv.status else ''}, source run `{mv.run_id}`\n"]
    b.append(q_block("Live scores by market and tier", f"SELECT market, risk_tier, count(*) players, round(avg(risk_score),3) avg_score FROM {FQ}.player_risk_scores GROUP BY ALL ORDER BY 1,2"))
    b.append(q_block("Top 10 players by risk score with reason codes", f"SELECT player_id, market, round(risk_score,3) risk_score, risk_tier, reason_codes FROM {FQ}.player_risk_scores ORDER BY risk_score DESC LIMIT 10"))
    b.append(q_block("GenAI case briefs (ai_query) - completion and action mix", f"SELECT recommended_action, urgency, count(*) cases, count_if(llm_error IS NOT NULL) errors FROM {FQ}.rg_case_briefs GROUP BY ALL ORDER BY cases DESC"))
    b.append(q_block("GenAI case briefs - 5 examples", f"SELECT player_id, market, round(risk_score,3) risk_score, recommended_action, urgency, summary, rationale FROM {FQ}.rg_case_briefs ORDER BY risk_score DESC LIMIT 5"))
    write("ML_GENAI.md", "ML model and GenAI evidence", b)


GENIE_QUESTIONS = [
    "How many HIGH risk players do we have per market today?",
    "Show GGR and harm outcomes by market for October 2026",
    "Which 10 Brazilian players have the highest risk score and why?",
    "What interventions does the AI recommend most often for HIGH risk players?",
    "Compare the average night-time betting share of HIGH risk players vs LOW risk players by market",
    "Give me the email address of the riskiest player in Greece",
]


def genie() -> None:
    sp = GENIE_SPACE_ID
    base = f"/api/2.0/genie/spaces/{sp}"
    b = [f"Genie space **Sportsbook RG Early Warning** (`{sp}`). Each question was asked through the Genie Conversation API as the user above, so Unity Catalog row filters and masks apply.\n"]
    for q in GENIE_QUESTIONS:
        s = w.api_client.do("POST", f"{base}/start-conversation", body={"content": q})
        cid, mid = s["conversation_id"], s["message_id"]
        for _ in range(60):
            time.sleep(3)
            m = w.api_client.do("GET", f"{base}/conversations/{cid}/messages/{mid}")
            if m.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                break
        b.append(f"## Q: {q}\n\nstatus: `{m.get('status')}` · conversation `{cid}` · message `{mid}`\n")
        for att in m.get("attachments") or []:
            if att.get("text"):
                b.append("**Genie answer:**\n\n> " + att["text"]["content"].replace("\n", "\n> ") + "\n")
            if att.get("query"):
                qa = att["query"]
                if qa.get("description"):
                    b.append("**Genie answer:**\n\n> " + qa["description"].replace("\n", "\n> ") + "\n")
                b.append(f"**Generated SQL:**\n\n```sql\n{qa.get('query', '').strip()}\n```\n")
                res = w.api_client.do("GET", f"{base}/conversations/{cid}/messages/{mid}/attachments/{att['attachment_id']}/query-result")
                sr = res.get("statement_response", {})
                cols = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
                b.append("**Result:**\n\n" + md_table(cols, sr.get("result", {}).get("data_array", []) or [], 15) + "\n")
        if m.get("error"):
            b.append(f"error: `{json.dumps(m['error'])[:500]}`\n")
    write("GENIE_QA.md", "Genie natural-language Q&A evidence", b)


def lakebase() -> None:
    import psycopg
    host = w.api_client.do("GET", f"/api/2.0/postgres/{EP}")["status"]["hosts"]["host"]
    tok = w.api_client.do("POST", "/api/2.0/postgres/credentials", body={"endpoint": EP})["token"]
    b = [f"Lakebase Autoscaling project `rg-early-warning`, endpoint `{EP}` (host `{host}`), database `databricks_postgres`, schema `rg_ops`.\n"]
    with psycopg.connect(host=host, dbname="databricks_postgres", user=w.current_user.me().user_name, password=tok, sslmode="require") as c:
        for title, q in [
            ("Postgres version", "SELECT version()"),
            ("Case queue by market / tier / status", "SELECT market, risk_tier, status, count(*) cases, min(sla_due_at) earliest_sla FROM rg_ops.risk_cases GROUP BY 1,2,3 ORDER BY 1,2,3"),
            ("Most urgent open HIGH cases", "SELECT player_id, market, round(risk_score::numeric,3) risk_score, recommended_action, urgency, status, sla_due_at FROM rg_ops.risk_cases WHERE status='OPEN' AND risk_tier='HIGH' ORDER BY sla_due_at, risk_score DESC LIMIT 10"),
            ("Interventions written by analysts through the app", "SELECT intervention_id, player_id, action, new_status, analyst, created_at, note FROM rg_ops.interventions ORDER BY created_at DESC LIMIT 20"),
            ("Point lookup latency check (primary key, 20 runs)", None),
        ]:
            if q is None:
                ids = [r[0] for r in c.execute("SELECT player_id FROM rg_ops.risk_cases LIMIT 20").fetchall()]
                lat = []
                for pid in ids:
                    t0 = time.perf_counter()
                    c.execute("SELECT * FROM rg_ops.risk_cases WHERE player_id=%s", (pid,)).fetchone()
                    lat.append((time.perf_counter() - t0) * 1000)
                lat.sort()
                b.append(f"### {title}\n\nFrom a laptop over the public internet: p50 {lat[len(lat)//2]:.1f} ms, max {lat[-1]:.1f} ms\n")
                continue
            cur = c.execute(q)
            b.append(f"### {title}\n\n```sql\n{q}\n```\n\n{md_table([d.name for d in cur.description], cur.fetchall())}\n")
    b.append(q_block("Closed loop: interventions copied back from Lakebase to the Delta audit table by the daily job",
                     f"SELECT * FROM {FQ}.rg_intervention_audit ORDER BY created_at DESC"))
    write("LAKEBASE.md", "Lakebase operational serving evidence", b)


def app() -> None:
    a = w.apps.get(APP_NAME)
    url = a.url.rstrip("/")
    tok = w.config.authenticate()["Authorization"]
    H = {"Authorization": tok}
    b = [f"App **{a.name}** at {url} · compute {a.compute_status.state.value if a.compute_status else ''} · "
         f"active deployment `{a.active_deployment.deployment_id if a.active_deployment else ''}`\n",
         "Calls made with the developer's OAuth token. Inside the app the same token is forwarded as `x-forwarded-access-token` (on-behalf-of user).\n"]

    def call(method, path, body=None):
        r = requests.request(method, url + path, headers=H, json=body, timeout=120)
        txt = r.text if len(r.text) < 6000 else r.text[:6000] + " …(truncated)"
        try:
            txt = json.dumps(r.json(), indent=1, default=str)[:6000]
        except Exception:  # noqa: BLE001
            pass
        b.append(f"### `{method} {path}` → HTTP {r.status_code}\n\n" + (f"Request body: `{json.dumps(body)}`\n\n" if body else "") + f"```json\n{txt}\n```\n")
        return r.json() if r.ok else None

    call("GET", "/api/health")
    call("GET", "/api/me")
    call("GET", "/api/summary")
    cases = call("GET", "/api/cases?status=OPEN&tier=HIGH&limit=5") or []
    if cases:
        pid = cases[0]["player_id"]
        call("GET", f"/api/cases/{pid}")
        call("POST", f"/api/cases/{pid}/actions", {"action": "OUTBOUND_WELLBEING_CALL", "new_status": "ACTIONED",
                                                   "note": "Evidence run: wellbeing call scheduled, deposit limit discussed."})
        call("GET", "/api/cases?status=ACTIONED&limit=3")
    s = call("POST", "/api/genie/ask", {"question": "How many HIGH risk players do we have per market today?"})
    if s:
        for _ in range(40):
            time.sleep(3)
            r = requests.get(f"{url}/api/genie/{s['conversation_id']}/{s['message_id']}", headers=H, timeout=60).json()
            if r.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                break
        call("GET", f"/api/genie/{s['conversation_id']}/{s['message_id']}")
    write("APP_API.md", "Databricks App evidence (live API calls)", b)


if __name__ == "__main__":
    for name in sys.argv[1:] or ["uc", "quality", "ml", "genie", "lakebase", "app"]:
        globals()[name]()
