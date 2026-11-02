# Databricks App evidence (live API calls)

Captured 2026-11-02 08:07 UTC from workspace `https://<workspace-host>` as `<builder_email>`.

App **rg-analyst-console** at https://rg-analyst-console-<workspace_id>.aws.databricksapps.com · compute ACTIVE · active deployment `01f1d6943c4419fe8113fab6406076bf`

Calls made with the developer's OAuth token. Inside the app the same token is forwarded as `x-forwarded-access-token` (on-behalf-of user).

### `GET /api/health` → HTTP 200

```json
{
 "ok": true,
 "lakebase_cases": 1859
}
```

### `GET /api/me` → HTTP 200

```json
{
 "email": "<builder_email>",
 "markets": [
  "BR",
  "CY",
  "GR",
  "MX",
  "RO"
 ],
 "actions": [
  "SAFER_GAMBLING_MESSAGE",
  "OUTBOUND_WELLBEING_CALL",
  "MANDATORY_COOL_OFF_24H",
  "DEPOSIT_LIMIT_REDUCTION",
  "AFFORDABILITY_REVIEW",
  "ESCALATE_TO_COMPLIANCE",
  "NO_ACTION_REQUIRED"
 ],
 "statuses": [
  "OPEN",
  "IN_REVIEW",
  "ACTIONED",
  "CLOSED_NO_ACTION"
 ]
}
```

### `GET /api/summary` → HTTP 200

```json
{
 "by_market": [
  {
   "market": "BR",
   "open_cases": 329,
   "open_high": 102,
   "due_24h": 36,
   "resolved": 195
  },
  {
   "market": "CY",
   "open_cases": 110,
   "open_high": 34,
   "due_24h": 8,
   "resolved": 71
  },
  {
   "market": "GR",
   "open_cases": 325,
   "open_high": 95,
   "due_24h": 32,
   "resolved": 190
  },
  {
   "market": "MX",
   "open_cases": 215,
   "open_high": 58,
   "due_24h": 21,
   "resolved": 90
  },
  {
   "market": "RO",
   "open_cases": 179,
   "open_high": 58,
   "due_24h": 23,
   "resolved": 155
  }
 ],
 "recent_interventions": [
  {
   "player_id": "P100143",
   "action": "OUTBOUND_WELLBEING_CALL",
   "new_status": "ACTIONED",
   "analyst": "<builder_email>",
   "created_at": "2026-11-01T23:32:42.344311+00:00"
  }
 ]
}
```

### `GET /api/cases?status=OPEN&tier=HIGH&limit=5` → HTTP 200

```json
[
 {
  "player_id": "P103710",
  "market": "BR",
  "risk_score": 0.9393468753776514,
  "risk_tier": "HIGH",
  "reason_codes": [
   "using 215% of deposit limit",
   "3 withdrawals reversed to keep playing",
   "47% of bets placed between 00:00-05:00"
  ],
  "recommended_action": "ESCALATE_TO_COMPLIANCE",
  "urgency": "WITHIN_24H",
  "status": "OPEN",
  "assigned_to": null,
  "sla_due_at": "2026-11-02T22:53:07.042402+00:00",
  "updated_at": "2026-11-01T23:33:58.794697+00:00"
 },
 {
  "player_id": "P102593",
  "market": "GR",
  "risk_score": 0.9367870507095032,
  "risk_tier": "HIGH",
  "reason_codes": [
   "2 withdrawals reversed to keep playing",
   "50% of bets placed between 00:00-05:00",
   "net loss EUR 526 in 28 days"
  ],
  "recommended_action": "OUTBOUND_WELLBEING_CALL",
  "urgency": "WITHIN_24H",
  "status": "OPEN",
  "assigned_to": null,
  "sla_due_at": "2026-11-02T22:53:07.042402+00:00",
  "updated_at": "2026-11-01T23:33:58.794697+00:00"
 },
 {
  "player_id": "P103550",
  "market": "GR",
  "risk_score": 0.9155233586254953,
  "risk_tier": "HIGH",
  "reason_codes": [
   "2 withdrawals reversed to keep playing",
   "using 73% of deposit limit",
   "38% of bets placed between 00:00-05:00"
  ],
  "recommended_action": "OUTBOUND_WELLBEING_CALL",
  "urgency": "WITHIN_24H",
  "status": "OPEN",
  "assigned_to": null,
  "sla_due_at": "2026-11-02T22:53:07.042402+00:00",
  "updated_at": "2026-11-01T23:33:58.794697+00:00"
 },
 {
  "player_id": "P104370",
  "market": "BR",
  "risk_score": 0.9155233586254953,
  "risk_tier": "HIGH",
  "reason_codes": [
   "2 withdrawals reversed to keep playing",
   "using 65% of deposit limit",
   "52% of bets placed between 00:00-05:00"
  ],
  "recommended_action": "OUTBOUND_WELLBEING_CALL",
  "urgency": "WITHIN_24H",
  "status": "OPEN",
  "assigned_to": null,
  "sla_due_at": "2026-11-02T22:53:07.042402+00:00",
  "updated_at": "2026-11-01T23:33:58.794697+00:00"
 },
 {
  "player_id": "P100692",
  "market": "BR",
  "risk_score": 0.9120158793476553,
  "risk_tier": "HIGH",
  "reason_codes": [
   "66% of bets placed between 00:00-05:00",
   "using 66% of deposit limit",
   "net loss EUR 1,101 in 28 days"
  ],
  "recommended_action": "AFFORDABILITY_REVIEW",
  "urgency": "WITHIN_24H",
  "status": "OPEN",
  "assigned_to": null,
  "sla_due_at": "2026-11-02T22:53:07.042402+00:00",
  "updated_at": "2026-11-01T23:33:58.794697+00:00"
 }
]
```

### `GET /api/cases/P103710` → HTTP 200

```json
{
 "case": {
  "player_id": "P103710",
  "market": "BR",
  "risk_score": 0.9393468753776514,
  "risk_tier": "HIGH",
  "reason_codes": [
   "using 215% of deposit limit",
   "3 withdrawals reversed to keep playing",
   "47% of bets placed between 00:00-05:00"
  ],
  "summary": "Player (35, BR) has a very high risk score of 0.939. Over 28 days they placed 116 bets with EUR 7,245 staked (3.1x stake trend), a net loss of EUR 972, and 85 deposits. Deposit-limit utilisation is 215% with no limit-increase requests, 3 withdrawals were reversed to keep playing, and 47% of bets fell between 00:00 and 05:00.",
  "recommended_action": "ESCALATE_TO_COMPLIANCE",
  "urgency": "WITHIN_24H",
  "model_version": 2,
  "status": "OPEN",
  "assigned_to": null,
  "opened_at": "2026-11-01T22:53:07.042402+00:00",
  "sla_due_at": "2026-11-02T22:53:07.042402+00:00",
  "scored_at": "2026-11-01T23:04:48.105422+00:00",
  "updated_at": "2026-11-01T23:33:58.794697+00:00"
 },
 "history": [],
 "trend": [
  {
   "activity_date": "2026-09-06",
   "bets": "6",
   "stake_eur": "203.33",
   "net_loss_eur": "-21.0",
   "night_bets": "0",
   "deposits": "0",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-07",
   "bets": "1",
   "stake_eur": "5.42",
   "net_loss_eur": "-12.41",
   "night_bets": "1",
   "deposits": "1",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-08",
   "bets": "1",
   "stake_eur": "17.9",
   "net_loss_eur": "-21.48",
   "night_bets": "0",
   "deposits": "0",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-09",
   "bets": "1",
   "stake_eur": "57.14",
   "net_loss_eur": "57.14",
   "night_bets": "1",
   "deposits": "1",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-10",
   "bets": "1",
   "stake_eur": "13.86",
   "net_loss_eur": "13.86",
   "night_bets": "1",
   "deposits": "6",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-11",
   "bets": "1",
   "stake_eur": "10.98",
   "net_loss_eur": "10.98",
   "night_bets": "0",
   "deposits": "0",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-12",
   "bets": "1",
   "stake_eur": "31.58",
   "net_loss_eur": "31.58",
   "night_bets": "1",
   "deposits": "2",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-13",
   "bets": "4",
   "stake_eur": "140.75",
   "net_loss_eur": "-124.84",
   "night_bets": "2",
   "deposits": "0",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-14",
   "bets": "3",
   "stake_eur": "70.59",
   "net_loss_eur": "70.59",
   "night_bets": "0",
   "deposits": "0",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-15",
   "bets": "3",
   "stake_eur": "140.76",
   "net_loss_eur": "-117.98",
   "night_bets": "1",
   "deposits": "1",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-16",
   "bets": "3",
   "stake_eur": "121.38",
   "net_loss_eur": "70.72",
   "night_bets": "0",
   "deposits": "0",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-17",
   "bets": "3",
   "stake_eur": "74.21",
   "net_loss_eur": "74.21",
   "night_bets": "0",
   "deposits": "2",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-19",
   "bets": "2",
   "stake_eur": "33.75",
   "net_loss_eur": "-9.66",
   "night_bets": "0",
   "deposits": "0",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-20",
   "bets": "2",
   "stake_eur": "16.83",
   "net_loss_eur": "7.47",
   "night_bets": "1",
   "deposits": "1",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-21",
   "bets": "1",
   "stake_eur": "27.16",
   "net_loss_eur": "-96.13",
   "night_bets": "0",
   "deposits": "2",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-22",
   "bets": "1",
   "stake_eur": "25.97",
   "net_loss_eur": "25.97",
   "night_bets": "0",
   "deposits": "3",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-23",
   "bets": "3",
   "stake_eur": "226.27",
   "net_loss_eur": "78.74",
   "night_bets": "2",
   "deposits": "2",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-24",
   "bets": "2",
   "stake_eur": "71.15",
   "net_loss_eur": "71.15",
   "night_bets": "0",
   "deposits": "2",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-25",
   "bets": "3",
   "stake_eur": "118.2",
   "net_loss_eur": "-31.08",
   "night_bets": "1",
   "deposits": "5",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-26",
   "bets": "4",
   "stake_eur": "122.78",
   "net_loss_eur": "-103.76",
   "night_bets": "1",
   "deposits": "1",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-27",
   "bets": "7",
   "stake_eur": "251.31",
   "net_loss_eur": "48.85",
   "night_bets": "1",
   "deposits": "2",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-28",
   "bets": "2",
   "stake_eur": "141.39",
   "net_loss_eur": "-48.04",
   "night_bets": "0",
   "deposits": "2",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-09-29",
   "bets": "2",
   "stake_eur": "52.54",
   "net_loss_eur": "-92.58",
   "night_bets": "0",
   "deposits": "0",
   "reversed_withdrawals": "1"
  },
  {
   "activity_date": "2026-09-30",
   "bets": "1",
   "stake_eur": "101.91",
   "net_loss_eur": "101.91",
   "night_bets": "1",
   "deposits": "4",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-10-01",
   "bets": "2",
   "stake_eur": "146.18",
   "net_loss_eur": "45.05",
   "night_bets": "1",
   "deposits": "1",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-10-02",
   "bets": "2",
   "stake_eur": "79.52",
   "net_loss_eur": "-1.59",
   "night_bets": "0",
   "deposits": "3",
   "reversed_withdrawals": "0"
  },
  {
   "activity_date": "2026-10-03",
   "bets": "3",
   "stake_eur": "64.59",
   "net_loss_eur": "22.75",
   "night_bets": "0",
   "deposits": "3",
   "reversed_withdrawals": "0"
  },
```

### `POST /api/cases/P103710/actions` → HTTP 200

Request body: `{"action": "OUTBOUND_WELLBEING_CALL", "new_status": "ACTIONED", "note": "Evidence run: wellbeing call scheduled, deposit limit discussed."}`

```json
{
 "intervention_id": 2,
 "player_id": "P103710",
 "action": "OUTBOUND_WELLBEING_CALL",
 "note": "Evidence run: wellbeing call scheduled, deposit limit discussed.",
 "analyst": "<builder_email>",
 "new_status": "ACTIONED",
 "created_at": "2026-11-02T08:09:36.036481+00:00"
}
```

### `GET /api/cases?status=ACTIONED&limit=3` → HTTP 200

```json
[
 {
  "player_id": "P103710",
  "market": "BR",
  "risk_score": 0.9393468753776514,
  "risk_tier": "HIGH",
  "reason_codes": [
   "using 215% of deposit limit",
   "3 withdrawals reversed to keep playing",
   "47% of bets placed between 00:00-05:00"
  ],
  "recommended_action": "ESCALATE_TO_COMPLIANCE",
  "urgency": "WITHIN_24H",
  "status": "ACTIONED",
  "assigned_to": "<builder_email>",
  "sla_due_at": "2026-11-02T22:53:07.042402+00:00",
  "updated_at": "2026-11-02T08:09:36.036481+00:00"
 },
 {
  "player_id": "P100143",
  "market": "GR",
  "risk_score": 0.9393468753776514,
  "risk_tier": "HIGH",
  "reason_codes": [
   "using 92% of deposit limit",
   "2 withdrawals reversed to keep playing",
   "41% of bets placed between 00:00-05:00"
  ],
  "recommended_action": "AFFORDABILITY_REVIEW",
  "urgency": "WITHIN_24H",
  "status": "ACTIONED",
  "assigned_to": "<builder_email>",
  "sla_due_at": "2026-11-02T22:53:07.042402+00:00",
  "updated_at": "2026-11-01T23:33:58.794697+00:00"
 }
]
```

### `POST /api/genie/ask` → HTTP 200

Request body: `{"question": "How many HIGH risk players do we have per market today?"}`

```json
{
 "conversation_id": "01f1d694be811ec08608fb7870c87d0e",
 "message_id": "01f1d694be8e16209c2362d108512f58"
}
```

### `GET /api/genie/01f1d694be811ec08608fb7870c87d0e/01f1d694be8e16209c2362d108512f58` → HTTP 200

```json
{
 "status": "COMPLETED",
 "text": "Today, the number of **HIGH** risk players by market is:\n- **BR:** 102\n- **GR:** 96\n- **MX:** 58\n- **RO:** 58\n- **CY:** 34\nAcross these 5 markets, **BR** has the highest count and **CY** the lowest, with **MX** and **RO** tied.",
 "sql": "SELECT `market`, COUNT(*) AS `high_risk_players`\nFROM `<catalog>`.`sportsbook_rg`.`player_risk_scores`\nWHERE `risk_tier` ILIKE '%HIGH%'\n  AND `market` IS NOT NULL\nGROUP BY `market`\nORDER BY `high_risk_players` DESC",
 "columns": [
  "market",
  "high_risk_players"
 ],
 "rows": [
  [
   "BR",
   "102"
  ],
  [
   "GR",
   "96"
  ],
  [
   "MX",
   "58"
  ],
  [
   "RO",
   "58"
  ],
  [
   "CY",
   "34"
  ]
 ],
 "error": null
}
```
