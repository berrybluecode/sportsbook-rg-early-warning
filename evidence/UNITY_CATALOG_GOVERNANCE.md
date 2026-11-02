# Unity Catalog governance evidence

Captured 2026-11-02 08:07 UTC from workspace `https://<workspace-host>` as `<builder_email>`.

### Tables in the governed schema

```sql
SELECT table_name, table_type, comment FROM <catalog>.information_schema.tables
WHERE table_schema = 'sportsbook_rg' ORDER BY table_name
```

| table_name | table_type | comment |
|---|---|---|
| __materialization_mat_a5c45d50_5690_48cc_b8fb_e9175456c920_bronze_bets_1 | MANAGED | Raw bet ledger as landed (one JSON file per day). Synthetic data. |
| __materialization_mat_a5c45d50_5690_48cc_b8fb_e9175456c920_bronze_fx_rates_1 | MANAGED | Reference FX rates to EUR. |
| __materialization_mat_a5c45d50_5690_48cc_b8fb_e9175456c920_bronze_players_1 | MANAGED | Raw player registry (KYC export) as landed. Contains PII. Synthetic data. |
| __materialization_mat_a5c45d50_5690_48cc_b8fb_e9175456c920_bronze_rg_events_1 | MANAGED | Raw Responsible Gambling control events (limit requests, self-exclusions, affordability fails). Synthetic data. |
| __materialization_mat_a5c45d50_5690_48cc_b8fb_e9175456c920_bronze_transactions_1 | MANAGED | Raw wallet transactions (deposits/withdrawals) as landed. Synthetic data. |
| __materialization_mat_a5c45d50_5690_48cc_b8fb_e9175456c920_gold_market_daily_kpis_1 | MANAGED | Business KPIs per licensed market per day: turnover, GGR, deposits, and RG harm outcomes. |
| __materialization_mat_a5c45d50_5690_48cc_b8fb_e9175456c920_gold_player_daily_1 | MANAGED | Player x day behavioural markers used for RG risk features. One row per player per active day. |
| __materialization_mat_a5c45d50_5690_48cc_b8fb_e9175456c920_silver_bets_1 | MANAGED | Validated, de-duplicated bets converted to EUR. Duplicate bet_ids from replayed exports are removed. |
| __materialization_mat_a5c45d50_5690_48cc_b8fb_e9175456c920_silver_bets_quarantine_1 | MANAGED | Bets rejected by data quality rules (null player, non-positive stake, invalid odds) for steward review. |
| __materialization_mat_a5c45d50_5690_48cc_b8fb_e9175456c920_silver_players_1 | MANAGED | Conformed player dimension. PII is column-masked by Unity Catalog; rows are filtered by market entitlement. |
| __materialization_mat_a5c45d50_5690_48cc_b8fb_e9175456c920_silver_rg_events_1 | MANAGED | Responsible Gambling control events. SELF_EXCLUSION and AFFORDABILITY_CHECK_FAILED are harm outcomes. |
| __materialization_mat_a5c45d50_5690_48cc_b8fb_e9175456c920_silver_transactions_1 | MANAGED | Validated wallet transactions in EUR. |
| bronze_bets | STREAMING_TABLE | Raw bet ledger as landed (one JSON file per day). Synthetic data. |
| bronze_fx_rates | STREAMING_TABLE | Reference FX rates to EUR. |
| bronze_players | STREAMING_TABLE | Raw player registry (KYC export) as landed. Contains PII. Synthetic data. |
| bronze_rg_events | STREAMING_TABLE | Raw Responsible Gambling control events (limit requests, self-exclusions, affordability fails). Synthetic data. |
| bronze_transactions | STREAMING_TABLE | Raw wallet transactions (deposits/withdrawals) as landed. Synthetic data. |
| event_log_a5c45d50_5690_48cc_b8fb_e9175456c920 | MANAGED | None |
| gold_market_daily_kpis | MATERIALIZED_VIEW | Business KPIs per licensed market per day: turnover, GGR, deposits, and RG harm outcomes. |
| gold_player_daily | MATERIALIZED_VIEW | Player x day behavioural markers used for RG risk features. One row per player per active day. |
| player_risk_scores | MANAGED | Daily RG harm risk score per active player (next-28-day probability), tier and reason codes. Model: rg_harm_risk_model@champion. |
| rg_case_briefs | MANAGED | LLM-generated RG case briefs (summary + recommended playbook action) for HIGH-tier players. Advisory only; analyst decides. |
| rg_intervention_audit | MANAGED | Analyst interventions copied from Lakebase rg_ops.interventions: regulatory audit trail and feedback labels. |
| rg_kpi_metrics | METRIC_VIEW | Certified sportsbook KPIs by licensed market and day: turnover, GGR, active players, RG harm outcomes. |
| rg_market_entitlements | MANAGED | Entitlements: which RG analyst may see which licensed market and whether they can see PII. Drives the row filters and column masks. |
| silver_bets | MATERIALIZED_VIEW | Validated, de-duplicated bets converted to EUR. Duplicate bet_ids from replayed exports are removed. |
| silver_bets_quarantine | MATERIALIZED_VIEW | Bets rejected by data quality rules (null player, non-positive stake, invalid odds) for steward review. |
| silver_players | MATERIALIZED_VIEW | Conformed player dimension. PII is column-masked by Unity Catalog; rows are filtered by market entitlement. |
| silver_rg_events | MATERIALIZED_VIEW | Responsible Gambling control events. SELF_EXCLUSION and AFFORDABILITY_CHECK_FAILED are harm outcomes. |
| silver_transactions | MATERIALIZED_VIEW | Validated wallet transactions in EUR. |

### Row filters attached

```sql
SELECT table_name, filter_name, target_columns FROM <catalog>.information_schema.row_filters WHERE table_schema='sportsbook_rg' ORDER BY 1
```

| table_name | filter_name | target_columns |
|---|---|---|
| gold_market_daily_kpis | <catalog>.sportsbook_rg.rg_market_filter | market |
| gold_player_daily | <catalog>.sportsbook_rg.rg_market_filter | market |
| player_risk_scores | <catalog>.sportsbook_rg.rg_market_filter | market |
| rg_case_briefs | <catalog>.sportsbook_rg.rg_market_filter | market |
| silver_players | <catalog>.sportsbook_rg.rg_market_filter | market |

### Column masks attached

```sql
SELECT table_name, column_name, mask_name FROM <catalog>.information_schema.column_masks WHERE table_schema='sportsbook_rg' ORDER BY 1,2
```

| table_name | column_name | mask_name |
|---|---|---|
| silver_players | date_of_birth | <catalog>.sportsbook_rg.mask_pii_date |
| silver_players | email | <catalog>.sportsbook_rg.mask_pii |
| silver_players | first_name | <catalog>.sportsbook_rg.mask_pii |
| silver_players | last_name | <catalog>.sportsbook_rg.mask_pii |

### Governance tags (tables)

```sql
SELECT table_name, tag_name, tag_value FROM <catalog>.information_schema.table_tags WHERE schema_name='sportsbook_rg' ORDER BY 1,2
```

| table_name | tag_name | tag_value |
|---|---|---|
| gold_market_daily_kpis | classification | internal |
| gold_market_daily_kpis | system.certification_status | certified |
| gold_player_daily | classification | confidential |
| gold_player_daily | rg_regulatory_scope | responsible_gambling |
| gold_player_daily | system.certification_status | certified |
| player_risk_scores | classification | confidential |
| player_risk_scores | rg_ml_model | rg_harm_risk_model |
| player_risk_scores | rg_regulatory_scope | responsible_gambling |
| rg_case_briefs | classification | confidential |
| rg_case_briefs | rg_ai_generated | true |
| rg_case_briefs | rg_regulatory_scope | responsible_gambling |
| rg_market_entitlements | classification | restricted |
| rg_market_entitlements | rg_purpose | access_control |
| silver_bets | classification | confidential |
| silver_players | classification | confidential |
| silver_players | rg_regulatory_scope | responsible_gambling |
| silver_transactions | classification | confidential |
| silver_transactions | rg_regulatory_scope | aml_and_responsible_gambling |

### Lineage: upstream sources of the ML score table and case briefs (system.access.table_lineage)

```sql
SELECT DISTINCT source_table_full_name, target_table_full_name, entity_type
FROM system.access.table_lineage
WHERE target_table_full_name IN ('<catalog>.sportsbook_rg.player_risk_scores', '<catalog>.sportsbook_rg.rg_case_briefs', '<catalog>.sportsbook_rg.gold_player_daily', '<catalog>.sportsbook_rg.silver_bets')
  AND source_table_full_name IS NOT NULL AND event_date >= current_date() - 2
ORDER BY target_table_full_name, source_table_full_name
```

| source_table_full_name | target_table_full_name | entity_type |
|---|---|---|
| <catalog>.sportsbook_rg.bronze_players | <catalog>.sportsbook_rg.gold_player_daily | PIPELINE |
| <catalog>.sportsbook_rg.silver_bets | <catalog>.sportsbook_rg.gold_player_daily | PIPELINE |
| <catalog>.sportsbook_rg.silver_rg_events | <catalog>.sportsbook_rg.gold_player_daily | PIPELINE |
| <catalog>.sportsbook_rg.silver_transactions | <catalog>.sportsbook_rg.gold_player_daily | PIPELINE |
| <catalog>.sportsbook_rg.player_risk_scores | <catalog>.sportsbook_rg.rg_case_briefs | JOB |
| <catalog>.sportsbook_rg.bronze_bets | <catalog>.sportsbook_rg.silver_bets | PIPELINE |
| <catalog>.sportsbook_rg.bronze_fx_rates | <catalog>.sportsbook_rg.silver_bets | PIPELINE |

## Row filter + column mask demo

The same query, run as the same user, before and after their entitlement is changed from `ALL` markets to `GR` + `CY` only. The filter is enforced by Unity Catalog, so no app code is involved.

### 1. Entitlement = ALL markets, no PII access

```sql
SELECT current_user() AS reader, market, count(*) AS players, max(email) AS sample_email, max(date_of_birth) AS sample_dob FROM <catalog>.sportsbook_rg.silver_players GROUP BY market ORDER BY market
```

| reader | market | players | sample_email | sample_dob |
|---|---|---|---|---|
| <builder_email> | BR | 3588 | ***MASKED*** | 2008-01-01 |
| <builder_email> | CY | 981 | ***MASKED*** | 2008-01-01 |
| <builder_email> | GR | 3552 | ***MASKED*** | 2008-01-01 |
| <builder_email> | MX | 1851 | ***MASKED*** | 2008-01-01 |
| <builder_email> | RO | 2025 | ***MASKED*** | 2008-01-01 |

### 2. Entitlement switched to GR + CY

```sql
SELECT current_user() AS reader, market, count(*) AS players, max(email) AS sample_email, max(date_of_birth) AS sample_dob FROM <catalog>.sportsbook_rg.silver_players GROUP BY market ORDER BY market
```

| reader | market | players | sample_email | sample_dob |
|---|---|---|---|---|
| <builder_email> | CY | 981 | ***MASKED*** | 2008-01-01 |
| <builder_email> | GR | 3552 | ***MASKED*** | 2008-01-01 |

### 2b. Same restriction applies to the ML scores table

```sql
SELECT market, risk_tier, count(*) players FROM <catalog>.sportsbook_rg.player_risk_scores GROUP BY ALL ORDER BY 1,2
```

| market | risk_tier | players |
|---|---|---|
| CY | HIGH | 34 |
| CY | LOW | 841 |
| CY | MEDIUM | 76 |
| GR | HIGH | 96 |
| GR | LOW | 3095 |
| GR | MEDIUM | 230 |

### 3. Entitlement restored to ALL

```sql
SELECT market, count(*) players FROM <catalog>.sportsbook_rg.silver_players GROUP BY market ORDER BY market
```

| market | players |
|---|---|
| BR | 3588 |
| CY | 981 |
| GR | 3552 |
| MX | 1851 |
| RO | 2025 |
