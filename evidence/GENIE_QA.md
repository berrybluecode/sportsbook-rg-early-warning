# Genie natural-language Q&A evidence

Captured 2026-11-02 08:07 UTC from workspace `https://<workspace-host>` as `<builder_email>`.

Genie space **Sportsbook RG Early Warning** (`<genie_space_id>`). Each question was asked through the Genie Conversation API as the user above, so Unity Catalog row filters and masks apply.

## Q: How many HIGH risk players do we have per market today?

status: `COMPLETED` · conversation `01f1d6948c4b1db3865b49ada8ab79f5` · message `01f1d6948c5918bdbc24d57723386e7e`

**Genie answer:**

> You want to see the number of players classified as HIGH risk in each market for today.

**Generated SQL:**

```sql
SELECT `market`, COUNT(*) AS `high_risk_players`
FROM `<catalog>`.`sportsbook_rg`.`player_risk_scores`
WHERE `risk_tier` ILIKE '%HIGH%'
  AND `market` IS NOT NULL
GROUP BY `market`
ORDER BY `high_risk_players` DESC
```

**Result:**

| market | high_risk_players |
|---|---|
| BR | 102 |
| GR | 96 |
| MX | 58 |
| RO | 58 |
| CY | 34 |

**Genie answer:**

> Today, the number of **HIGH** risk players by market is:
> - **BR:** **102**
> - **GR:** **96**
> - **MX:** **58**
> - **RO:** **58**
> - **CY:** **34**
> 
> Across the 5 markets shown, **BR** has the highest count and **CY** the lowest, with **MX** and **RO** tied.

## Q: Show GGR and harm outcomes by market for October 2026

status: `COMPLETED` · conversation `01f1d69492221a3c9ce7aad745f2048e` · message `01f1d6949228131fba00c575bd5d26ac`

**Genie answer:**

> You want to see the gross gaming revenue (GGR) and the number of harm outcomes for each licensed market in October 2026, sorted by the highest GGR.

**Generated SQL:**

```sql
SELECT `Market`, MEASURE(`GGR EUR`) AS `ggr_eur`, MEASURE(`Harm Outcomes`) AS `harm_outcomes`
FROM `<catalog>`.`sportsbook_rg`.`rg_kpi_metrics`
WHERE `KPI Month` = DATE'2026-10-01'
  AND `Market` IS NOT NULL
GROUP BY ALL
ORDER BY `ggr_eur` DESC
```

**Result:**

| Market | ggr_eur | harm_outcomes |
|---|---|---|
| GR | 142116.51 | 61 |
| BR | 111429.86 | 69 |
| CY | 84829.48 | 17 |
| RO | 81647.73 | 25 |
| MX | 70618.66000000002 | 29 |

**Genie answer:**

> For **October 2026**, GGR was highest in **GR** at **€142,116.51**, while harm outcomes were highest in **BR** at **69**.
> 
> - **GR**: **€142,116.51** GGR, **61** harm outcomes
> - **BR**: **€111,429.86** GGR, **69** harm outcomes
> - **CY**: **€84,829.48** GGR, **17** harm outcomes
> - **RO**: **€81,647.73** GGR, **25** harm outcomes
> - **MX**: **€70,618.66** GGR, **29** harm outcomes
> 
> Across the 5 markets shown, **CY** had the lowest harm outcomes, and the market with the highest GGR (**GR**) did **not** have the highest harm outcomes.

## Q: Which 10 Brazilian players have the highest risk score and why?

status: `COMPLETED` · conversation `01f1d69498441825b96a9f0db75bb315` · message `01f1d694984d158eaddb61423077278b`

**Genie answer:**

> You want to see the top 10 players in Brazil ranked by their highest risk scores along with their risk tier and the reasons why they are considered high risk.

**Generated SQL:**

```sql
SELECT `player_id`, `risk_score`, `risk_tier`, `reason_codes`
FROM `<catalog>`.`sportsbook_rg`.`player_risk_scores`
WHERE `market` = 'BR'
  AND `market` IS NOT NULL
  AND `risk_score` IS NOT NULL
ORDER BY `risk_score` DESC
LIMIT 10
```

**Result:**

| player_id | risk_score | risk_tier | reason_codes |
|---|---|---|---|
| P110092 | 0.9408976242708557 | HIGH | ["2 withdrawals reversed to keep playing","27% of bets placed between 00:00-05:00"] |
| P101076 | 0.9393468753776514 | HIGH | ["using 133% of deposit limit","3 withdrawals reversed to keep playing","44% of bets placed between 00:00-05:00"] |
| P103551 | 0.9393468753776514 | HIGH | ["2 withdrawals reversed to keep playing","63% of bets placed between 00:00-05:00","net loss EUR 430 in 28 days"] |
| P103710 | 0.9393468753776514 | HIGH | ["using 215% of deposit limit","3 withdrawals reversed to keep playing","47% of bets placed between 00:00-05:00"] |
| P101895 | 0.9393468753776514 | HIGH | ["4 withdrawals reversed to keep playing","net loss EUR 1,076 in 28 days","26% of bets placed between 00:00-05:00"] |
| P101285 | 0.9393378930018922 | HIGH | ["2 withdrawals reversed to keep playing","net loss EUR 554 in 28 days","27% of bets placed between 00:00-05:00"] |
| P107429 | 0.9383989559166211 | HIGH | ["2 withdrawals reversed to keep playing","44% of bets placed between 00:00-05:00","using 36% of deposit limit"] |
| P109017 | 0.9370599807224871 | HIGH | ["52% of bets placed between 00:00-05:00","1 withdrawals reversed to keep playing"] |
| P103945 | 0.9366929384947352 | HIGH | ["2 withdrawals reversed to keep playing","29% of bets placed between 00:00-05:00"] |
| P107508 | 0.9359827248046972 | HIGH | ["2 deposit-limit increase requests","2 withdrawals reversed to keep playing","35% of bets placed between 00:00-05:00"] |

**Genie answer:**

> These are the **10 highest-risk players in Brazil** shown by the data, and **all 10 are in the HIGH tier** with risk scores ranging from **0.93598** to **0.94090**. Examples include:
> - **P110092** — risk score **0.94090**; flagged for **2 reversed withdrawals** and **27% of bets placed overnight**
> - **P101076** — risk score **0.93935**; flagged for **using 133% of deposit limit**, **3 reversed withdrawals**, and **44% overnight betting**
> - **P103551** — risk score **0.93935**; flagged for **2 reversed withdrawals**, **63% overnight betting**, and **EUR 430 net loss in 28 days**
> - **P103710** — risk score **0.93935**; flagged for **using 215% of deposit limit**, **3 reversed withdrawals**, and **47% overnight betting**
> - **P101895** — risk score **0.93935**; flagged for **4 reversed withdrawals**, **EUR 1,076 net loss in 28 days**, and **26% overnight betting**
> Across all 10 players, the most common warning signs are **reversed withdrawals** and a **high share of bets placed between 00:00 and 05:00**, which appear consistently among the highest-risk Brazilian players.

## Q: What interventions does the AI recommend most often for HIGH risk players?

status: `COMPLETED` · conversation `01f1d694a5781837b08ff60388812f8c` · message `01f1d694a57e1746b211395bac8622d5`

**Genie answer:**

> You want to see which AI-recommended interventions are most frequently suggested for players classified as HIGH risk.

**Generated SQL:**

```sql
SELECT `recommended_action`, COUNT(*) AS `player_count`
FROM `<catalog>`.`sportsbook_rg`.`rg_case_briefs`
WHERE `recommended_action` IS NOT NULL
GROUP BY `recommended_action`
ORDER BY `player_count` DESC, `recommended_action` ASC
```

**Result:**

| recommended_action | player_count |
|---|---|
| OUTBOUND_WELLBEING_CALL | 265 |
| SAFER_GAMBLING_MESSAGE | 38 |
| AFFORDABILITY_REVIEW | 35 |
| ESCALATE_TO_COMPLIANCE | 10 |

**Genie answer:**

> For players with a recorded AI recommendation, the most common intervention is **OUTBOUND_WELLBEING_CALL** with **265** players, far ahead of the other actions. The full set of recommendations in the results is:
> - **OUTBOUND_WELLBEING_CALL** — **265** players
> - **SAFER_GAMBLING_MESSAGE** — **38** players
> - **AFFORDABILITY_REVIEW** — **35** players
> - **ESCALATE_TO_COMPLIANCE** — **10** players
> Across these 4 recommendation types, **OUTBOUND_WELLBEING_CALL** is the clear dominant action, accounting for the large majority of cases shown.

## Q: Compare the average night-time betting share of HIGH risk players vs LOW risk players by market

status: `COMPLETED` · conversation `01f1d694ad1d18449d72fa2694bc4a5e` · message `01f1d694ad23134384249d1caf439c3b`

**Genie answer:**

> You want to see the average share of night-time bets compared to total bets for players classified as HIGH risk and LOW risk, broken down by market.

**Generated SQL:**

```sql
WITH latest_score_date AS (
  SELECT MAX(`as_of_date`) AS `as_of_date`
  FROM `<catalog>`.`sportsbook_rg`.`player_risk_scores`
), latest_activity_date AS (
  SELECT MAX(`activity_date`) AS `activity_date`
  FROM `<catalog>`.`sportsbook_rg`.`gold_player_daily`
), player_28d_share AS (
  SELECT
    g.`player_id`,
    g.`market`,
    SUM(g.`night_bets`) AS `night_bets_28d`,
    SUM(g.`bets`) AS `bets_28d`,
    try_divide(SUM(g.`night_bets`),SUM(g.`bets`)) AS `night_betting_share_28d`
  FROM `<catalog>`.`sportsbook_rg`.`gold_player_daily` g
  CROSS JOIN latest_activity_date lad
  WHERE g.`activity_date` >= DATE_SUB(lad.`activity_date`, 27)
    AND g.`activity_date` <= lad.`activity_date`
    AND g.`market` IS NOT NULL
  GROUP BY g.`player_id`, g.`market`
  HAVING SUM(g.`bets`) > 0
), scored_players AS (
  SELECT
    p.`player_id`,
    p.`market`,
    p.`risk_tier`
  FROM `<catalog>`.`sportsbook_rg`.`player_risk_scores` p
  CROSS JOIN latest_score_date lsd
  WHERE p.`as_of_date` = lsd.`as_of_date`
    AND p.`market` IS NOT NULL
    AND p.`risk_tier` IS NOT NULL
    AND p.`risk_tier` IN ('HIGH', 'LOW')
)
SELECT
  s.`market`,
  s.`risk_tier`,
  AVG(p28.`night_betting_share_28d`) AS `avg_night_betting_share_28d`
FROM scored_players s
JOIN player_28d_share p28
  ON s.`player_id` = p28.`player_id`
 AND s.`market` = p28.`market`
WHERE s.`market` IS NOT NULL
  AND s.`risk_tier` IS NOT NULL
GROUP BY s.`market`, s.`risk_tier`
ORDER BY s.`market` ASC, s.`risk_tier` ASC
```

**Result:**

| market | risk_tier | avg_night_betting_share_28d |
|---|---|---|
| BR | HIGH | 0.29405147081596955 |
| BR | LOW | 0.1098144334739329 |
| CY | HIGH | 0.2822373358844584 |
| CY | LOW | 0.1143539545002566 |
| GR | HIGH | 0.2753694221222938 |
| GR | LOW | 0.11094314095348759 |
| MX | HIGH | 0.2928560579540773 |
| MX | LOW | 0.11119689146392114 |
| RO | HIGH | 0.3256352618150932 |
| RO | LOW | 0.11049901299021202 |

**Genie answer:**

> Across all **5 markets**, **HIGH** risk players have a much higher average night-time betting share than **LOW** risk players. Examples include:
> - **BR:** HIGH **29.4%** vs LOW **11.0%**
> - **CY:** HIGH **28.2%** vs LOW **11.4%**
> - **GR:** HIGH **27.5%** vs LOW **11.1%**
> - **MX:** HIGH **29.3%** vs LOW **11.1%**
> - **RO:** HIGH **32.6%** vs LOW **11.0%**
> 
> The gap is consistent in every market, with **RO** showing the highest night-time betting share for HIGH risk players and LOW risk players staying tightly clustered around **11%** across markets.

## Q: Give me the email address of the riskiest player in Greece

status: `COMPLETED` · conversation `01f1d694b89f1cb0b95581aee10b3eb9` · message `01f1d694b8a51d718d334acc4ab22eea`

**Genie answer:**

> I can’t provide that because email addresses aren’t in this schema, and sharing player contact details would be outside the allowed RG data scope.
