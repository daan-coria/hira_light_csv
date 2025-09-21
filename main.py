from pathlib import Path
import pandas as pd
from datetime import datetime

# --- Loaders (only the 4 canonical ones) ---
from ingestion.excel_v010 import (
    load_census_from_excel,
    load_staffing_rules_from_excel,
    load_shifts_from_excel,
    load_resources_from_excel,
)

# --- Logic pieces ---
from logic.staffing_plan import build_staffing_plan
from logic.position_control import build_position_control, compare_plan_vs_resources
from logic.scheduler import assign_staff_to_shifts

# --- Excel formatting ---
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

# File name
FILENAME = "HIRA Light (IP) v0.12 (1).xlsx"

# Styling constants
HEADER_FILL = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
HEADER_FONT = Font(bold=True, color="000000")
THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin")
)
CENTER_ALIGN = Alignment(horizontal="center", vertical="center")


def _resolve_excel_path() -> Path:
    here = Path(__file__).resolve().parent
    root = here.parent
    candidates = [
        root / "data" / FILENAME,
        here / "data" / FILENAME,
        root / FILENAME,
    ]
    for p in candidates:
        if p.exists():
            return p
    tried = "\n - ".join(str(p) for p in candidates)
    raise FileNotFoundError(f"Could not find '{FILENAME}'. Tried:\n - {tried}")


def _format_sheet(ws, sheet_name=None):
    # Header row
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER
        cell.alignment = CENTER_ALIGN

    # Borders + alignment for data rows
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.border = THIN_BORDER
            if isinstance(cell.value, (int, float)):
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            if "date" in str(ws.cell(row=1, column=cell.col_idx).value).lower():
                cell.number_format = "yyyy-mm-dd"

    # Adjust column widths
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_length = max((len(str(c.value)) for c in col if c.value is not None), default=0)
        ws.column_dimensions[col_letter].width = max(12, max_length + 2)

    ws.freeze_panes = "A2"


def run_pipeline():
    excel_path = _resolve_excel_path()
    print(f"📘 Using workbook: {excel_path}")

    # --- Load canonical inputs ---
    census_df = load_census_from_excel(str(excel_path), sheet_name="Census Input")
    rules_df = load_staffing_rules_from_excel(str(excel_path), sheet_name="Staffing Grid")
    resources_df = load_resources_from_excel(str(excel_path), sheet_name="Resource Input")
    shifts_df = load_shifts_from_excel(str(excel_path), sheet_name="Shifts Input")

    print("✅ Loaded Census, Staffing Grid, Resource Input, and Shifts Input")

    # --- Build staffing plan ---
    # NOTE: Season must be selected manually ("High", "Medium", "Low")
    plan_df = build_staffing_plan(census_df, rules_df, season="Medium")

    # --- Compare vs resources ---
    pos_ctrl_df = build_position_control(resources_df)
    comp_df = compare_plan_vs_resources(plan_df, pos_ctrl_df)

    # --- Assign staff to shifts ---
    schedule_df = assign_staff_to_shifts(plan_df, shifts_df)

    # --- Normalize dates to yyyy-mm-dd (remove timestamp) ---
    for df in [plan_df, comp_df, schedule_df]:
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"]).dt.date

    # --- Write outputs ---
    out_path = excel_path.parent / "staffing_outputs.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        plan_df.to_excel(writer, sheet_name="Staffing Plan", index=False)
        comp_df.to_excel(writer, sheet_name="Staffing vs Resources", index=False)
        schedule_df.to_excel(writer, sheet_name="Staffing Schedule", index=False)

    # --- Apply formatting ---
    wb = load_workbook(out_path)
    for sheet in wb.sheetnames:
        _format_sheet(wb[sheet], sheet)
    wb.save(out_path)

    print(f"\n✅ Wrote outputs to {out_path}")
    print("📝 Staffing Plan (preview):")
    print(plan_df.head(5))
    print("\n📊 Staffing vs Resources (preview):")
    print(comp_df.head(5))
    print("\n⏰ Staffing Schedule (preview):")
    print(schedule_df.head(5))


if __name__ == "__main__":
    run_pipeline()
