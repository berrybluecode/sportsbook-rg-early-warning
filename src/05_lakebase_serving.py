# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · Lakebase operational serving (Delta ⇄ Postgres)
# MAGIC
# MAGIC The RG case queue is **operational**: analysts claim cases, log interventions and close them, and SLA timers have to be exact.
# MAGIC That's OLTP work, so it lives in **Lakebase Postgres**. Analytics stays in Delta.
# MAGIC
# MAGIC This notebook runs daily after scoring. It does two things:
# MAGIC 1. **Lakebase → Delta:** copies the analysts' interventions into `rg_intervention_audit`. This gives the regulator an audit trail, and the outcomes can serve as future training labels.
# MAGIC 2. **Delta → Lakebase:** upserts HIGH/MEDIUM risk scores and GenAI briefs into `rg_ops.risk_cases`. Analyst-owned fields (status, assignee) are never overwritten.

# COMMAND ----------

# MAGIC %pip install "psycopg[binary]>=3.2" -q
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("catalog", "main")  # overridden by the job parameter
dbutils.widgets.text("schema", "sportsbook_rg")
dbutils.widgets.text("lakebase_endpoint", "projects/rg-early-warning/branches/production/endpoints/primary")
dbutils.widgets.text("app_sp_role", "")  # app service principal client id, granted DML on rg_ops
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
EP, APP_ROLE = dbutils.widgets.get("lakebase_endpoint"), dbutils.widgets.get("app_sp_role").strip()
spark.sql(f"USE {CATALOG}.{SCHEMA}")

# COMMAND ----------

import psycopg, json
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
host = w.api_client.do("GET", f"/api/2.0/postgres/{EP}")["status"]["hosts"]["host"]
token = w.api_client.do("POST", "/api/2.0/postgres/credentials", body={"endpoint": EP})["token"]
user = w.current_user.me().user_name
conn = psycopg.connect(host=host, dbname="databricks_postgres", user=user, password=token, sslmode="require", autocommit=True)
print("Connected to Lakebase:", conn.execute("select version()").fetchone()[0][:60])

# COMMAND ----------

DDL = """
CREATE SCHEMA IF NOT EXISTS rg_ops;
CREATE TABLE IF NOT EXISTS rg_ops.risk_cases (
  player_id          text PRIMARY KEY,
  market             text NOT NULL,
  risk_score         double precision NOT NULL,
  risk_tier          text NOT NULL,
  reason_codes       text[],
  summary            text,
  recommended_action text,
  urgency            text,
  model_version      int,
  status             text NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','IN_REVIEW','ACTIONED','CLOSED_NO_ACTION')),
  assigned_to        text,
  opened_at          timestamptz NOT NULL DEFAULT now(),
  sla_due_at         timestamptz NOT NULL,
  scored_at          timestamptz NOT NULL,
  updated_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS risk_cases_queue_idx ON rg_ops.risk_cases (market, status, sla_due_at);
CREATE TABLE IF NOT EXISTS rg_ops.interventions (
  intervention_id bigserial PRIMARY KEY,
  player_id       text NOT NULL REFERENCES rg_ops.risk_cases(player_id),
  action          text NOT NULL,
  note            text,
  analyst         text NOT NULL,
  new_status      text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now()
);
"""
conn.execute(DDL)
if APP_ROLE:
    conn.execute(f'GRANT USAGE ON SCHEMA rg_ops TO "{APP_ROLE}"')
    conn.execute(f'GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA rg_ops TO "{APP_ROLE}"')
    conn.execute(f'GRANT USAGE ON ALL SEQUENCES IN SCHEMA rg_ops TO "{APP_ROLE}"')
    print("Granted rg_ops DML to app role", APP_ROLE)

# COMMAND ----------

# MAGIC %md ### 1 · Lakebase → Delta: intervention audit trail

# COMMAND ----------

import pandas as pd
rows = conn.execute("""SELECT i.intervention_id, i.player_id, c.market, i.action, i.note, i.analyst, i.new_status, i.created_at
                       FROM rg_ops.interventions i JOIN rg_ops.risk_cases c USING (player_id)""").fetchall()
cols = ["intervention_id", "player_id", "market", "action", "note", "analyst", "new_status", "created_at"]
spark.sql("""CREATE TABLE IF NOT EXISTS rg_intervention_audit (intervention_id BIGINT, player_id STRING, market STRING, action STRING,
             note STRING, analyst STRING, new_status STRING, created_at TIMESTAMP)
             COMMENT 'Analyst interventions copied from Lakebase rg_ops.interventions: regulatory audit trail and feedback labels.'""")
if rows:
    spark.createDataFrame(pd.DataFrame(rows, columns=cols)).createOrReplaceTempView("new_interventions")
    spark.sql("""MERGE INTO rg_intervention_audit t USING new_interventions s ON t.intervention_id = s.intervention_id
                 WHEN NOT MATCHED THEN INSERT *""")
print("Interventions in Lakebase:", len(rows), "| in Delta audit:", spark.table("rg_intervention_audit").count())

# COMMAND ----------

# MAGIC %md ### 2 · Delta → Lakebase: publish today's cases

# COMMAND ----------

cases = spark.sql("""
  SELECT s.player_id, s.market, s.risk_score, s.risk_tier, s.reason_codes, b.summary, b.recommended_action,
         coalesce(b.urgency, CASE WHEN s.risk_tier = 'HIGH' THEN 'WITHIN_72H' ELSE 'THIS_WEEK' END) AS urgency,
         s.model_version, s.scored_at
  FROM player_risk_scores s LEFT JOIN rg_case_briefs b USING (player_id)
  WHERE s.risk_tier IN ('HIGH', 'MEDIUM')""").toPandas()

UPSERT = """
INSERT INTO rg_ops.risk_cases AS c (player_id, market, risk_score, risk_tier, reason_codes, summary, recommended_action, urgency,
                                    model_version, scored_at, sla_due_at)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
        now() + CASE %s WHEN 'WITHIN_24H' THEN interval '24 hours' WHEN 'WITHIN_72H' THEN interval '72 hours' ELSE interval '7 days' END)
ON CONFLICT (player_id) DO UPDATE SET
  risk_score = EXCLUDED.risk_score, risk_tier = EXCLUDED.risk_tier, reason_codes = EXCLUDED.reason_codes,
  summary = coalesce(EXCLUDED.summary, c.summary), recommended_action = coalesce(EXCLUDED.recommended_action, c.recommended_action),
  urgency = EXCLUDED.urgency, model_version = EXCLUDED.model_version, scored_at = EXCLUDED.scored_at, updated_at = now(),
  -- a more urgent assessment tightens the SLA; it never extends it
  sla_due_at = LEAST(c.sla_due_at, c.opened_at + (EXCLUDED.sla_due_at - now()))
"""
with conn.cursor() as cur:
    cur.executemany(UPSERT, [
        (r.player_id, r.market, float(r.risk_score), r.risk_tier, list(r.reason_codes) if r.reason_codes is not None else [],
         r.summary, r.recommended_action, r.urgency, int(r.model_version), r.scored_at.to_pydatetime(), r.urgency)
        for r in cases.itertuples()])
print(f"Upserted {len(cases):,} cases into Lakebase rg_ops.risk_cases")

# Queue rule: an OPEN case whose player is no longer HIGH/MEDIUM after re-scoring is auto-resolved (attributed to the system)
stale = conn.execute("""UPDATE rg_ops.risk_cases SET status = 'CLOSED_NO_ACTION', risk_tier = 'LOW', assigned_to = 'system:rescore',
                        updated_at = now() WHERE status = 'OPEN' AND NOT (player_id = ANY(%s)) RETURNING player_id""",
                     (list(cases.player_id),)).fetchall()
print(f"Auto-resolved {len(stale):,} open cases that fell below the MEDIUM threshold")

# COMMAND ----------

display(pd.DataFrame(conn.execute("""
  SELECT market, risk_tier, status, count(*) AS cases, min(sla_due_at) AS earliest_sla
  FROM rg_ops.risk_cases GROUP BY 1,2,3 ORDER BY 1,2,3""").fetchall(),
  columns=["market", "risk_tier", "status", "cases", "earliest_sla"]))

# COMMAND ----------

conn.close()
