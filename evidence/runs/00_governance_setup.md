# 00_governance_setup (executed)

Task `governance_setup` · task run 314647040704769 · job run 255598176370280


# 00 · Unity Catalog governance setup (runs before the pipeline)

An RG analyst licensed for Brazil must not see Greek players. Behavioural data is needed to protect players, but identity (name, email, date of birth) is only for Compliance.
This notebook creates the **entitlement table** and the **row filter** and **column mask** functions. The Lakeflow pipeline attaches them to its tables when it creates them (`WITH ROW FILTER` and `MASK`).

```python
-- Parameters :catalog, :schema (and :llm_endpoint) are supplied by the job (see databricks.yml).
```

```python
USE CATALOG IDENTIFIER(:catalog);
USE SCHEMA IDENTIFIER(:schema);

CREATE TABLE IF NOT EXISTS rg_market_entitlements (
  principal STRING COMMENT 'User email or service principal application id',
  market STRING COMMENT 'Licensed market the principal may see, or ALL',
  pii_access BOOLEAN COMMENT 'TRUE only for Compliance officers who may unmask player identity',
  role STRING COMMENT 'Business role, for audit'
) COMMENT 'Entitlements: which RG analyst may see which licensed market and whether they can see PII. Drives the row filters and column masks.';
```

**Output:**

|  |
|

|  |
|

|  |
|

```python
-- Demo principals: the builder sees all markets but NOT PII (an RG analyst role). Synthetic personas cover the other roles.
MERGE INTO rg_market_entitlements t
USING (SELECT * FROM VALUES
  (current_user(), 'ALL', false, 'RG_ANALYST_GLOBAL'),
  ('rg.analyst.br@example.invalid', 'BR', false, 'RG_ANALYST'),
  ('rg.analyst.gr@example.invalid', 'GR', false, 'RG_ANALYST'),
  ('rg.analyst.gr@example.invalid', 'CY', false, 'RG_ANALYST'),
  ('compliance.officer@example.invalid', 'ALL', true, 'COMPLIANCE_OFFICER')
  AS s(principal, market, pii_access, role)) s
ON t.principal = s.principal AND t.market = s.market
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;

SELECT * FROM rg_market_entitlements ORDER BY role, market;
```

**Output:**

| num_affected_rows | num_updated_rows | num_deleted_rows | num_inserted_rows |
|---|---|---|---|
| 5 | 5 | 0 | 0 |

| principal | market | pii_access | role |
|---|---|---|---|
| compliance.officer@example.invalid | ALL | True | COMPLIANCE_OFFICER |
| rg.analyst.br@example.invalid | BR | False | RG_ANALYST |
| rg.analyst.gr@example.invalid | CY | False | RG_ANALYST |
| rg.analyst.gr@example.invalid | GR | False | RG_ANALYST |
| <builder_email> | ALL | False | RG_ANALYST_GLOBAL |

```python
CREATE OR REPLACE FUNCTION rg_market_filter(row_market STRING)
RETURNS BOOLEAN
COMMENT 'Row filter: a reader only sees rows for licensed markets they are entitled to in rg_market_entitlements.'
RETURN EXISTS (
  SELECT 1 FROM rg_market_entitlements e
  WHERE e.principal = current_user() AND (e.market = 'ALL' OR e.market = row_market)
);

CREATE OR REPLACE FUNCTION mask_pii(v STRING)
RETURNS STRING
COMMENT 'Column mask: reveals player identity only to principals with pii_access = TRUE.'
RETURN CASE WHEN EXISTS (SELECT 1 FROM rg_market_entitlements e WHERE e.principal = current_user() AND e.pii_access)
            THEN v ELSE '***MASKED***' END;

CREATE OR REPLACE FUNCTION mask_pii_date(v DATE)
RETURNS DATE
COMMENT 'Column mask for dates of birth: year only unless pii_access = TRUE.'
RETURN CASE WHEN EXISTS (SELECT 1 FROM rg_market_entitlements e WHERE e.principal = current_user() AND e.pii_access)
            THEN v ELSE trunc(v, 'YEAR') END;
```

**Output:**

|  |
|

|  |
|

|  |
|

```python
SHOW USER FUNCTIONS IN IDENTIFIER(:schema);
```

**Output:**

| function |
|---|
| <catalog>.sportsbook_rg.mask_pii |
| <catalog>.sportsbook_rg.mask_pii_date |
| <catalog>.sportsbook_rg.rg_market_filter |
