# ML model and GenAI evidence

Captured 2026-11-02 08:07 UTC from workspace `https://<workspace-host>` as `<builder_email>`.

MLflow experiment `/Users/<builder_email>/sportsbook_rg_harm_risk` · run `a4df03720f1544b38696f786fb90ad5b` (hgb_rg_harm_28d) · status FINISHED

## Validation metrics (time-based hold-out snapshot)

| metric | value |
|---|---|
| alert_capacity_k | 353.0 |
| median_lead_time_days | 11.0 |
| model_precision_at_k | 0.1841 |
| model_precision_at_rule_volume | 0.0906 |
| model_recall_at_k | 0.3495 |
| model_recall_at_rule_volume | 0.414 |
| rule_alerts | 850.0 |
| rule_precision | 0.0529 |
| rule_recall | 0.2419 |
| valid_base_rate | 0.0158 |
| valid_pr_auc | 0.1371 |
| valid_roc_auc | 0.7294 |

## Parameters

| param | value |
|---|---|
| class_weight | balanced |
| horizon_days | 28 |
| l2_regularization | 1.0 |
| learning_rate | 0.05 |
| max_iter | 300 |
| max_leaf_nodes | 31 |
| random_state | 7 |
| train_asofs | 2026-08-08,2026-08-15,2026-08-22,2026-08-29 |
| valid_asof | 2026-10-02 |

## Unity Catalog model

`<catalog>.sportsbook_rg.rg_harm_risk_model` version **2**, status READY, source run `a4df03720f1544b38696f786fb90ad5b`

### Live scores by market and tier

```sql
SELECT market, risk_tier, count(*) players, round(avg(risk_score),3) avg_score FROM <catalog>.sportsbook_rg.player_risk_scores GROUP BY ALL ORDER BY 1,2
```

| market | risk_tier | players | avg_score |
|---|---|---|---|
| BR | HIGH | 102 | 0.825 |
| BR | LOW | 3129 | 0.223 |
| BR | MEDIUM | 227 | 0.546 |
| CY | HIGH | 34 | 0.808 |
| CY | LOW | 841 | 0.22 |
| CY | MEDIUM | 76 | 0.547 |
| GR | HIGH | 96 | 0.811 |
| GR | LOW | 3095 | 0.226 |
| GR | MEDIUM | 230 | 0.545 |
| MX | HIGH | 58 | 0.834 |
| MX | LOW | 1576 | 0.231 |
| MX | MEDIUM | 157 | 0.546 |
| RO | HIGH | 58 | 0.839 |
| RO | LOW | 1789 | 0.201 |
| RO | MEDIUM | 121 | 0.547 |

### Top 10 players by risk score with reason codes

```sql
SELECT player_id, market, round(risk_score,3) risk_score, risk_tier, reason_codes FROM <catalog>.sportsbook_rg.player_risk_scores ORDER BY risk_score DESC LIMIT 10
```

| player_id | market | risk_score | risk_tier | reason_codes |
|---|---|---|---|---|
| P110092 | BR | 0.941 | HIGH | ["2 withdrawals reversed to keep playing","27% of bets placed between 00:00-05:00"] |
| P104338 | RO | 0.941 | HIGH | ["2 withdrawals reversed to keep playing","using 41% of deposit limit","29% of bets placed between 00:00-05:00"] |
| P108663 | RO | 0.94 | HIGH | ["5 withdrawals reversed to keep playing","2 deposit-limit increase requests","36% of bets placed between 00:00-05:00"] |
| P100951 | MX | 0.939 | HIGH | ["3 withdrawals reversed to keep playing"] |
| P103210 | CY | 0.939 | HIGH | ["3 withdrawals reversed to keep playing","1 deposit-limit increase requests","50% of bets placed between 00:00-05:00"] |
| P101895 | BR | 0.939 | HIGH | ["4 withdrawals reversed to keep playing","net loss EUR 1,076 in 28 days","26% of bets placed between 00:00-05:00"] |
| P103977 | GR | 0.939 | HIGH | ["3 withdrawals reversed to keep playing","using 122% of deposit limit","51% of bets placed between 00:00-05:00"] |
| P103710 | BR | 0.939 | HIGH | ["using 215% of deposit limit","3 withdrawals reversed to keep playing","47% of bets placed between 00:00-05:00"] |
| P101285 | BR | 0.939 | HIGH | ["2 withdrawals reversed to keep playing","net loss EUR 554 in 28 days","27% of bets placed between 00:00-05:00"] |
| P100898 | RO | 0.939 | HIGH | ["2 deposit-limit increase requests","2 withdrawals reversed to keep playing","55% of bets placed between 00:00-05:00"] |

### GenAI case briefs (ai_query) - completion and action mix

```sql
SELECT recommended_action, urgency, count(*) cases, count_if(llm_error IS NOT NULL) errors FROM <catalog>.sportsbook_rg.rg_case_briefs GROUP BY ALL ORDER BY cases DESC
```

| recommended_action | urgency | cases | errors |
|---|---|---|---|
| OUTBOUND_WELLBEING_CALL | WITHIN_72H | 173 | 0 |
| OUTBOUND_WELLBEING_CALL | WITHIN_24H | 92 | 0 |
| SAFER_GAMBLING_MESSAGE | THIS_WEEK | 36 | 0 |
| AFFORDABILITY_REVIEW | WITHIN_24H | 19 | 0 |
| AFFORDABILITY_REVIEW | WITHIN_72H | 16 | 0 |
| ESCALATE_TO_COMPLIANCE | WITHIN_24H | 10 | 0 |
| SAFER_GAMBLING_MESSAGE | WITHIN_72H | 2 | 0 |

### GenAI case briefs - 5 examples

```sql
SELECT player_id, market, round(risk_score,3) risk_score, recommended_action, urgency, summary, rationale FROM <catalog>.sportsbook_rg.rg_case_briefs ORDER BY risk_score DESC LIMIT 5
```

| player_id | market | risk_score | recommended_action | urgency | summary | rationale |
|---|---|---|---|---|---|---|
| P104338 | RO | 0.941 | OUTBOUND_WELLBEING_CALL | WITHIN_24H | Risk score is very high (0.941) with a 5.1x stake increase over the 28-day window (EUR 4,058 staked across 70 bets) and 52 deposits. Two withdrawals were reversed to keep playing, and 29% of bets fall between 00:00-05:00. Net loss is relatively modes | Sharp stake escalation, reversed withdrawals and frequent deposits point to strong escalation and possible loss chasing, while net loss and limit utilisation are not high enough to trigger an affordability review or compliance escalation. |
| P110092 | BR | 0.941 | OUTBOUND_WELLBEING_CALL | WITHIN_24H | Player (age 21, BR) has a very high risk score of 0.941. Over 28 days, stake rose 5.4x, with 105 bets, EUR 1,152 staked, 57 deposits and a EUR 165 net loss. Two withdrawals were reversed to keep playing and 27% of bets fell between 00:00-05:00. Depos | Reversed withdrawals, a 5.4x stake escalation, frequent deposits and heavy night-time play are strong escalation signals, while the modest net loss and 2% limit utilisation do not meet the thresholds for AFFORDABILITY_REVIEW or ESCALATE_TO_COMPLIANCE |
| P108663 | RO | 0.94 | OUTBOUND_WELLBEING_CALL | WITHIN_24H | 26-year-old RO player with a very high risk score (0.94). Stake has risen 3.4x, with 103 bets and EUR 1,133 staked over 28 days, and net loss is EUR 281. Behavioural markers are strong: 5 reversed withdrawals, 53 deposits, 2 deposit-limit increase re | Escalating stakes, repeated withdrawal reversals, limit-increase requests and frequent night play indicate strong escalation and likely loss chasing, while the low net loss and 4% limit utilisation do not meet the thresholds for AFFORDABILITY_REVIEW  |
| P100143 | GR | 0.939 | AFFORDABILITY_REVIEW | WITHIN_24H | 72-year-old GR player with a very high risk score (0.939) over 28 days: 101 bets, EUR 4,998 staked (stake trend 3.3x) and EUR 644 net loss, with 88 deposits and 92% deposit-limit utilisation. Behavioural markers include 2 reversed withdrawals to cont | High deposit-limit utilisation (92%) combined with a EUR 644 net loss, 3.3x stake escalation, 88 deposits and reversed withdrawals warrants verification of the player's financial capacity, particularly given age 72. |
| P103210 | CY | 0.939 | OUTBOUND_WELLBEING_CALL | WITHIN_72H | Risk score is very high (0.939) with 52 bets and EUR 1,306 staked over 28 days, stake up 4.7x versus baseline, and 45 deposits in the window. Behavioural markers include 3 reversed withdrawals, 1 deposit-limit increase request, and 50% of bets placed | Net loss and limit utilisation are low, so AFFORDABILITY_REVIEW or compliance escalation is not triggered, but the very high risk score, 4.7x stake escalation, repeated withdrawal reversals, a limit increase request and heavy night play indicate stro |
