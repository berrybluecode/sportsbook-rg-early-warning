-- Lakeflow Spark Declarative Pipeline: Sportsbook Responsible Gambling (RG) early warning
-- Raw operator exports in a UC volume -> bronze (Auto Loader) -> silver (expectations, FX, dedup) -> gold features & KPIs
-- Config: ${landing_root}, ${catalog}, ${schema}

-- ============================ BRONZE (incremental Auto Loader) ============================

CREATE OR REFRESH STREAMING TABLE bronze_players
COMMENT 'Raw player registry (KYC export) as landed. Contains PII. Synthetic data.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('${landing_root}/players/', format => 'csv', header => true,
  schemaHints => 'daily_deposit_limit_local DOUBLE, marketing_opt_in BOOLEAN');

CREATE OR REFRESH STREAMING TABLE bronze_bets
COMMENT 'Raw bet ledger as landed (one JSON file per day). Synthetic data.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('${landing_root}/bets/', format => 'json',
  schemaHints => 'stake DOUBLE, odds DOUBLE, payout DOUBLE, placed_at STRING');

CREATE OR REFRESH STREAMING TABLE bronze_transactions
COMMENT 'Raw wallet transactions (deposits/withdrawals) as landed. Synthetic data.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('${landing_root}/transactions/', format => 'json',
  schemaHints => 'amount DOUBLE, created_at STRING');

CREATE OR REFRESH STREAMING TABLE bronze_rg_events
COMMENT 'Raw Responsible Gambling control events (limit requests, self-exclusions, affordability fails). Synthetic data.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('${landing_root}/rg_events/', format => 'json');

CREATE OR REFRESH STREAMING TABLE bronze_fx_rates
COMMENT 'Reference FX rates to EUR.'
AS SELECT *, current_timestamp() AS ingested_at
FROM STREAM read_files('${landing_root}/reference/', format => 'csv', header => true, schemaHints => 'rate_to_eur DOUBLE');

-- ============================ SILVER (governed, validated) ============================

CREATE OR REFRESH MATERIALIZED VIEW silver_players (
  player_id STRING COMMENT 'Synthetic player identifier',
  first_name STRING MASK ${catalog}.${schema}.mask_pii COMMENT 'PII - masked unless the reader has pii_access',
  last_name STRING MASK ${catalog}.${schema}.mask_pii COMMENT 'PII - masked unless the reader has pii_access',
  email STRING MASK ${catalog}.${schema}.mask_pii COMMENT 'PII - masked unless the reader has pii_access',
  date_of_birth DATE MASK ${catalog}.${schema}.mask_pii_date COMMENT 'PII - masked unless the reader has pii_access',
  age INT COMMENT 'Age in years at pipeline run (non-identifying)',
  market STRING COMMENT 'Licensed market (GR, CY, RO, BR, MX)',
  currency STRING,
  registration_date DATE,
  tenure_days INT,
  kyc_status STRING,
  marketing_opt_in BOOLEAN,
  daily_deposit_limit_eur DOUBLE,
  CONSTRAINT valid_market EXPECT (market IN ('GR','CY','RO','BR','MX')) ON VIOLATION DROP ROW,
  CONSTRAINT adult EXPECT (age >= 18) ON VIOLATION DROP ROW
)
COMMENT 'Conformed player dimension. PII is column-masked by Unity Catalog; rows are filtered by market entitlement.'
WITH ROW FILTER ${catalog}.${schema}.rg_market_filter ON (market)
AS SELECT
  p.player_id, p.first_name, p.last_name, p.email,
  to_date(p.date_of_birth) AS date_of_birth,
  CAST(floor(datediff(DATE'2026-10-31', to_date(p.date_of_birth)) / 365.25) AS INT) AS age,
  p.market, p.currency, to_date(p.registration_date) AS registration_date,
  datediff(DATE'2026-10-31', to_date(p.registration_date)) AS tenure_days,
  p.kyc_status, p.marketing_opt_in,
  round(p.daily_deposit_limit_local * fx.rate_to_eur, 2) AS daily_deposit_limit_eur
FROM bronze_players p JOIN bronze_fx_rates fx USING (currency);

CREATE OR REFRESH MATERIALIZED VIEW silver_bets (
  CONSTRAINT valid_player EXPECT (player_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT positive_stake EXPECT (stake > 0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_odds EXPECT (odds >= 1.01) ON VIOLATION DROP ROW,
  CONSTRAINT settled_status EXPECT (status IN ('WON','LOST'))
)
COMMENT 'Validated, de-duplicated bets converted to EUR. Duplicate bet_ids from replayed exports are removed.'
AS SELECT
  b.bet_id, b.player_id, to_timestamp(b.placed_at) AS placed_at, to_date(to_timestamp(b.placed_at)) AS bet_date,
  hour(to_timestamp(b.placed_at)) AS bet_hour, b.sport, b.bet_type, b.channel, b.status, b.odds,
  b.stake, b.payout, b.currency,
  round(b.stake * fx.rate_to_eur, 2) AS stake_eur,
  round(b.payout * fx.rate_to_eur, 2) AS payout_eur
FROM bronze_bets b JOIN bronze_fx_rates fx USING (currency)
QUALIFY row_number() OVER (PARTITION BY b.bet_id ORDER BY b.ingested_at) = 1;

CREATE OR REFRESH MATERIALIZED VIEW silver_bets_quarantine
COMMENT 'Bets rejected by data quality rules (null player, non-positive stake, invalid odds) for steward review.'
AS SELECT *, CASE WHEN player_id IS NULL THEN 'NULL_PLAYER_ID' WHEN stake <= 0 THEN 'NON_POSITIVE_STAKE' ELSE 'INVALID_ODDS' END AS dq_reason
FROM bronze_bets WHERE player_id IS NULL OR stake <= 0 OR odds < 1.01;

CREATE OR REFRESH MATERIALIZED VIEW silver_transactions (
  CONSTRAINT valid_player EXPECT (player_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT positive_amount EXPECT (amount > 0) ON VIOLATION DROP ROW,
  CONSTRAINT known_type EXPECT (type IN ('DEPOSIT','WITHDRAWAL')) ON VIOLATION DROP ROW
)
COMMENT 'Validated wallet transactions in EUR.'
AS SELECT t.transaction_id, t.player_id, to_timestamp(t.created_at) AS created_at, to_date(to_timestamp(t.created_at)) AS tx_date,
  t.type, t.status, t.payment_method, t.amount, t.currency, round(t.amount * fx.rate_to_eur, 2) AS amount_eur
FROM bronze_transactions t JOIN bronze_fx_rates fx USING (currency)
QUALIFY row_number() OVER (PARTITION BY t.transaction_id ORDER BY t.ingested_at) = 1;

CREATE OR REFRESH MATERIALIZED VIEW silver_rg_events (
  CONSTRAINT valid_player EXPECT (player_id IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Responsible Gambling control events. SELF_EXCLUSION and AFFORDABILITY_CHECK_FAILED are harm outcomes.'
AS SELECT event_id, player_id, to_date(event_date) AS event_date, event_type, source,
  event_type IN ('SELF_EXCLUSION','AFFORDABILITY_CHECK_FAILED') AS is_harm_outcome
FROM bronze_rg_events;

-- ============================ GOLD (features & business KPIs) ============================

CREATE OR REFRESH MATERIALIZED VIEW gold_player_daily (
  player_id STRING, market STRING, activity_date DATE,
  bets BIGINT, stake_eur DOUBLE, payout_eur DOUBLE, net_loss_eur DOUBLE, max_stake_eur DOUBLE,
  night_bets BIGINT COMMENT 'Bets placed between 00:00 and 04:59 local time',
  live_bets BIGINT, deposits BIGINT, deposit_eur DOUBLE, withdrawals BIGINT, withdrawal_eur DOUBLE,
  reversed_withdrawals BIGINT COMMENT 'Withdrawals the player cancelled to keep playing - key RG marker',
  limit_increase_requests BIGINT, harm_outcomes BIGINT
)
COMMENT 'Player x day behavioural markers used for RG risk features. One row per player per active day.'
WITH ROW FILTER ${catalog}.${schema}.rg_market_filter ON (market)
AS WITH b AS (
  SELECT player_id, bet_date AS d, count(*) bets, sum(stake_eur) stake_eur, sum(payout_eur) payout_eur, max(stake_eur) max_stake_eur,
         count_if(bet_hour < 5) night_bets, count_if(bet_type = 'LIVE') live_bets
  FROM silver_bets GROUP BY ALL),
t AS (
  SELECT player_id, tx_date AS d,
         count_if(type='DEPOSIT') deposits, sum(CASE WHEN type='DEPOSIT' THEN amount_eur END) deposit_eur,
         count_if(type='WITHDRAWAL' AND status='COMPLETED') withdrawals,
         sum(CASE WHEN type='WITHDRAWAL' AND status='COMPLETED' THEN amount_eur END) withdrawal_eur,
         count_if(type='WITHDRAWAL' AND status='REVERSED') reversed_withdrawals
  FROM silver_transactions GROUP BY ALL),
r AS (
  SELECT player_id, event_date AS d, count_if(event_type='DEPOSIT_LIMIT_INCREASE_REQUEST') limit_increase_requests,
         count_if(is_harm_outcome) harm_outcomes
  FROM silver_rg_events GROUP BY ALL),
k AS (SELECT player_id, d FROM b UNION SELECT player_id, d FROM t UNION SELECT player_id, d FROM r)
SELECT k.player_id, p.market, k.d AS activity_date,
  coalesce(bets,0) bets, round(coalesce(stake_eur,0),2) stake_eur, round(coalesce(payout_eur,0),2) payout_eur,
  round(coalesce(stake_eur,0) - coalesce(payout_eur,0),2) net_loss_eur, coalesce(max_stake_eur,0) max_stake_eur,
  coalesce(night_bets,0) night_bets, coalesce(live_bets,0) live_bets,
  coalesce(deposits,0) deposits, round(coalesce(deposit_eur,0),2) deposit_eur,
  coalesce(withdrawals,0) withdrawals, round(coalesce(withdrawal_eur,0),2) withdrawal_eur,
  coalesce(reversed_withdrawals,0) reversed_withdrawals,
  coalesce(limit_increase_requests,0) limit_increase_requests, coalesce(harm_outcomes,0) harm_outcomes
FROM k
JOIN (SELECT player_id, market FROM bronze_players) p USING (player_id)
LEFT JOIN b ON b.player_id = k.player_id AND b.d = k.d
LEFT JOIN t ON t.player_id = k.player_id AND t.d = k.d
LEFT JOIN r ON r.player_id = k.player_id AND r.d = k.d;

CREATE OR REFRESH MATERIALIZED VIEW gold_market_daily_kpis (
  market STRING, kpi_date DATE,
  active_players BIGINT COMMENT 'Distinct players with at least one bet',
  bets BIGINT, turnover_eur DOUBLE COMMENT 'Total settled stakes in EUR',
  ggr_eur DOUBLE COMMENT 'Gross Gaming Revenue = stakes - payouts (EUR)',
  deposits_eur DOUBLE, self_exclusions BIGINT, affordability_fails BIGINT, limit_increase_requests BIGINT
)
COMMENT 'Business KPIs per licensed market per day: turnover, GGR, deposits, and RG harm outcomes.'
WITH ROW FILTER ${catalog}.${schema}.rg_market_filter ON (market)
AS SELECT g.market, g.activity_date AS kpi_date,
  count_if(g.bets > 0) active_players, sum(g.bets) bets, round(sum(g.stake_eur),2) turnover_eur,
  round(sum(g.stake_eur) - sum(g.payout_eur),2) ggr_eur, round(sum(g.deposit_eur),2) deposits_eur,
  sum(e.self_exclusions) self_exclusions, sum(e.affordability_fails) affordability_fails, sum(g.limit_increase_requests) limit_increase_requests
FROM gold_player_daily g
LEFT JOIN (SELECT player_id, event_date, count_if(event_type='SELF_EXCLUSION') self_exclusions,
                  count_if(event_type='AFFORDABILITY_CHECK_FAILED') affordability_fails
           FROM silver_rg_events GROUP BY ALL) e
  ON e.player_id = g.player_id AND e.event_date = g.activity_date
GROUP BY ALL;
