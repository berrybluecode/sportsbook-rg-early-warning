# 02_governance_hardening (executed)

Task `governance_hardening` · task run 903717946400363 · job run 255598176370280


# 02 · Unity Catalog governance hardening (runs after the pipeline)

* **Classification tags** using the workspace's governed tag policies (`classification`, `class.email_address` / `class.name` / `class.date_of_birth`, `system.certification_status`) plus RG-specific tags (`rg_regulatory_scope`, `rg_domain`)
* **Certified metric view** `rg_kpi_metrics`, so Genie and dashboards share one definition of GGR, turnover and harm rate
* **Evidence** that the row filters and column masks are attached, plus a live check of what the current user sees

```python
-- Parameters :catalog, :schema (and :llm_endpoint) are supplied by the job (see databricks.yml).
```

```python
USE CATALOG IDENTIFIER(:catalog);
USE SCHEMA IDENTIFIER(:schema);

ALTER SCHEMA IDENTIFIER(:schema) SET TAGS ('rg_domain' = 'risk_and_compliance', 'rg_regulatory_scope' = 'responsible_gambling', 'rg_data_origin' = 'synthetic');

-- Governed (policy-backed) tags: classification, class.* PII classes, system.certification_status
ALTER MATERIALIZED VIEW silver_players SET TAGS ('classification' = 'confidential', 'rg_regulatory_scope' = 'responsible_gambling');
ALTER MATERIALIZED VIEW silver_players ALTER COLUMN email SET TAGS ('class.email_address' = '');
ALTER MATERIALIZED VIEW silver_players ALTER COLUMN first_name SET TAGS ('class.name' = '');
ALTER MATERIALIZED VIEW silver_players ALTER COLUMN last_name SET TAGS ('class.name' = '');
ALTER MATERIALIZED VIEW silver_players ALTER COLUMN date_of_birth SET TAGS ('class.date_of_birth' = '');
ALTER MATERIALIZED VIEW gold_player_daily SET TAGS ('classification' = 'confidential', 'rg_regulatory_scope' = 'responsible_gambling', 'system.certification_status' = 'certified');
ALTER MATERIALIZED VIEW gold_market_daily_kpis SET TAGS ('classification' = 'internal', 'system.certification_status' = 'certified');
ALTER MATERIALIZED VIEW silver_bets SET TAGS ('classification' = 'confidential');
ALTER MATERIALIZED VIEW silver_transactions SET TAGS ('classification' = 'confidential', 'rg_regulatory_scope' = 'aml_and_responsible_gambling');
ALTER TABLE rg_market_entitlements SET TAGS ('classification' = 'restricted', 'rg_purpose' = 'access_control');
```

**Output:**

|  |
|

|  |
|

|  |
|

|  |
|

|  |
|

|  |
|

|  |
|

|  |
|

|  |
|

|  |
|

|  |
|

|  |
|

|  |
|

 ### Certified metric view

```python
CREATE OR REPLACE VIEW rg_kpi_metrics
WITH METRICS
LANGUAGE YAML
COMMENT 'Certified sportsbook KPIs by licensed market and day: turnover, GGR, active players, RG harm outcomes.'
AS $$
version: 1.1
source: gold_market_daily_kpis
dimensions:
  - name: Market
    expr: market
    comment: Licensed market (GR, CY, RO, BR, MX)
  - name: KPI Date
    expr: kpi_date
  - name: KPI Month
    expr: date_trunc('MONTH', kpi_date)
measures:
  - name: Turnover EUR
    expr: SUM(turnover_eur)
    comment: Total settled stakes in EUR
  - name: GGR EUR
    expr: SUM(ggr_eur)
    comment: Gross Gaming Revenue = stakes minus payouts, EUR
    synonyms: ['gross gaming revenue', 'gaming revenue']
  - name: Deposits EUR
    expr: SUM(deposits_eur)
  - name: Harm Outcomes
    expr: SUM(self_exclusions + affordability_fails)
    comment: Self-exclusions plus failed affordability checks
    synonyms: ['self exclusions', 'rg incidents']
  - name: Harm Outcomes per 1k Active Player Days
    expr: 1000.0 * SUM(self_exclusions + affordability_fails) / NULLIF(SUM(active_players), 0)
$$;
```

**Output:**

| result |
|---|

 ### Evidence: policies attached to tables

```python
SELECT table_name, filter_name AS row_filter_function, target_columns
FROM information_schema.row_filters
WHERE table_schema = :schema ORDER BY table_name;
```

**Output:**

| table_name | row_filter_function | target_columns |
|---|---|---|
| gold_market_daily_kpis | <catalog>.sportsbook_rg.rg_market_filter | market |
| gold_player_daily | <catalog>.sportsbook_rg.rg_market_filter | market |
| player_risk_scores | <catalog>.sportsbook_rg.rg_market_filter | market |
| rg_case_briefs | <catalog>.sportsbook_rg.rg_market_filter | market |
| silver_players | <catalog>.sportsbook_rg.rg_market_filter | market |

```python
SELECT table_name, column_name, mask_name AS column_mask_function
FROM information_schema.column_masks
WHERE table_schema = :schema ORDER BY table_name, column_name;
```

**Output:**

| table_name | column_name | column_mask_function |
|---|---|---|
| silver_players | date_of_birth | <catalog>.sportsbook_rg.mask_pii_date |
| silver_players | email | <catalog>.sportsbook_rg.mask_pii |
| silver_players | first_name | <catalog>.sportsbook_rg.mask_pii |
| silver_players | last_name | <catalog>.sportsbook_rg.mask_pii |

```python
SELECT table_name, tag_name, tag_value FROM information_schema.table_tags
WHERE schema_name = :schema ORDER BY table_name, tag_name;
```

**Output:**

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

```python
SELECT table_name, column_name, tag_name, tag_value FROM information_schema.column_tags
WHERE schema_name = :schema ORDER BY table_name, column_name;
```

**Output:**

| table_name | column_name | tag_name | tag_value |
|---|---|---|---|
| silver_players | date_of_birth | class.date_of_birth |  |
| silver_players | email | class.email_address |  |
| silver_players | first_name | class.name |  |
| silver_players | last_name | class.name |  |

 ### Evidence: what the current principal actually sees (global RG analyst: all markets, no PII)

```python
SELECT current_user() AS reader, market, count(*) AS players, max(email) AS sample_email, max(date_of_birth) AS sample_dob
FROM silver_players GROUP BY market ORDER BY market;
```

**Output:**

| reader | market | players | sample_email | sample_dob |
|---|---|---|---|---|
| <builder_email> | BR | 3588 | ***MASKED*** | 2008-01-01 |
| <builder_email> | CY | 981 | ***MASKED*** | 2008-01-01 |
| <builder_email> | GR | 3552 | ***MASKED*** | 2008-01-01 |
| <builder_email> | MX | 1851 | ***MASKED*** | 2008-01-01 |
| <builder_email> | RO | 2025 | ***MASKED*** | 2008-01-01 |

```python
SELECT `Market`, MEASURE(`Turnover EUR`) AS turnover_eur, MEASURE(`GGR EUR`) AS ggr_eur, MEASURE(`Harm Outcomes`) AS harm_outcomes
FROM rg_kpi_metrics GROUP BY `Market` ORDER BY ggr_eur DESC;
```

**Output:**

| Market | turnover_eur | ggr_eur | harm_outcomes |
|---|---|---|---|
| GR | 9906816.96 | 675312.3200000005 | 128 |
| BR | 6853434.96 | 480433.59000000014 | 124 |
| MX | 4130569.6300000004 | 281084.1799999999 | 60 |
| RO | 3872848.1899999985 | 275291.35000000003 | 56 |
| CY | 3293606.410000001 | 252054.97999999998 | 28 |
