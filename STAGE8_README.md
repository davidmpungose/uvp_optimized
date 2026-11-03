# Stage 8: Permanent SQL Result Storage

This package is deliberately standalone so it does not disturb the working `main.py`.

## 1. Copy files
Copy `app/database/*`, `app/services/*`, and `results_main.py` into the project root, preserving folders.

## 2. Add `.env` values
Copy values from `.env.stage8.example` into the project `.env`.

## 3. Create the SQL tables
```powershell
py results_main.py create-results-schema
```

## 4. Load and validate one quarter
```powershell
py results_main.py load-quarter-results --quarter 2024-Q1
py results_main.py validate-results --quarter 2024-Q1
```

## 5. Load all available quarters
```powershell
py results_main.py load-all-results
```

Only potential cases are stored in `analytics.CaseResults`. All quarter clustering rows are stored in `analytics.ClusterResults`. Existing rows for the chosen quarter are deleted and replaced inside a transaction.
