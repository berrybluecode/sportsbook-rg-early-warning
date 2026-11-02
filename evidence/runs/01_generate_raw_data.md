# 01_generate_raw_data (executed)

Task `generate_raw_data` · task run 31592373943300 · job run 255598176370280


# 01 · Generate synthetic raw sportsbook data

Simulates the raw exports that a multi-market online sportsbook operator lands every day:

| Feed | Format | Path in volume |
|---|---|---|
| Player registry (KYC export) | CSV | `players/` |
| Bet ledger | JSON lines, one folder per day | `bets/` |
| Wallet transactions | JSON lines, one folder per day | `transactions/` |
| Responsible Gambling (RG) control events | JSON lines | `rg_events/` |
| FX reference rates | CSV | `reference/` |

**All data is synthetic.** Names come from a small fixed list, emails use the reserved `example.invalid` domain.

A hidden share of players (~6%) follows a *harm trajectory*: after an onset day, their bet frequency,
stake size, night-time play, deposit frequency, and reversed withdrawals all escalate. About 70% of them
later self-exclude or fail an affordability check. These outcomes are the label that the model learns to predict
**before** they happen. Separately, "high-roller" players stake a lot but stay stable, so the model can't just learn "big stakes = risk".

Single markers are noisy on purpose: ~3% of all players' withdrawals get reversed, and stable players also ask for limit increases. A rule built on one marker therefore raises many false alarms.

Deliberate data quality defects (for the Lakeflow expectations to catch): null `player_id`, negative stakes, duplicate `bet_id`s.

```python
dbutils.widgets.text("catalog", "<catalog>")
dbutils.widgets.text("schema", "sportsbook_rg")
dbutils.widgets.text("n_players", "12000")
dbutils.widgets.text("days", "120")
dbutils.widgets.text("end_date", "2026-10-31")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
N_PLAYERS = int(dbutils.widgets.get("n_players"))
DAYS = int(dbutils.widgets.get("days"))
END_DATE = dbutils.widgets.get("end_date")
ROOT = f"/Volumes/{CATALOG}/{SCHEMA}/raw_landing"
print(f"Landing root: {ROOT}  players={N_PLAYERS} days={DAYS} end={END_DATE}")
```

**Output:**

```
Landing root: /Volumes/<catalog>/sportsbook_rg/raw_landing  players=12000 days=120 end=2026-10-31
```

```python
import json, os, shutil
import numpy as np
import pandas as pd

rng = np.random.default_rng(20261031)

# Start from a clean landing zone so reruns are reproducible
for sub in ["players", "bets", "transactions", "rg_events", "reference"]:
    p = f"{ROOT}/{sub}"
    if os.path.exists(p):
        shutil.rmtree(p)
    os.makedirs(p, exist_ok=True)

end = pd.Timestamp(END_DATE)
dates = pd.date_range(end=end, periods=DAYS, freq="D")

MARKETS = {  # market -> (currency, share of players, avg stake in local currency)
    "GR": ("EUR", 0.30, 9.0),
    "CY": ("EUR", 0.08, 11.0),
    "RO": ("RON", 0.17, 35.0),
    "BR": ("BRL", 0.30, 40.0),
    "MX": ("MXN", 0.15, 160.0),
}
FX_TO_EUR = {"EUR": 1.0, "RON": 0.201, "BRL": 0.168, "MXN": 0.049}
```

 ## Players

```python
FIRST = ["Alex", "Maria", "Nikos", "Elena", "Joao", "Ana", "Luis", "Sofia", "Andrei", "Ioana", "Carlos", "Lucia",
         "Petros", "Daria", "Mateus", "Camila", "Diego", "Valeria", "Stefan", "Irina"]
LAST = ["Silva", "Papadopoulos", "Garcia", "Popescu", "Santos", "Lopez", "Georgiou", "Ionescu", "Oliveira",
        "Martinez", "Nikolaou", "Dumitru", "Costa", "Hernandez", "Christou", "Pereira"]

mk = list(MARKETS)
player_market = rng.choice(mk, size=N_PLAYERS, p=[MARKETS[m][1] for m in mk])
player_ids = np.array([f"P{100000 + i}" for i in range(N_PLAYERS)])
age = rng.integers(18, 75, N_PLAYERS)
young = age < 26

# Hidden behavioural archetypes
is_harm = rng.random(N_PLAYERS) < np.where(young, 0.10, 0.05)  # harm trajectory, more likely if young
is_high_roller = (~is_harm) & (rng.random(N_PLAYERS) < 0.04)    # big but stable stakes
harm_onset = np.where(is_harm, rng.integers(25, DAYS - 10, N_PLAYERS), 10_000)

base_rate = rng.lognormal(mean=-0.3, sigma=0.8, size=N_PLAYERS)  # bets per day
base_rate = np.clip(base_rate, 0.05, 6)
avg_stake_local = np.array([MARKETS[m][2] for m in player_market]) * rng.lognormal(0, 0.6, N_PLAYERS)
avg_stake_local = np.where(is_high_roller, avg_stake_local * 12, avg_stake_local)
base_night_share = rng.beta(1.5, 12, N_PLAYERS)

reg_date = end - pd.to_timedelta(rng.integers(DAYS + 30, DAYS + 1500, N_PLAYERS), unit="D")
players = pd.DataFrame({
    "player_id": player_ids,
    "first_name": rng.choice(FIRST, N_PLAYERS),
    "last_name": rng.choice(LAST, N_PLAYERS),
    "email": [f"player{100000 + i}@example.invalid" for i in range(N_PLAYERS)],
    "date_of_birth": (end - pd.to_timedelta(age * 365 + rng.integers(0, 365, N_PLAYERS), unit="D")).strftime("%Y-%m-%d"),
    "market": player_market,
    "currency": [MARKETS[m][0] for m in player_market],
    "registration_date": reg_date.strftime("%Y-%m-%d"),
    "kyc_status": rng.choice(["VERIFIED", "VERIFIED", "VERIFIED", "PENDING"], N_PLAYERS),
    "marketing_opt_in": rng.random(N_PLAYERS) < 0.6,
    "daily_deposit_limit_local": np.round(np.array([MARKETS[m][2] for m in player_market]) * rng.choice([20, 50, 100, 250], N_PLAYERS), 0),
})
players.to_csv(f"{ROOT}/players/players_export.csv", index=False)
pd.DataFrame([{"currency": c, "rate_to_eur": r, "valid_from": str(dates[0].date())} for c, r in FX_TO_EUR.items()]) \
  .to_csv(f"{ROOT}/reference/fx_rates.csv", index=False)
print(players.market.value_counts().to_dict(), "harm:", int(is_harm.sum()), "high_rollers:", int(is_high_roller.sum()))
```

**Output:**

```
{'BR': 3590, 'GR': 3552, 'RO': 2025, 'MX': 1852, 'CY': 981} harm: 676 high_rollers: 440
```

 ## Daily bets, wallet transactions and RG events

```python
SPORTS = ["Football", "Basketball", "Tennis", "Esports", "Volleyball", "Ice Hockey"]
SPORT_P = [0.55, 0.15, 0.12, 0.08, 0.05, 0.05]
BET_TYPES = ["SINGLE", "ACCUMULATOR", "LIVE"]
prev_net_loss = np.zeros(N_PLAYERS)
excluded = np.zeros(N_PLAYERS, dtype=bool)
exclusion_day = np.where(is_harm & (rng.random(N_PLAYERS) < 0.70),
                         harm_onset + rng.gamma(4, 8, N_PLAYERS).astype(int) + 5, 10_000)
# A few non-harm players self-exclude for unrelated reasons (label noise)
exclusion_day = np.where((~is_harm) & (rng.random(N_PLAYERS) < 0.004), rng.integers(0, DAYS, N_PLAYERS), exclusion_day)

bet_seq, tx_seq, rg_rows, totals = 0, 0, [], {"bets": 0, "tx": 0}
for d_idx, day in enumerate(dates):
    t = d_idx
    since = np.clip(t - harm_onset, 0, None)
    esc = 1 + np.where(is_harm, since / 20.0, 0)                       # escalation multiplier
    chase = np.where(is_harm & (since > 0), 1 + np.clip(prev_net_loss / (avg_stake_local * 5 + 1), 0, 2), 1)
    weekend = 1.35 if day.dayofweek >= 5 else 1.0
    rate = base_rate * esc * weekend
    active = ~excluded
    n_bets = np.where(active, rng.poisson(rate), 0)

    idx = np.repeat(np.arange(N_PLAYERS), n_bets)
    nb = len(idx)
    stake = np.round(avg_stake_local[idx] * rng.lognormal(0, 0.7, nb) * np.sqrt(esc[idx]) * chase[idx], 2)
    odds = np.round(1.2 + rng.gamma(1.6, 1.1, nb), 2)
    win = rng.random(nb) < (0.93 / odds)
    payout = np.where(win, np.round(stake * odds, 2), 0.0)
    night_share = np.clip(base_night_share[idx] + np.where(is_harm[idx], since[idx] / 120.0, 0), 0, 0.6)
    is_night = rng.random(nb) < night_share
    hour = np.where(is_night, rng.integers(0, 5, nb), rng.choice(np.arange(9, 24), nb))
    ts = day + pd.to_timedelta(hour, unit="h") + pd.to_timedelta(rng.integers(0, 3600, nb), unit="s")

    bets = pd.DataFrame({
        "bet_id": [f"B{bet_seq + i:09d}" for i in range(nb)],
        "player_id": player_ids[idx],
        "placed_at": ts.strftime("%Y-%m-%dT%H:%M:%S"),
        "sport": rng.choice(SPORTS, nb, p=SPORT_P),
        "bet_type": rng.choice(BET_TYPES, nb, p=[0.5, 0.3, 0.2]),
        "stake": stake,
        "currency": players.currency.values[idx],
        "odds": odds,
        "status": np.where(win, "WON", "LOST"),
        "payout": payout,
        "channel": rng.choice(["APP", "WEB"], nb, p=[0.78, 0.22]),
    })
    bet_seq += nb
    # Inject raw-data defects (~0.3% each)
    if nb:
        bad = rng.random(nb)
        bets.loc[bad < 0.003, "player_id"] = None
        bets.loc[(bad >= 0.003) & (bad < 0.005), "stake"] *= -1
        bets = pd.concat([bets, bets.sample(frac=0.003, random_state=d_idx)])   # duplicate bet_ids (replayed export)

    # Wallet: deposits scale with stakes, losses and escalation; withdrawals for winners
    staked = np.bincount(idx, weights=stake, minlength=N_PLAYERS)
    paid = np.bincount(idx, weights=payout, minlength=N_PLAYERS)
    net_loss = staked - paid
    n_dep = np.where(active & (staked > 0), rng.poisson(0.5 + 0.6 * np.where(is_harm, since / 15.0, 0) + (net_loss > 0)), 0)
    n_wd = np.where(active & (net_loss < -avg_stake_local), rng.poisson(0.8), 0)
    tx = []
    for kind, counts in [("DEPOSIT", n_dep), ("WITHDRAWAL", n_wd)]:
        j = np.repeat(np.arange(N_PLAYERS), counts)
        if not len(j):
            continue
        per = np.where(kind == "DEPOSIT",
                       np.maximum(staked[j], avg_stake_local[j] * 2) / np.maximum(counts[j], 1),
                       np.abs(net_loss[j]) / np.maximum(counts[j], 1))
        amt = np.round(per * rng.lognormal(0, 0.3, len(j)), 2)
        status = np.full(len(j), "COMPLETED", dtype=object)
        if kind == "WITHDRAWAL":  # harm players cancel withdrawals to keep playing
            p_rev = np.where(is_harm[j] & (since[j] > 0), 0.22, 0.03)
            status = np.where(rng.random(len(j)) < p_rev, "REVERSED", "COMPLETED")
        tx.append(pd.DataFrame({
            "transaction_id": [f"T{tx_seq + i:09d}" for i in range(len(j))],
            "player_id": player_ids[j],
            "created_at": (day + pd.to_timedelta(rng.integers(0, 86400, len(j)), unit="s")).strftime("%Y-%m-%dT%H:%M:%S"),
            "type": kind,
            "amount": amt,
            "currency": players.currency.values[j],
            "payment_method": rng.choice(["CARD", "E_WALLET", "BANK_TRANSFER", "PIX", "OXXO"], len(j)),
            "status": status,
        }))
        tx_seq += len(j)
    tx = pd.concat(tx) if tx else pd.DataFrame()

    # RG control events: deposit-limit increase requests, cool-offs, self-exclusions, affordability fails
    lim_req = active & is_harm & (since > 0) & (rng.random(N_PLAYERS) < 0.012)
    lim_req |= active & (~is_harm) & (rng.random(N_PLAYERS) < 0.0015)
    for p in np.where(lim_req)[0]:
        rg_rows.append((player_ids[p], str(day.date()), "DEPOSIT_LIMIT_INCREASE_REQUEST", "PLAYER"))
    for p in np.where(active & (exclusion_day == t))[0]:
        kind = "SELF_EXCLUSION" if rng.random() < 0.75 else "AFFORDABILITY_CHECK_FAILED"
        rg_rows.append((player_ids[p], str(day.date()), kind, "PLAYER" if kind == "SELF_EXCLUSION" else "COMPLIANCE"))
        excluded[p] = True

    prev_net_loss = np.maximum(net_loss, 0)
    dstr = str(day.date())
    os.makedirs(f"{ROOT}/bets/{dstr}", exist_ok=True)
    bets.to_json(f"{ROOT}/bets/{dstr}/bets_{dstr}.json", orient="records", lines=True)
    if len(tx):
        os.makedirs(f"{ROOT}/transactions/{dstr}", exist_ok=True)
        tx.to_json(f"{ROOT}/transactions/{dstr}/transactions_{dstr}.json", orient="records", lines=True)
    totals["bets"] += len(bets)
    totals["tx"] += len(tx)

rg = pd.DataFrame(rg_rows, columns=["player_id", "event_date", "event_type", "source"])
rg.insert(0, "event_id", [f"E{i:07d}" for i in range(len(rg))])
rg.to_json(f"{ROOT}/rg_events/rg_events_export.json", orient="records", lines=True)
print(f"bets rows={totals['bets']:,} transactions={totals['tx']:,} rg_events={len(rg):,}")
print(rg.event_type.value_counts().to_dict())
```

**Output:**

```
bets rows=1,608,843 transactions=1,074,195 rg_events=2,722
{'DEPOSIT_LIMIT_INCREASE_REQUEST': 2326, 'SELF_EXCLUSION': 309, 'AFFORDABILITY_CHECK_FAILED': 87}
```

 ## Landing zone inventory

```python
inv = []
for sub in ["players", "bets", "transactions", "rg_events", "reference"]:
    files = [os.path.join(r, f) for r, _, fs in os.walk(f"{ROOT}/{sub}") for f in fs]
    inv.append({"feed": sub, "files": len(files), "mb": round(sum(os.path.getsize(f) for f in files) / 1e6, 1)})
display(pd.DataFrame(inv))
```

**Output:**

| feed | files | mb |
|---|---|---|
| players | 1 | 1.2 |
| bets | 120 | 335.5 |
| transactions | 120 | 199.6 |
| rg_events | 1 | 0.4 |
| reference | 1 | 0.0 |
