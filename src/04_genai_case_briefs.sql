-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 04 · GenAI case briefs for HIGH-risk players (`ai_query`)
-- MAGIC
-- MAGIC An RG analyst currently spends about 15–20 minutes per case reading raw ledgers before deciding what to do.
-- MAGIC For every HIGH-tier player, a Foundation Model on Databricks writes a short, **non-identifying** brief from the governed features and reason codes.
-- MAGIC It also recommends one intervention from the operator's RG playbook. The model returns JSON; SQL parses it and rejects any action that isn't in the playbook. The analyst always makes the final decision in the app (human in the loop).

-- COMMAND ----------

-- Parameters :catalog, :schema (and :llm_endpoint) are supplied by the job (see databricks.yml).

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalog);
USE SCHEMA IDENTIFIER(:schema);

DROP TABLE IF EXISTS rg_case_briefs;

CREATE TABLE rg_case_briefs
COMMENT 'LLM-generated RG case briefs (summary + recommended playbook action) for HIGH-tier players. Advisory only; analyst decides.'
AS
WITH cases AS (
  SELECT player_id, market, risk_score, reason_codes, age, bets_28d, round(stake_28d) stake_28d, round(net_loss_28d) net_loss_28d,
         round(stake_trend, 1) stake_trend, round(night_share_28d, 2) night_share_28d, deposits_28d,
         reversed_withdrawals_28d, limit_requests_28d, round(deposit_limit_utilisation, 2) deposit_limit_utilisation
  FROM player_risk_scores WHERE risk_tier = 'HIGH'
),
llm AS (
  SELECT *, ai_query(
    :llm_endpoint,
    concat(
      'You are a Responsible Gambling analyst assistant at a licensed online sportsbook. ',
      'Write for a trained RG analyst. Do not invent facts beyond the data. Never include names or contact details. ',
      'Playbook actions (choose exactly one): SAFER_GAMBLING_MESSAGE, OUTBOUND_WELLBEING_CALL, MANDATORY_COOL_OFF_24H, ',
      'DEPOSIT_LIMIT_REDUCTION, AFFORDABILITY_REVIEW, ESCALATE_TO_COMPLIANCE. ',
      'Use AFFORDABILITY_REVIEW or ESCALATE_TO_COMPLIANCE when net loss or deposit-limit utilisation is high, ',
      'OUTBOUND_WELLBEING_CALL for strong escalation or loss chasing, SAFER_GAMBLING_MESSAGE only for mild signals. ',
      'Player data (28-day window, EUR): ', to_json(named_struct(
        'market', market, 'risk_score', round(risk_score, 3), 'risk_markers', reason_codes, 'age', age,
        'bets_28d', bets_28d, 'stake_28d', stake_28d, 'net_loss_28d', net_loss_28d, 'stake_trend_x', stake_trend,
        'night_share', night_share_28d, 'deposits_28d', deposits_28d, 'reversed_withdrawals_28d', reversed_withdrawals_28d,
        'deposit_limit_increase_requests_28d', limit_requests_28d, 'deposit_limit_utilisation', deposit_limit_utilisation)),
      ' Respond with ONLY a JSON object, no markdown, with keys: "summary" (2-3 sentences), "recommended_action" (one playbook action), ',
      '"rationale" (1 sentence), "urgency" (one of WITHIN_24H, WITHIN_72H, THIS_WEEK).'
    ),
    failOnError => false
  ) AS resp
  FROM cases
)
SELECT player_id, market, risk_score, reason_codes,
       b.summary,
       CASE WHEN b.recommended_action IN ('SAFER_GAMBLING_MESSAGE','OUTBOUND_WELLBEING_CALL','MANDATORY_COOL_OFF_24H',
                 'DEPOSIT_LIMIT_REDUCTION','AFFORDABILITY_REVIEW','ESCALATE_TO_COMPLIANCE') THEN b.recommended_action END AS recommended_action,
       b.rationale,
       CASE WHEN b.urgency IN ('WITHIN_24H','WITHIN_72H','THIS_WEEK') THEN b.urgency END AS urgency,
       coalesce(llm_error, CASE WHEN b.summary IS NULL THEN 'unparseable response' END) AS llm_error,
       :llm_endpoint AS llm_endpoint, current_timestamp() AS generated_at
FROM (
  SELECT *, from_json(regexp_extract(resp.result, '(?s)(\\{.*\\})', 1),
                      'summary STRING, recommended_action STRING, rationale STRING, urgency STRING') AS b,
         resp.errorMessage AS llm_error
  FROM llm
);

-- COMMAND ----------

ALTER TABLE rg_case_briefs SET ROW FILTER rg_market_filter ON (market);
ALTER TABLE rg_case_briefs SET TAGS ('classification' = 'confidential', 'rg_ai_generated' = 'true', 'rg_regulatory_scope' = 'responsible_gambling');

-- COMMAND ----------

SELECT count(*) AS briefs, count_if(llm_error IS NULL AND summary IS NOT NULL) AS succeeded, count_if(llm_error IS NOT NULL) AS failed
FROM rg_case_briefs;

-- COMMAND ----------

SELECT recommended_action, urgency, count(*) AS cases FROM rg_case_briefs GROUP BY ALL ORDER BY cases DESC;

-- COMMAND ----------

SELECT player_id, market, round(risk_score, 3) AS risk_score, recommended_action, urgency, summary
FROM rg_case_briefs ORDER BY risk_score DESC LIMIT 5;
