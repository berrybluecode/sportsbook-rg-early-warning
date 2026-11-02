# Lakebase operational serving evidence

Captured 2026-11-02 08:07 UTC from workspace `https://<workspace-host>` as `<builder_email>`.

Lakebase Autoscaling project `rg-early-warning`, endpoint `projects/rg-early-warning/branches/production/endpoints/primary` (host `<lakebase-host>`), database `databricks_postgres`, schema `rg_ops`.

### Postgres version

```sql
SELECT version()
```

| version |
|---|
| PostgreSQL 17.11 (0bfbbeb) on x86_64-pc-linux-gnu, compiled by gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0, 64-bit |

### Case queue by market / tier / status

```sql
SELECT market, risk_tier, status, count(*) cases, min(sla_due_at) earliest_sla FROM rg_ops.risk_cases GROUP BY 1,2,3 ORDER BY 1,2,3
```

| market | risk_tier | status | cases | earliest_sla |
|---|---|---|---|---|
| BR | HIGH | ACTIONED | 1 | 2026-11-02 22:53:07.042402+00:00 |
| BR | HIGH | OPEN | 101 | 2026-11-02 22:53:07.042402+00:00 |
| BR | LOW | CLOSED_NO_ACTION | 195 | 2026-11-04 22:53:07.042402+00:00 |
| BR | MEDIUM | OPEN | 227 | 2026-11-04 22:53:07.042402+00:00 |
| CY | HIGH | OPEN | 34 | 2026-11-02 23:14:38.901051+00:00 |
| CY | LOW | CLOSED_NO_ACTION | 71 | 2026-11-04 22:53:07.042402+00:00 |
| CY | MEDIUM | OPEN | 76 | 2026-11-04 22:53:07.042402+00:00 |
| GR | HIGH | ACTIONED | 1 | 2026-11-02 22:53:07.042402+00:00 |
| GR | HIGH | OPEN | 95 | 2026-11-02 22:53:07.042402+00:00 |
| GR | LOW | CLOSED_NO_ACTION | 189 | 2026-11-04 22:53:07.042402+00:00 |
| GR | MEDIUM | OPEN | 230 | 2026-11-04 22:53:07.042402+00:00 |
| MX | HIGH | OPEN | 58 | 2026-11-02 23:14:38.901051+00:00 |
| MX | LOW | CLOSED_NO_ACTION | 90 | 2026-11-04 22:53:07.042402+00:00 |
| MX | MEDIUM | OPEN | 157 | 2026-11-04 22:53:07.042402+00:00 |
| RO | HIGH | OPEN | 58 | 2026-11-02 22:53:07.042402+00:00 |
| RO | LOW | CLOSED_NO_ACTION | 155 | 2026-11-04 22:53:07.042402+00:00 |
| RO | MEDIUM | OPEN | 121 | 2026-11-04 22:53:07.042402+00:00 |

### Most urgent open HIGH cases

```sql
SELECT player_id, market, round(risk_score::numeric,3) risk_score, recommended_action, urgency, status, sla_due_at FROM rg_ops.risk_cases WHERE status='OPEN' AND risk_tier='HIGH' ORDER BY sla_due_at, risk_score DESC LIMIT 10
```

| player_id | market | risk_score | recommended_action | urgency | status | sla_due_at |
|---|---|---|---|---|---|---|
| P102593 | GR | 0.937 | OUTBOUND_WELLBEING_CALL | WITHIN_24H | OPEN | 2026-11-02 22:53:07.042402+00:00 |
| P103550 | GR | 0.916 | OUTBOUND_WELLBEING_CALL | WITHIN_24H | OPEN | 2026-11-02 22:53:07.042402+00:00 |
| P104370 | BR | 0.916 | OUTBOUND_WELLBEING_CALL | WITHIN_24H | OPEN | 2026-11-02 22:53:07.042402+00:00 |
| P100692 | BR | 0.912 | AFFORDABILITY_REVIEW | WITHIN_24H | OPEN | 2026-11-02 22:53:07.042402+00:00 |
| P107212 | BR | 0.911 | OUTBOUND_WELLBEING_CALL | WITHIN_24H | OPEN | 2026-11-02 22:53:07.042402+00:00 |
| P107222 | RO | 0.910 | OUTBOUND_WELLBEING_CALL | WITHIN_24H | OPEN | 2026-11-02 22:53:07.042402+00:00 |
| P102538 | RO | 0.900 | AFFORDABILITY_REVIEW | WITHIN_24H | OPEN | 2026-11-02 22:53:07.042402+00:00 |
| P107980 | RO | 0.898 | OUTBOUND_WELLBEING_CALL | WITHIN_24H | OPEN | 2026-11-02 22:53:07.042402+00:00 |
| P100622 | BR | 0.893 | OUTBOUND_WELLBEING_CALL | WITHIN_24H | OPEN | 2026-11-02 22:53:07.042402+00:00 |
| P101818 | GR | 0.858 | OUTBOUND_WELLBEING_CALL | WITHIN_24H | OPEN | 2026-11-02 22:53:07.042402+00:00 |

### Interventions written by analysts through the app

```sql
SELECT intervention_id, player_id, action, new_status, analyst, created_at, note FROM rg_ops.interventions ORDER BY created_at DESC LIMIT 20
```

| intervention_id | player_id | action | new_status | analyst | created_at | note |
|---|---|---|---|---|---|---|
| 2 | P103710 | OUTBOUND_WELLBEING_CALL | ACTIONED | <builder_email> | 2026-11-02 08:09:36.036481+00:00 | Evidence run: wellbeing call scheduled, deposit limit discussed. |
| 1 | P100143 | OUTBOUND_WELLBEING_CALL | ACTIONED | <builder_email> | 2026-11-01 23:32:42.344311+00:00 | Evidence run: wellbeing call scheduled, deposit limit discussed. |

### Point lookup latency check (primary key, 20 runs)

From a laptop over the public internet: p50 21.1 ms, max 40.9 ms

### Closed loop: interventions copied back from Lakebase to the Delta audit table by the daily job

```sql
SELECT * FROM <catalog>.sportsbook_rg.rg_intervention_audit ORDER BY created_at DESC
```

| intervention_id | player_id | market | action | note | analyst | new_status | created_at |
|---|---|---|---|---|---|---|---|
| 1 | P100143 | GR | OUTBOUND_WELLBEING_CALL | Evidence run: wellbeing call scheduled, deposit limit discussed. | <builder_email> | ACTIONED | 2026-11-01T23:32:42.344Z |
