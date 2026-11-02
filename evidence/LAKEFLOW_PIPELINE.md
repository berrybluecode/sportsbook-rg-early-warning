# Lakeflow ingestion and data quality evidence

Captured 2026-11-02 08:07 UTC from workspace `https://<workspace-host>` as `<builder_email>`.

Pipeline id `a5c45d50-5690-48cc-b8fb-e9175456c920` · latest update `67155c7d-ce9f-4fb5-b923-77c6d6ea0236` · state **COMPLETED**

### Lakeflow flows: rows written in the latest update (pipeline event log)

```sql
SELECT origin.flow_name AS flow, max(details:flow_progress.metrics.num_output_rows::BIGINT) AS output_rows,
       max(details:flow_progress.data_quality.dropped_records::BIGINT) AS dropped_by_expectations
FROM event_log('a5c45d50-5690-48cc-b8fb-e9175456c920')
WHERE event_type = 'flow_progress' AND origin.update_id = '67155c7d-ce9f-4fb5-b923-77c6d6ea0236' AND details:flow_progress.status = 'COMPLETED'
GROUP BY 1 ORDER BY 1
```

| flow | output_rows | dropped_by_expectations |
|---|---|---|
| <catalog>.sportsbook_rg.bronze_bets | None | None |
| <catalog>.sportsbook_rg.bronze_fx_rates | None | None |
| <catalog>.sportsbook_rg.bronze_players | None | None |
| <catalog>.sportsbook_rg.bronze_rg_events | None | None |
| <catalog>.sportsbook_rg.bronze_transactions | None | None |
| <catalog>.sportsbook_rg.gold_market_daily_kpis | 600 | 0 |
| <catalog>.sportsbook_rg.gold_player_daily | 809679 | 0 |
| <catalog>.sportsbook_rg.silver_bets | 1596039 | 7987 |
| <catalog>.sportsbook_rg.silver_bets_quarantine | 8013 | 0 |
| <catalog>.sportsbook_rg.silver_players | 11997 | 3 |
| <catalog>.sportsbook_rg.silver_rg_events | 2722 | 0 |
| <catalog>.sportsbook_rg.silver_transactions | 1074195 | 0 |

### Lakeflow expectations: passed / failed records per rule (pipeline event log)

```sql
SELECT origin.flow_name AS flow, e.name AS expectation, sum(e.passed_records) AS passed_records, sum(e.failed_records) AS failed_records
FROM event_log('a5c45d50-5690-48cc-b8fb-e9175456c920'),
     LATERAL explode(from_json(details:flow_progress.data_quality.expectations,
       'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) AS t(e)
WHERE event_type = 'flow_progress' AND origin.update_id = '67155c7d-ce9f-4fb5-b923-77c6d6ea0236'
GROUP BY 1, 2 ORDER BY 1, 2
```

| flow | expectation | passed_records | failed_records |
|---|---|---|---|
| <catalog>.sportsbook_rg.silver_bets | positive_stake | 1600840 | 3186 |
| <catalog>.sportsbook_rg.silver_bets | settled_status | 1604026 | 0 |
| <catalog>.sportsbook_rg.silver_bets | valid_odds | 1604026 | 0 |
| <catalog>.sportsbook_rg.silver_bets | valid_player | 1599225 | 4801 |
| <catalog>.sportsbook_rg.silver_players | adult | 11997 | 3 |
| <catalog>.sportsbook_rg.silver_players | valid_market | 12000 | 0 |
| <catalog>.sportsbook_rg.silver_rg_events | valid_player | 2722 | 0 |
| <catalog>.sportsbook_rg.silver_transactions | known_type | 1074195 | 0 |
| <catalog>.sportsbook_rg.silver_transactions | positive_amount | 1074195 | 0 |
| <catalog>.sportsbook_rg.silver_transactions | valid_player | 1074195 | 0 |

### Row counts bronze -> silver

```sql
SELECT 'bets' feed, (SELECT count(*) FROM <catalog>.sportsbook_rg.bronze_bets) bronze_rows, (SELECT count(*) FROM <catalog>.sportsbook_rg.silver_bets) silver_rows,
       (SELECT count(*) FROM <catalog>.sportsbook_rg.silver_bets_quarantine) quarantined, (SELECT count(*) - count(DISTINCT bet_id) FROM <catalog>.sportsbook_rg.bronze_bets) duplicate_bet_ids
UNION ALL SELECT 'transactions', (SELECT count(*) FROM <catalog>.sportsbook_rg.bronze_transactions), (SELECT count(*) FROM <catalog>.sportsbook_rg.silver_transactions), NULL,
       (SELECT count(*) - count(DISTINCT transaction_id) FROM <catalog>.sportsbook_rg.bronze_transactions)
UNION ALL SELECT 'players', (SELECT count(*) FROM <catalog>.sportsbook_rg.bronze_players), (SELECT count(*) FROM <catalog>.sportsbook_rg.silver_players), NULL, NULL
```

| feed | bronze_rows | silver_rows | quarantined | duplicate_bet_ids |
|---|---|---|---|---|
| bets | 1608843 | 1596039 | 8013 | 4817 |
| transactions | 1074195 | 1074195 | None | 0 |
| players | 12000 | 11997 | None | None |

### Quarantine reasons

```sql
SELECT dq_reason, count(*) n FROM <catalog>.sportsbook_rg.silver_bets_quarantine GROUP BY 1 ORDER BY 2 DESC
```

| dq_reason | n |
|---|---|
| NULL_PLAYER_ID | 4817 |
| NON_POSITIVE_STAKE | 3196 |

### Gold KPIs - October 2026 by market (certified metric view)

```sql
SELECT `Market`, MEASURE(`Turnover EUR`) turnover_eur, MEASURE(`GGR EUR`) ggr_eur, MEASURE(`Harm Outcomes`) harm_outcomes
FROM <catalog>.sportsbook_rg.rg_kpi_metrics WHERE `KPI Month` = DATE'2026-10-01' GROUP BY `Market` ORDER BY ggr_eur DESC
```

| Market | turnover_eur | ggr_eur | harm_outcomes |
|---|---|---|---|
| GR | 2700405.7800000003 | 142116.51 | 61 |
| BR | 1880323.2600000002 | 111429.86 | 69 |
| CY | 904542.79 | 84829.48 | 17 |
| RO | 1083098.3600000003 | 81647.73 | 25 |
| MX | 1137883.27 | 70618.66000000002 | 29 |
