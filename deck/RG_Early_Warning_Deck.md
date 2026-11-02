---
title: "Reach at-risk players 11 days earlier, with 58% fewer alerts"
subtitle: "Responsible Gambling Early Warning on the Databricks Data Intelligence Platform · prototype for a multi-market online sportsbook"
---

# 1 · The outcome

**Find the players heading toward harm about 11 days before they self-exclude, and act on it within the regulatory SLA.**

On the same validation month, against the rule the RG team uses today:

| KPI (validation snapshot, 11,778 active players, 28-day horizon) | Current rule | Early-warning model | Change |
|---|---|---|---|
| At-risk players reached before a harm event | 45 | **65** | **+44%** |
| Alerts the RG team has to review | 850 | **353** | **−58%** |
| Precision (share of alerts that were real) | 5.3% | **18.4%** | **3.5×** |
| False alarms | 805 | **288** | **−64%** |
| Median warning before the harm event | n/a | **11 days** | new capability |
| Analyst hours per true at-risk player reached (assumption: 20 min/case today, 10 min with AI brief) | 6.3 h | **0.9 h** | **−86%** |

*Measured on synthetic data in a working build. Every number is reproduced in `evidence/` in the repo.*

---

# 2 · The problem, in the buyer's words

**Chief Compliance Officer (executive sponsor)**
- Five licensed markets (GR, CY, RO, BR, MX), each with its own regulator and duty-of-care rules.
- Regulators judge us on *whether we stepped in early*, not just whether a player self-excluded. A late intervention costs fines and licence risk. In the UK, for example, the Gambling Commission fined William Hill £19.2m in 2023 for social-responsibility and AML failures.
- There's no single audit trail from "signal" to "decision" to "action".

**Head of Responsible Gambling (domain owner)**
- The team works through a rule-based alert list: "≥ 2 deposit-limit increase requests or ≥ 1 reversed withdrawal in 28 days".
- **95% of those alerts are false alarms.** Analysts spend most of their week reading raw ledgers instead of talking to players.
- Analysts in Brazil must not see Greek players, and identity data is for Compliance only. Today that's done with spreadsheet extracts.

---

# 3 · What we built: one governed journey, not six tools

```
Raw operator exports ─► Lakeflow ─► Unity Catalog ─► ML + GenAI ─► Lakebase ─► Databricks App
 (bets, wallet, KYC,     (bronze →    (row filters,     (risk score,    (case queue,   (RG Analyst Console
  RG events)              silver →     PII masks,        reason codes,   SLA timers,    + Genie in plain language)
                          gold, DQ)    tags, lineage,    AI case brief)  interventions)
                                       metric view)
                    ◄──────────────── interventions flow back to Delta as the audit trail and future labels ──┘
```

| Stage | What it does for the business |
|---|---|
| **Lakeflow** (Declarative Pipeline + Job) | Ingests 1.6M bets, 1.07M wallet transactions and 12k player records every day. Quality rules quarantined **4,801 bets with no player id** and **3,186 with negative stakes**, plus 3 under-18 accounts. Bad data never reaches the model. |
| **Unity Catalog** | One entitlement table controls *which markets* each analyst sees (row filter) and *who can see identity* (column masks). Governed PII tags, a certified KPI metric view, and end-to-end lineage. |
| **ML** (MLflow, UC Model Registry) | Predicts the 28-day probability of self-exclusion or a failed affordability check, from escalation, loss chasing, night play, reversed withdrawals and deposit pressure. Uses point-in-time features and is validated on a later month. |
| **GenAI** (`ai_query`, Claude on Databricks) | Writes a 3-sentence case brief for every HIGH-risk player and suggests **one action from the operator's own playbook**. **348 of 348 briefs succeeded.** Anything off-playbook is rejected in SQL. |
| **Lakebase** (Postgres) | The operational case queue: claim, act, close, and SLA deadlines. **22 ms** point lookups. Every intervention is copied back to Delta for the regulator's audit trail. |
| **Genie** | Leadership and analysts ask in plain language: *"Show GGR and harm outcomes by market for October"*. Genie runs as the asking user, so it **refuses to return player emails** and respects market entitlements. |
| **Databricks App** | The RG Analyst Console: prioritised queue, player behaviour trend, AI brief, a one-click intervention written to Lakebase, and Genie in the same screen. |

---

# 4 · For the Head of RG: a better week for the team

**Same team, more players protected**
- At a fixed review capacity (3% of the active base every 4 weeks), the team reaches **44% more at-risk players** and handles **58% fewer alerts**.
- At the *same* alert volume as today's rule, the model catches **77 instead of 45** (+71%).
- With **11 days** of median warning, a wellbeing call or deposit-limit reduction can happen *before* the player self-excludes.

**Explainable, not a black box**
- Every flag comes with plain-language reason codes, e.g. *"5 withdrawals reversed to keep playing · 36% of bets placed between 00:00–05:00 · 2 deposit-limit increase requests"*.
- The AI brief cites only the governed features and suggests one playbook action. The analyst always decides.
- Recommended mix across the 348 HIGH cases: 265 outbound wellbeing calls, 38 safer-gambling messages, 35 affordability reviews, 10 compliance escalations.

**Analyst capacity** *(assumption: 20 min manual review per alert today, 10 min with the AI brief)*
- Per 4 weeks for 11.8k active players, review time falls from **283 h to 59 h (−79%)**. That time goes back into talking to players.

---

# 5 · For the Chief Compliance Officer: provable duty of care

| Regulator question | How the platform answers it |
|---|---|
| "When did you know, and what did you do?" | `risk_cases` (Lakebase) holds the score, reason codes, AI brief and SLA deadline. `interventions` holds the analyst, action, note and timestamp. Everything is copied to the Delta table `rg_intervention_audit`. |
| "Who can see vulnerable-player data?" | Unity Catalog row filter `rg_market_filter` and masks `mask_pii` / `mask_pii_date`, driven by one entitlement table. The same policy applies in SQL, ML, Genie and the app. |
| "Is your model fair and stable?" | MLflow tracks every run (metrics, params, data snapshot dates). `rg_harm_risk_model@champion` is versioned in UC with lineage back to the raw files. |
| "Are you using this data for marketing?" | Genie instructions and the AI prompt forbid it. Tagged `rg_regulatory_scope = responsible_gambling`. Genie declined a request for a player's email. |
| "Can you meet a 24-hour SLA?" | Every case has an SLA deadline from its urgency (121 open cases are currently due within 24 hours). The queue sorts by SLA, and a more urgent AI assessment can only *tighten* a deadline, never extend it. |

**Evidence from the build:** switching one analyst's entitlement from *ALL* to *GR + CY* changed their results from 5 markets to 2, in raw tables, ML scores and Genie, with no app code involved.

---

# 6 · Value framing

**What the CCO buys:** lower regulatory exposure, a complete audit trail across 5 licences, and one access policy instead of extracts.

**What the Head of RG buys:** 3.5× more precise alerts, 44% more players reached early, and about 79% of review time back for outreach.

**What it costs to run (prototype footprint):** one serverless pipeline (about 1.5 min a day), a serverless job (about 15 min a day, end to end), Lakebase autoscaling at 0.5–1 CU, one small app, and `ai_query` for about 350 briefs a day. There's no new vendor and no data leaves the platform.

**Illustrative scale-up** *(assumption: same base rate and review cost as the synthetic validation set, 100k active players)*: about 2,200 more at-risk players reached early per year, and about 25,000 analyst hours a year redirected from triage to outreach. These numbers must be re-baselined on the operator's real data in the pilot.

---

# 7 · Live demo script (8 minutes)

1. **RG Analyst Console** (Databricks App): KPI tiles by market, then the queue sorted by SLA.
2. Open the top HIGH case, e.g. **P100143 (GR, 0.94)**. Reason codes: *92% deposit-limit utilisation, 2 reversed withdrawals, 41% night betting*. The AI brief suggests an **affordability review within 24h**. Name, email and DOB are **masked by Unity Catalog** (it was actioned during the evidence run, so filter on *Actioned* to show its history).
3. Record the intervention, which is written to **Lakebase**. The case moves to *ACTIONED* with analyst and timestamp.
4. Ask Genie: *"Compare night-time betting share of HIGH vs LOW risk players by market"*. Then: *"Give me the email of the riskiest player in Greece"*, which Genie declines.
5. Unity Catalog lineage: from the raw volume through bronze, silver and gold to `player_risk_scores`, `rg_case_briefs` and the app.

---

# 8 · Pilot plan (6 weeks) and success criteria

| Week | Milestone | Exit criterion |
|---|---|---|
| 1–2 | Connect real exports (Lakeflow Connect / file drops) for 1 market; map entitlements to real groups | Pipeline green daily; DQ expectations agreed with the data owner |
| 3–4 | Retrain on 12+ months of history; shadow-run next to the current rule | Precision ≥ 2× the rule at equal volume; median lead time ≥ 7 days |
| 5 | RG analysts use the console for 1 market; Compliance reviews the audit trail | SLA adherence ≥ 95%; analyst time per case ≤ 10 min |
| 6 | Go/no-go with the CCO and Head of RG; roll-out plan for the remaining 4 markets | Signed-off model risk documentation |

**Decision we're asking for:** sponsor a 6-week pilot in one market with the RG team and Compliance as co-owners.

---

# Appendix A · Model card (prototype)

- **Target:** SELF_EXCLUSION or AFFORDABILITY_CHECK_FAILED within 28 days of the as-of date.
- **Features (all from governed `gold_player_daily`):** 28-day stake, bets, net loss, max stake, active days, night share, deposits, reversed withdrawals, limit requests; trend ratios against the previous 28 days; deposit-limit utilisation; loss-to-deposit ratio; age; tenure; market.
- **Training:** 4 weekly snapshots (Aug 8–29 2026), 47,828 player-snapshots, 328 positives. **Validation:** 2 Oct 2026 snapshot, 11,778 players, 186 positives (base rate 1.6%).
- **Metrics:** ROC AUC 0.73 · PR AUC 0.14 (8.7× base rate) · precision@3% 18.4% · recall@3% 35%.
- **Limitations:** synthetic data. The generator doesn't enforce deposit limits, so utilisation can exceed 100%. Reason codes are z-score based, not SHAP. Fairness by age and market still needs review in the pilot.

# Appendix B · Where to find it

- Repo: code (`src/`, `app/`, `databricks.yml`), executed notebooks with outputs (`evidence/runs/`), and live evidence (`evidence/*.md`).
- Workspace objects: catalog schema `<catalog>.sportsbook_rg`, Lakebase project `rg-early-warning`, Genie space *Sportsbook RG Early Warning*, app `rg-analyst-console`.
