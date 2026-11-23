import openpyxl

wb = openpyxl.load_workbook(r"C:\Users\user\Downloads\학생명렬표.xlsx")
sheet = wb.active
print("Sheet title:", sheet.title)
print("Max row:", sheet.max_row, "Max col:", sheet.max_column)

# Print header rows
for r in range(1, min(6, sheet.max_row + 1)):
    row_vals = [sheet.cell(r, c).value for c in range(1, sheet.max_column + 1)]
    print(f"Row {r}:", [v for v in row_vals if v is not None])
