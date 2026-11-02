# Architecture: one governed data journey

```mermaid
flowchart LR
  subgraph Raw["Raw operator exports (synthetic)"]
    P[players CSV<br/>KYC + PII]
    B[bets JSON<br/>1 file/day]
    T[wallet tx JSON]
    R[RG events JSON]
  end
  subgraph UC["Unity Catalog · <catalog>.sportsbook_rg"]
    V[(Volume raw_landing)]
    subgraph LF["Lakeflow Declarative Pipeline"]
      BR[bronze_*<br/>Auto Loader streaming tables]
      SI[silver_*<br/>expectations · dedup · FX<br/>row filter + PII masks]
      GO[gold_player_daily<br/>gold_market_daily_kpis]
    end
    MV[rg_kpi_metrics<br/>certified metric view]
    ML[rg_harm_risk_model@champion<br/>MLflow · UC registry]
    SC[player_risk_scores<br/>row-filtered]
    AI[rg_case_briefs<br/>ai_query · Claude]
    AU[rg_intervention_audit]
  end
  LB[(Lakebase Postgres<br/>rg_ops.risk_cases<br/>rg_ops.interventions)]
  G[Genie space<br/>Sportsbook RG Early Warning]
  APP[Databricks App<br/>RG Analyst Console]

  P & B & T & R --> V --> BR --> SI --> GO --> MV
  GO --> ML --> SC --> AI
  SC & AI -->|daily upsert| LB
  LB -->|interventions back to Delta| AU
  MV & SC & AI & GO --> G
  LB <-->|queue + actions<br/>app service principal| APP
  GO & SI -->|player trend + profile<br/>on-behalf-of user| APP
  G -->|Conversation API<br/>on-behalf-of user| APP
```

## How each stage hands off to the next

| Stage | Asset | Hands off to |
|---|---|---|
| Lakeflow | `src/pipeline/rg_lakeflow_pipeline.sql`: 5 Auto Loader bronze streaming tables, 5 silver MVs with 11 expectations, a quarantine MV, 2 gold MVs | `gold_player_daily` is the only input to the features |
| Unity Catalog | `src/00_governance_setup.sql`, `src/02_governance_hardening.sql`: an entitlement table, row filter `rg_market_filter`, masks `mask_pii` / `mask_pii_date`, governed tags, a certified metric view, lineage | The same policies apply in the pipeline, the ML table, the GenAI table, Genie and the app |
| ML | `src/03_train_score_risk_model.py`: point-in-time features, time-split validation, comparison with the current rule, UC model `@champion`, reason codes | `player_risk_scores` |
| GenAI | `src/04_genai_case_briefs.sql`: `ai_query` with a JSON-schema response format, limited to a fixed playbook of actions | `rg_case_briefs` |
| Lakebase | `src/05_lakebase_serving.py`: upserts the HIGH/MEDIUM cases with an SLA, and copies interventions back to Delta | `rg_ops.risk_cases`, `rg_intervention_audit` |
| Genie | `tools/create_genie_space.py`: metric view, 5 tables, instructions, example SQL | The app's "Ask Genie" panel, or Genie directly |
| App | `app/`: FastAPI + vanilla JS | Analysts read and write Lakebase, see UC data through their own identity, and ask Genie |

## Two identities, on purpose

* **Lakebase (OLTP)** is accessed by the app's **service principal**. The app limits the queue to the markets that **Unity Catalog** says the user may see. It gets that list by running `SELECT DISTINCT market FROM player_risk_scores` as the user, which goes through the row filter. Entitlements live in one place.
* **Unity Catalog reads and Genie** run **on behalf of the signed-in user** (`x-forwarded-access-token`, scopes `sql` and `dashboards.genie`). The row filters and PII masks therefore apply without any app code.

## Orchestration

One Lakeflow Job (`sportsbook-rg-early-warning-daily`, in `databricks.yml`) runs these steps in order: generate raw data, governance setup, Lakeflow pipeline, governance hardening, train and score, GenAI briefs, Lakebase serving. In production, the generator task would be replaced by the operator's real file drops or a Lakeflow Connect source, and the job would run daily.
