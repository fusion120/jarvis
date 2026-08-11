---
lang: python
keywords: excel, openpyxl, xlsx, spreadsheet, workbook, worksheet, cell, formula, styling
---

# Reading and writing .xlsx with openpyxl

Excel files show up in every report pipeline. `openpyxl` reads/writes `.xlsx` with styling,
formulas, and multiple sheets, and `data_only=True` lets you read cached formula results
instead of the formula strings.

```python
# pip install openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill


def write_report(path: str, rows: list[tuple]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"
    ws.append(["Item", "Qty", "Price"])          # row 1 = header
    for row in rows:
        ws.append(row)

    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="DDDDDD")

    ws.append(["TOTAL", f"=SUM(B2:B{1 + len(rows)})", ""])   # live formula
    wb.save(path)


def read_report(path: str) -> list[tuple]:
    wb = load_workbook(path, data_only=True)     # cached values, not formulas
    ws = wb.active
    return [
        tuple(row)
        for row in ws.iter_rows(min_row=2, values_only=True)
        if any(v is not None for v in row)
    ]


write_report("report.xlsx", [("widget", 3, 4.50), ("gadget", 7, 9.99)])
print(read_report("report.xlsx"))
```

Gotchas:
- `load_workbook` default returns *formula strings* (`"=SUM(B2:B3)"`), not values — pass
  `data_only=True` to read cached values. A file saved by a non-Excel writer may have no cache,
  returning `None`.
- Rows/cells are 1-indexed (`ws["A1"]`, `ws.cell(row=2, column=1)`); 0-indexing crashes or
  silently shifts data.
- Formulas are stored but not recalculated by openpyxl — Excel recalculates on open; the cached
  value only exists if something saved it with calculated results.
- The first worksheet is `wb.active`; creating `Workbook()` already contains one sheet, so
  `create_sheet` adds a *second* one — don't double-create.
- `ws.append` writes to the next empty row; merging style/`Font` across a row range needs
  explicit loops or `range` — copying cell styles one at a time is normal.
- Only `.xlsx` is supported, not legacy `.xls` (that needs `xlrd`/`xlwt` or LibreOffice).
