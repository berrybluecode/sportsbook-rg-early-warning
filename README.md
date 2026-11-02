# Sportsbook Responsible Gambling Early Warning

**Industry:** online sports betting (regulated, multi-market).
**Customer problem:** a sportsbook licensed in five markets (GR, CY, RO, BR, MX) has to spot players heading toward gambling harm and step in within regulatory SLAs. Its current rule-based alerts are 95% false alarms, so analysts spend their time triaging instead of contacting players. Regulators ask for proof of *timely* intervention.

**Outcome in this build** (validation month, synthetic data): **+44% at-risk players reached** before a harm event, **58% fewer alerts**, **3.5× precision** compared with the current rule, and a **median 11-day warning**.

> All data is synthetic, produced by `src/01_generate_raw_data.py`. No customer data was used.

## The end-to-end journey

| Stage | Where in the repo | Execution evidence (text) |
|---|---|---|
| **Lakeflow**: Auto Loader bronze → silver (11 expectations, dedup, FX, quarantine) → gold, orchestrated by a Lakeflow Job | `src/pipeline/rg_lakeflow_pipeline.sql`, `databricks.yml` | [evidence/LAKEFLOW_PIPELINE.md](evidence/LAKEFLOW_PIPELINE.md), [evidence/runs/JOB_RUN_SUMMARY.md](evidence/runs/JOB_RUN_SUMMARY.md), [01_generate_raw_data.md](evidence/runs/01_generate_raw_data.md) |
| **Unity Catalog**: entitlement-driven row filter, PII column masks, governed tags, certified metric view, lineage | `src/00_governance_setup.sql`, `src/02_governance_hardening.sql` | [evidence/UNITY_CATALOG_GOVERNANCE.md](evidence/UNITY_CATALOG_GOVERNANCE.md) (includes a before/after row-filter demo), [00](evidence/runs/00_governance_setup.md), [02](evidence/runs/02_governance_hardening.md) |
| **ML**: point-in-time features, time-split validation against the current rule, MLflow, UC model `@champion`, batch scores with reason codes | `src/03_train_score_risk_model.py` | [evidence/ML_GENAI.md](evidence/ML_GENAI.md), [03_train_score_risk_model.md](evidence/runs/03_train_score_risk_model.md) |
| **GenAI**: `ai_query` (Claude on Databricks) writes case briefs, with actions limited to the RG playbook | `src/04_genai_case_briefs.sql` | [evidence/ML_GENAI.md](evidence/ML_GENAI.md), [04_genai_case_briefs.md](evidence/runs/04_genai_case_briefs.md) |
| **Lakebase**: Postgres case queue with SLA; interventions copied back to Delta as the audit trail | `src/05_lakebase_serving.py` | [evidence/LAKEBASE.md](evidence/LAKEBASE.md), [05_lakebase_serving.md](evidence/runs/05_lakebase_serving.md) |
| **Genie**: space over the metric view, scores, briefs and gold tables | `tools/create_genie_space.py` | [evidence/GENIE_QA.md](evidence/GENIE_QA.md): 6 questions with generated SQL and results, including a refused PII request |
| **Databricks App**: RG Analyst Console (FastAPI; Lakebase as the app's service principal, UC and Genie on behalf of the user) | `app/` | [evidence/APP_API.md](evidence/APP_API.md): live API calls against the deployed app, including a write to Lakebase |

Architecture and identity model: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Business deck: [deck/RG_Early_Warning_Deck.md](deck/RG_Early_Warning_Deck.md) (PDF alongside).

## Headline results (copied from the evidence files)

| | Current rule | Model (3% review capacity) | Model (same volume as rule) |
|---|---|---|---|
| Alerts | 850 | 353 | 850 |
| True at-risk players caught | 45 | 65 | 77 |
| Precision | 5.3% | 18.4% | 9.1% |
| Recall | 24.2% | 35.0% | 41.4% |

ROC AUC 0.73 · PR AUC 0.137 (base rate 1.6%) · median lead time 11 days · 348/348 GenAI briefs succeeded · Lakebase p50 point lookup 22 ms (from a laptop) · Lakeflow expectations dropped 4,801 null-player bets, 3,186 non-positive stakes and 3 under-age players.

## Run it yourself

Prerequisites: a Databricks workspace with serverless, Lakebase Autoscaling and Foundation Model endpoints; Databricks CLI ≥ 0.285; `uv`.

Workspace-specific values are kept out of git. Copy `local.settings.example.json` to `local.settings.json` (used by `tools/`), and create a `local.env` that exports `DATABRICKS_CONFIG_PROFILE` and `BUNDLE_VAR_catalog`, `BUNDLE_VAR_warehouse_id`, `BUNDLE_VAR_genie_space_id`, `BUNDLE_VAR_app_sp_role` (used by the bundle). Committed evidence passes through `tools/settings.redact()`, so hosts, ids, the catalog and user names appear as placeholders like `<catalog>` and `<workspace-host>`.

```bash
source local.env
# 1. Lakebase project (once)
databricks postgres create-project rg-early-warning --json '{"spec":{"display_name":"Sportsbook RG Early Warning"}}'
# 2. Schema + landing volume (once)
#    CREATE SCHEMA <catalog>.sportsbook_rg; CREATE VOLUME <catalog>.sportsbook_rg.raw_landing;
# 3. Deploy and run the end-to-end job (generate -> govern -> Lakeflow -> ML -> GenAI -> Lakebase)
databricks bundle deploy && databricks bundle run rg_end_to_end
# 4. Genie space (prints its id), then the app
uv run --with databricks-sdk tools/create_genie_space.py
databricks bundle deploy && databricks bundle run rg_analyst_console
# 5. Capture evidence (redacted)
uv run --with databricks-sdk tools/export_run_evidence.py <job_run_id>
uv run --with databricks-sdk --with "psycopg[binary]" --with requests tools/capture_evidence.py
```

After the first app deploy, the app's service principal needs `USAGE` on schema `rg_ops` and `SELECT, INSERT, UPDATE` on its tables in Lakebase. `05_lakebase_serving.py` grants these when `app_sp_role` is set.

## Build log

- Job run `255598176370280` is the evidence run. Two tasks were *repaired* inside the same run, and the summary lists every attempt:
  - `genai_case_briefs`: the first attempt "succeeded", but all 348 `ai_query` calls returned *"Structured output is not supported for this model"*. I switched to prompt-level JSON with SQL validation; the rerun gave 348/348.
  - `lakebase_serving`: re-run after fixing SLA tightening on upsert, and again after the app wrote an intervention, to show the copy back to Delta. The evidence capture writes one more intervention through the app, so Lakebase can hold one more row than the Delta audit until the next daily run.
- Earlier job runs failed (SQL warehouses don't support `CREATE WIDGET`; workspace tag policies reject the `domain` tag), and those fixes are in the code. The first data version made the single-marker rule unrealistically strong. I added realistic noise and regenerated the data, as noted in the generator notebook.

## Limitations

The data is synthetic, and deposit limits aren't enforced in the generator, so utilisation can exceed 100%. Reason codes are z-score based (not SHAP). The analyst review times in the deck's capacity estimate (20 and 10 minutes) are assumptions, not measurements. Before production, the model needs a fairness review by age and market.
