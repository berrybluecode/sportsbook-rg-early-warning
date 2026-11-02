# 03_train_score_risk_model (executed)

Task `train_score_model` · task run 610361420554486 · job run 255598176370280


# 03 · Train and score the RG harm early-warning model

**Question:** which active players will self-exclude or fail an affordability check in the **next 28 days**?

* Features: 28-day behaviour vs the previous 28 days, from the governed `gold_player_daily` (escalation, loss chasing, night play, reversed withdrawals, deposit-limit requests).
* Point-in-time snapshots: features use data **up to** the as-of date only. Labels use the 28 days **after** it. This avoids leakage.
* Time-based split: train on earlier snapshots, validate on a later, unseen snapshot.
* Compared with the **current manual rule** (flag if ≥ 2 deposit-limit increase requests OR ≥ 1 reversed withdrawal in 28 days).
* Tracked in MLflow, registered in Unity Catalog as `rg_harm_risk_model@champion`, batch-scored into `player_risk_scores` with plain-language reason codes.

```python
%pip install -q "mlflow>=3.1" "scikit-learn>=1.4"
%restart_python
```

**Output:**

```
Note: you may need to restart the kernel using %restart_python or dbutils.library.restartPython() to use updated packages.
```

```python
dbutils.widgets.text("catalog", "<catalog>")
dbutils.widgets.text("schema", "sportsbook_rg")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
FQ = f"{CATALOG}.{SCHEMA}"
MODEL_NAME = f"{FQ}.rg_harm_risk_model"
spark.sql(f"USE {FQ}")
```

**Output:**

```
{'text/plain': 'DataFrame[]'}
```

```python
import numpy as np, pandas as pd, mlflow
from pyspark.sql import functions as F

end_date = spark.table("gold_player_daily").agg(F.max("activity_date")).first()[0]
print("Latest activity date:", end_date)
H = 28  # feature window and label horizon, days

FEATURE_SQL = """
WITH w AS (
  SELECT g.*, p.age, p.tenure_days, p.daily_deposit_limit_eur,
         CASE WHEN activity_date >  date_sub(DATE'{asof}', {h}) THEN 'cur' ELSE 'prev' END AS win
  FROM gold_player_daily g JOIN silver_players p USING (player_id, market)
  WHERE activity_date <= DATE'{asof}' AND activity_date > date_sub(DATE'{asof}', {h2})
),
excluded AS (SELECT DISTINCT player_id FROM silver_rg_events WHERE is_harm_outcome AND event_date <= DATE'{asof}'),
f AS (
  SELECT player_id, market, max(age) age, max(tenure_days) tenure_days, max(daily_deposit_limit_eur) deposit_limit_eur,
    sum(CASE WHEN win='cur' THEN bets END) bets_28d,
    sum(CASE WHEN win='cur' THEN stake_eur END) stake_28d,
    sum(CASE WHEN win='cur' THEN net_loss_eur END) net_loss_28d,
    max(CASE WHEN win='cur' THEN max_stake_eur END) max_stake_28d,
    count(CASE WHEN win='cur' AND bets > 0 THEN 1 END) active_days_28d,
    sum(CASE WHEN win='cur' THEN night_bets END) / nullif(sum(CASE WHEN win='cur' THEN bets END), 0) night_share_28d,
    sum(CASE WHEN win='cur' THEN deposits END) deposits_28d,
    sum(CASE WHEN win='cur' THEN deposit_eur END) deposit_eur_28d,
    sum(CASE WHEN win='cur' THEN reversed_withdrawals END) reversed_withdrawals_28d,
    sum(CASE WHEN win='cur' THEN limit_increase_requests END) limit_requests_28d,
    sum(CASE WHEN win='prev' THEN stake_eur END) stake_prev_28d,
    sum(CASE WHEN win='prev' THEN bets END) bets_prev_28d,
    sum(CASE WHEN win='prev' THEN deposits END) deposits_prev_28d
  FROM w GROUP BY player_id, market
)
SELECT DATE'{asof}' AS as_of_date, f.*,
  (coalesce(stake_28d,0) + 1) / (coalesce(stake_prev_28d,0) + 1) AS stake_trend,
  (coalesce(bets_28d,0) + 1) / (coalesce(bets_prev_28d,0) + 1) AS bets_trend,
  (coalesce(deposits_28d,0) + 1) / (coalesce(deposits_prev_28d,0) + 1) AS deposit_trend,
  coalesce(deposit_eur_28d,0) / nullif(deposit_limit_eur * 28, 0) AS deposit_limit_utilisation,
  coalesce(net_loss_28d,0) / nullif(deposit_eur_28d, 0) AS loss_to_deposit_ratio,
  CASE WHEN EXISTS (SELECT 1 FROM silver_rg_events e WHERE e.player_id = f.player_id AND e.is_harm_outcome
                    AND e.event_date > DATE'{asof}' AND e.event_date <= date_add(DATE'{asof}', {h})) THEN 1 ELSE 0 END AS label
FROM f LEFT ANTI JOIN excluded x USING (player_id)
WHERE coalesce(bets_28d,0) > 0
"""

def snapshot(asof):
    return spark.sql(FEATURE_SQL.format(asof=asof, h=H, h2=2 * H)).toPandas()

FEATURES = ["age", "tenure_days", "bets_28d", "stake_28d", "net_loss_28d", "max_stake_28d", "active_days_28d",
            "night_share_28d", "deposits_28d", "deposit_eur_28d", "reversed_withdrawals_28d", "limit_requests_28d",
            "stake_trend", "bets_trend", "deposit_trend", "deposit_limit_utilisation", "loss_to_deposit_ratio"]

d = pd.Timestamp(end_date)
train_asofs = [(d - pd.Timedelta(days=x)).date() for x in (84, 77, 70, 63)]
valid_asof = (d - pd.Timedelta(days=H + 1)).date()     # last snapshot whose 28-day label window is fully observed
live_asof = d.date()

train = pd.concat([snapshot(a) for a in train_asofs], ignore_index=True)
valid = snapshot(valid_asof)
print(f"train snapshots={train_asofs} rows={len(train):,} positives={int(train.label.sum())} "
      f"| valid as_of={valid_asof} rows={len(valid):,} positives={int(valid.label.sum())}")
```

**Output:**

```
Latest activity date: 2026-10-31
train snapshots=[datetime.date(2026, 8, 8), datetime.date(2026, 8, 15), datetime.date(2026, 8, 22), datetime.date(2026, 8, 29)] rows=47,828 positives=328 | valid as_of=2026-10-02 rows=11,778 positives=186
```

```python
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
from mlflow.models import infer_signature

mlflow.set_registry_uri("databricks-uc")
user = spark.sql("SELECT current_user()").first()[0]
mlflow.set_experiment(f"/Users/{user}/sportsbook_rg_harm_risk")

def prep(df):
    X = df[FEATURES].astype("float64").fillna(0.0)
    X["market_BR"], X["market_MX"], X["market_RO"] = [(df.market == m).astype("float64") for m in ("BR", "MX", "RO")]
    return X

Xtr, ytr, Xva, yva = prep(train), train.label.values, prep(valid), valid.label.values

def at_k(y, s, k):
    top = np.argsort(-s)[:k]
    return y[top].sum() / k, y[top].sum() / max(y.sum(), 1)

with mlflow.start_run(run_name="hgb_rg_harm_28d") as run:
    params = dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, l2_regularization=1.0,
                  class_weight="balanced", random_state=7)
    model = HistGradientBoostingClassifier(**params).fit(Xtr, ytr)
    s = model.predict_proba(Xva)[:, 1]

    # Capacity-based alerting: RG team can review ~3% of the active base per 4-week cycle
    k = int(round(0.03 * len(valid)))
    prec_k, rec_k = at_k(yva, s, k)
    rule = ((valid.limit_requests_28d.fillna(0) >= 2) | (valid.reversed_withdrawals_28d.fillna(0) >= 1)).values
    rule_prec = yva[rule].sum() / max(rule.sum(), 1)
    rule_rec = yva[rule].sum() / max(yva.sum(), 1)

    metrics = {"valid_roc_auc": roc_auc_score(yva, s), "valid_pr_auc": average_precision_score(yva, s),
               "valid_base_rate": yva.mean(), "alert_capacity_k": k,
               "model_precision_at_k": prec_k, "model_recall_at_k": rec_k,
               "rule_alerts": int(rule.sum()), "rule_precision": rule_prec, "rule_recall": rule_rec}
    mlflow.log_params({**params, "horizon_days": H, "train_asofs": ",".join(map(str, train_asofs)), "valid_asof": str(valid_asof)})
    mlflow.log_metrics(metrics)
    mlflow.sklearn.log_model(model, name="model", signature=infer_signature(Xtr, model.predict_proba(Xtr)[:, 1]),
                             input_example=Xtr.head(3), registered_model_name=MODEL_NAME)
    run_id = run.info.run_id

pd.DataFrame([metrics]).T.rename(columns={0: "value"})
```

**Output:**

```
If you are using MLflow Tracing, you can migrate your traces to Unity Catalog for unlimited storage, fine-grained access controls, and queryability from notebooks, SQL, and dashboards. Learn more: https://docs.databricks.com/aws/en/mlflow3/genai/tracing/migrate-traces-to-uc
🔗 View Logged Model at: https://<workspace-host>/ml/experiments/3198537323088987/models/m-7669dcb957154b28b79a2fb3c4f78ecf?o=<workspace_id>
Registered model '<catalog>.sportsbook_rg.rg_harm_risk_model' already exists. Creating a new version of this model...


{'text/plain': 'Uploading artifacts:   0%|          | 0/11 [00:00<?, ?it/s]', 'application/vnd.jupyter.widget-view+json': {'version_major': 2, 'version_minor': 0, 'model_id': '9f48cb30855941b483f7d49d54f188c3'}}

🔗 Created version '2' of model '<catalog>.sportsbook_rg.rg_harm_risk_model': https://<workspace-host>/explore/data/models/<catalog>/sportsbook_rg/rg_harm_risk_model/version/2?o=<workspace_id>


{'text/plain': '                           value\nvalid_roc_auc           0.729396\nvalid_pr_auc            0.137137\nvalid_base_rate         0.015792\nalert_capacity_k      353.000000\nmodel_precision_at_k    0.184136\nmodel_recall_at_k       0.349462\nrule_alerts           850.000000\nrule_precision          0.052941\nrule_recall             0.241935', 'text/html': '<div>\n<style scoped>\n    .dataframe tbody tr th:only-of-type {\n        vertical-align: middle;\n    }\n\n    .dataframe tbody tr th {\n        vertical-align: top;\n    }\n\n    .dataframe thead th {\n        text-align: right;\n    }\n</style>\n<table border="1" class="dataframe">\n  <thead>\n    <tr style="text-align: right;">\n      <th></th>\n      <th>value</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <th>valid_roc_auc</th>\n      <td>0.729396</td>\n    </tr>\n    <tr>\n      <th>valid_pr_auc</th>\n      <td>0.137137</td>\n    </tr>\n    <tr>\n      <th>valid_base_rate</th>\n      <td>0.015792</td>\n    </tr>\n    <tr>\n      <th>alert_capacity_k</th>\n      <td>353.000000</td>\n    </tr>\n    <tr>\n      <th>model_precision_at_k</th>\n      <td>0.184136</td>\n    </tr>\n    <tr>\n      <th>model_recall_at_k</th>\n      <td>0.349462</td>\n    </tr>\n    <tr>\n      <th>rule_alerts</th>\n      <td>850.000000</td>\n    </tr>\n    <tr>\n      <th>rule_precision</th>\n      <td>0.052941</td>\n    </tr>\n    <tr>\n      <th>rule_recall</th>\n      <td>0.241935</td>\n    </tr>\n  </tbody>\n</table>\n</div>'}
```

 ### Model vs current rule: same reviewer workload, more harm caught

```python
thr = float(np.sort(s)[-k])
k_rule = int(rule.sum())
prec_kr, rec_kr = at_k(yva, s, k_rule)
mlflow.log_metrics({"model_precision_at_rule_volume": prec_kr, "model_recall_at_rule_volume": rec_kr}, run_id=run_id)
cmp = pd.DataFrame([
    {"approach": "Current manual rule", "alerts": int(rule.sum()), "true_harm_caught": int(yva[rule].sum()),
     "precision": round(rule_prec, 3), "recall": round(rule_rec, 3)},
    {"approach": f"ML model, top {k} (3% capacity)", "alerts": k, "true_harm_caught": int(yva[s >= thr].sum()),
     "precision": round(prec_k, 3), "recall": round(rec_k, 3)},
    {"approach": f"ML model, top {k_rule} (same volume as rule)", "alerts": k_rule, "true_harm_caught": int(round(prec_kr * k_rule)),
     "precision": round(prec_kr, 3), "recall": round(rec_kr, 3)},
])
display(cmp)

# Lead time: how many days before the harm event did the model flag the player?
ev = spark.sql(f"""SELECT player_id, min(event_date) first_harm FROM silver_rg_events
                   WHERE is_harm_outcome AND event_date > DATE'{valid_asof}' GROUP BY player_id""").toPandas()
flagged = valid.loc[s >= thr, ["player_id"]].merge(ev, on="player_id")
lead = (pd.to_datetime(flagged.first_harm) - pd.Timestamp(valid_asof)).dt.days
print(f"Median lead time before harm event for correctly flagged players: {lead.median():.0f} days (n={len(lead)})")
mlflow.log_metric("median_lead_time_days", float(lead.median()), run_id=run_id)
```

**Output:**

| approach | alerts | true_harm_caught | precision | recall |
|---|---|---|---|---|
| Current manual rule | 850 | 45 | 0.053 | 0.242 |
| ML model, top 353 (3% capacity) | 353 | 65 | 0.184 | 0.349 |
| ML model, top 850 (same volume as rule) | 850 | 77 | 0.091 | 0.414 |

Median lead time before harm event for correctly flagged players: 11 days (n=65)


```python
from mlflow import MlflowClient
client = MlflowClient()
latest = max(client.search_model_versions(f"name='{MODEL_NAME}'"), key=lambda v: int(v.version))
client.set_registered_model_alias(MODEL_NAME, "champion", latest.version)
client.update_registered_model(MODEL_NAME, description="Predicts probability of an RG harm outcome (self-exclusion or failed affordability check) in the next 28 days. Trained on synthetic data.")
print(f"Registered {MODEL_NAME} version {latest.version} as @champion (run {run_id})")
```

**Output:**

```
Registered <catalog>.sportsbook_rg.rg_harm_risk_model version 2 as @champion (run a4df03720f1544b38696f786fb90ad5b)
```

 ### Batch score the live base (as of the latest day) with reason codes

```python
import time
t0 = time.time()
champion = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")
live = snapshot(live_asof)
live["risk_score"] = champion.predict_proba(prep(live))[:, 1]
cut_high = np.quantile(live.risk_score, 0.97)
cut_med = np.quantile(live.risk_score, 0.90)
live["risk_tier"] = np.where(live.risk_score >= cut_high, "HIGH", np.where(live.risk_score >= cut_med, "MEDIUM", "LOW"))
print(f"scored {len(live):,} players in {time.time() - t0:.0f}s")

REASONS = {  # feature -> plain-language marker used by analysts and the GenAI case brief
    "stake_trend": "stakes up {v:.1f}x vs previous 4 weeks",
    "bets_trend": "betting frequency up {v:.1f}x",
    "deposit_trend": "deposit frequency up {v:.1f}x",
    "night_share_28d": "{v:.0%} of bets placed between 00:00-05:00",
    "reversed_withdrawals_28d": "{v:.0f} withdrawals reversed to keep playing",
    "limit_requests_28d": "{v:.0f} deposit-limit increase requests",
    "deposit_limit_utilisation": "using {v:.0%} of deposit limit",
    "net_loss_28d": "net loss EUR {v:,.0f} in 28 days",
}
ref = train[train.label == 0][list(REASONS)].astype(float)
vals = live[list(REASONS)].astype(float).fillna(0.0)
z = ((vals - ref.mean()) / ref.std().replace(0, 1)).to_numpy()
order = np.argsort(-z, axis=1)[:, :3]
names = np.array(list(REASONS))
live["reason_codes"] = [
    [REASONS[names[j]].format(v=vals.iat[i, j]) for j in order[i] if z[i, j] > 1.0] for i in range(len(live))]
live["model_version"] = int(latest.version)
out_cols = ["player_id", "market", "as_of_date", "risk_score", "risk_tier", "reason_codes", "model_version"] + FEATURES
t0 = time.time()
live["as_of_date"] = pd.to_datetime(live["as_of_date"]).dt.date
spark.sql("DROP TABLE IF EXISTS player_risk_scores")  # recreated daily; the row filter is re-attached below
(spark.createDataFrame(live[out_cols])
   .withColumn("scored_at", F.current_timestamp())
   .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("player_risk_scores"))
print(f"wrote player_risk_scores in {time.time() - t0:.0f}s")
spark.sql("ALTER TABLE player_risk_scores SET ROW FILTER rg_market_filter ON (market)")
spark.sql("COMMENT ON TABLE player_risk_scores IS 'Daily RG harm risk score per active player (next-28-day probability), tier and reason codes. Model: rg_harm_risk_model@champion.'")
spark.sql("ALTER TABLE player_risk_scores SET TAGS ('classification'='confidential','rg_regulatory_scope'='responsible_gambling','rg_ml_model'='rg_harm_risk_model')")

display(spark.sql("""SELECT market, risk_tier, count(*) players, round(avg(risk_score),3) avg_score
                     FROM player_risk_scores GROUP BY ALL ORDER BY market, risk_tier"""))
```

**Output:**

```
{'text/plain': 'Downloading artifacts:   0%|          | 0/11 [00:00<?, ?it/s]', 'application/vnd.jupyter.widget-view+json': {'version_major': 2, 'version_minor': 0, 'model_id': 'e4a96564a04240fb9036dbe67caa9738'}}

scored 11,589 players in 6s
wrote player_risk_scores in 10s


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
```

```python
display(spark.sql("SELECT player_id, market, round(risk_score,3) risk_score, risk_tier, reason_codes FROM player_risk_scores ORDER BY risk_score DESC LIMIT 10"))
```

**Output:**

| player_id | market | risk_score | risk_tier | reason_codes |
|---|---|---|---|---|
| P110092 | BR | 0.941 | HIGH | ['2 withdrawals reversed to keep playing', '27% of bets placed between 00:00-05:00'] |
| P104338 | RO | 0.941 | HIGH | ['2 withdrawals reversed to keep playing', 'using 41% of deposit limit', '29% of bets placed between 00:00-05:00'] |
| P108663 | RO | 0.94 | HIGH | ['5 withdrawals reversed to keep playing', '2 deposit-limit increase requests', '36% of bets placed between 00:00-05:00'] |
| P103977 | GR | 0.939 | HIGH | ['3 withdrawals reversed to keep playing', 'using 122% of deposit limit', '51% of bets placed between 00:00-05:00'] |
| P101285 | BR | 0.939 | HIGH | ['2 withdrawals reversed to keep playing', 'net loss EUR 554 in 28 days', '27% of bets placed between 00:00-05:00'] |
| P108345 | MX | 0.939 | HIGH | ['4 withdrawals reversed to keep playing', '2 deposit-limit increase requests', 'using 61% of deposit limit'] |
| P103710 | BR | 0.939 | HIGH | ['using 215% of deposit limit', '3 withdrawals reversed to keep playing', '47% of bets placed between 00:00-05:00'] |
| P101895 | BR | 0.939 | HIGH | ['4 withdrawals reversed to keep playing', 'net loss EUR 1,076 in 28 days', '26% of bets placed between 00:00-05:00'] |
| P100951 | MX | 0.939 | HIGH | ['3 withdrawals reversed to keep playing'] |
| P100898 | RO | 0.939 | HIGH | ['2 deposit-limit increase requests', '2 withdrawals reversed to keep playing', '55% of bets placed between 00:00-05:00'] |
