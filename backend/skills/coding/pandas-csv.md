---
lang: python
keywords: csv, excel, pandas, dataframe, data, clean, columns
---
# Read and clean CSV/data with pandas

```python
import pandas as pd

df = pd.read_csv("data.csv")            # or read_excel("data.xlsx")
print(df.head())                        # first rows
print(df.columns.tolist())              # column names
print(df.dtypes)                        # types

# clean
df = df.dropna(subset=["email"])        # drop rows missing the key column
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

# filter + group
total = df.groupby("region")["amount"].sum()
print(total)

df.to_csv("cleaned.csv", index=False)
```

Gotchas:
- `pd.read_csv` guesses types; check `df.dtypes` and cast numbers/dates.
- Missing values show as `NaN`; handle them before math or you get silent
  `NaN` results.
- `to_csv(..., index=False)` unless you actually want the row index column.
- Big files: use `df.info()` first; if it's gigabytes, consider chunking or
  Polars instead.
- Column names with spaces/special chars: `df["order total"]`, not `df.order
  total`.
