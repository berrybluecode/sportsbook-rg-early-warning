-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 02 · Unity Catalog governance hardening (runs after the pipeline)
-- MAGIC
-- MAGIC * **Classification tags** using the workspace's governed tag policies (`classification`, `class.email_address` / `class.name` / `class.date_of_birth`, `system.certification_status`) plus RG-specific tags (`rg_regulatory_scope`, `rg_domain`)
-- MAGIC * **Certified metric view** `rg_kpi_metrics`, so Genie and dashboards share one definition of GGR, turnover and harm rate
-- MAGIC * **Evidence** that the row filters and column masks are attached, plus a live check of what the current user sees

-- COMMAND ----------

-- Parameters :catalog, :schema (and :llm_endpoint) are supplied by the job (see databricks.yml).

-- COMMAND ----------

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

-- COMMAND ----------

-- MAGIC %md ### Certified metric view

-- COMMAND ----------

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

-- COMMAND ----------

-- MAGIC %md ### Evidence: policies attached to tables

-- COMMAND ----------

SELECT table_name, filter_name AS row_filter_function, target_columns
FROM information_schema.row_filters
WHERE table_schema = :schema ORDER BY table_name;

-- COMMAND ----------

SELECT table_name, column_name, mask_name AS column_mask_function
FROM information_schema.column_masks
WHERE table_schema = :schema ORDER BY table_name, column_name;

-- COMMAND ----------

SELECT table_name, tag_name, tag_value FROM information_schema.table_tags
WHERE schema_name = :schema ORDER BY table_name, tag_name;

-- COMMAND ----------

SELECT table_name, column_name, tag_name, tag_value FROM information_schema.column_tags
WHERE schema_name = :schema ORDER BY table_name, column_name;

-- COMMAND ----------

-- MAGIC %md ### Evidence: what the current principal actually sees (global RG analyst: all markets, no PII)

-- COMMAND ----------

SELECT current_user() AS reader, market, count(*) AS players, max(email) AS sample_email, max(date_of_birth) AS sample_dob
FROM silver_players GROUP BY market ORDER BY market;

-- COMMAND ----------

SELECT `Market`, MEASURE(`Turnover EUR`) AS turnover_eur, MEASURE(`GGR EUR`) AS ggr_eur, MEASURE(`Harm Outcomes`) AS harm_outcomes
FROM rg_kpi_metrics GROUP BY `Market` ORDER BY ggr_eur DESC;
