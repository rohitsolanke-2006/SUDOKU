import io
from typing import List, Dict, Any, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.models.schemas import SignalModel

def build_scenario_input_workbook(scenario_id: str, signals: List[SignalModel], scenario_title: str, scenario_description: str) -> io.BytesIO:
    """
    Builds a professional, formatted Excel workbook for sample signal input data.
    Includes a dedicated README worksheet explaining the scenario to judges/evaluators,
    and a formatted 'Signal Register' sheet with frozen headers and auto-sized columns.
    """
    wb = openpyxl.Workbook()
    
    # -------------------------------------------------------------------------
    # Sheet 1: README & Scenario Guide
    # -------------------------------------------------------------------------
    ws_readme = wb.active
    ws_readme.title = "Scenario Guide"
    ws_readme.views.sheetView[0].showGridLines = True

    # Title styling
    title_font = Font(name="Calibri", size=16, bold=True, color="1F2423")
    subtitle_font = Font(name="Calibri", size=11, bold=True, color="247C70")
    body_font = Font(name="Calibri", size=10, color="333333")
    bold_body = Font(name="Calibri", size=10, bold=True, color="1F2423")
    box_fill = PatternFill(start_color="F4F6F4", end_color="F4F6F4", fill_type="solid")
    accent_fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin', color='C8CECA'),
        right=Side(style='thin', color='C8CECA'),
        top=Side(style='thin', color='C8CECA'),
        bottom=Side(style='thin', color='C8CECA')
    )

    ws_readme["B2"] = "IO SIGNAL SUDOKU — Industrial I/O Allocation Platform"
    ws_readme["B2"].font = title_font
    ws_readme["B3"] = f"DEMO SCENARIO DATASET: {scenario_title}"
    ws_readme["B3"].font = subtitle_font

    ws_readme["B5"] = "SCENARIO OVERVIEW"
    ws_readme["B5"].font = bold_body
    ws_readme["B6"] = scenario_description
    ws_readme["B6"].font = body_font

    # Info Box
    info_rows = [
        ("Platform Target", "Emerson DeltaV Electronic Marshaling Cabinet CAB-01 (64 CHARMs)"),
        ("Optimization Engine", "Google OR-Tools CP-SAT v9.10+ (Constraint Programming)"),
        ("Independent Validator", "IEC 61131-2, IEC 60079-11 (Ex-ia), IEEE 518 Noise Segregation"),
        ("Data Origin", "SYNTHETIC DEMO BENCHMARK — Clearly labeled for hackathon evaluation"),
        ("Signal Count", f"{len(signals)} instrumentation loops in this register")
    ]

    start_r = 8
    for label, val in info_rows:
        ws_readme.cell(row=start_r, column=2, value=label).font = bold_body
        ws_readme.cell(row=start_r, column=2).fill = box_fill
        ws_readme.cell(row=start_r, column=2).border = thin_border
        
        ws_readme.cell(row=start_r, column=3, value=val).font = body_font
        ws_readme.cell(row=start_r, column=3).fill = box_fill
        ws_readme.cell(row=start_r, column=3).border = thin_border
        start_r += 1

    ws_readme.column_dimensions["B"].width = 24
    ws_readme.column_dimensions["C"].width = 65

    # -------------------------------------------------------------------------
    # Sheet 2: Signal Register (Importable Data)
    # -------------------------------------------------------------------------
    ws_data = wb.create_sheet(title="Signal Register")
    ws_data.views.sheetView[0].showGridLines = True

    headers = [
        "tag",
        "description",
        "signal_type",
        "voltage",
        "is_intrinsic_safety",
        "safety_integrity_level",
        "multicore_cable_id",
        "cable_pair_index",
        "power_dissipation_watts",
        "locked",
        "assigned_position_id"
    ]

    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="247C70", end_color="247C70", fill_type="solid")
    alt_fill = PatternFill(start_color="F8FAF9", end_color="F8FAF9", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    # Write headers
    for col_idx, h in enumerate(headers, start=1):
        c = ws_data.cell(row=1, column=col_idx, value=h)
        c.font = header_font
        c.fill = header_fill
        c.alignment = center_align
        c.border = thin_border

    # Write data rows
    for r_idx, s in enumerate(signals, start=2):
        row_values = [
            s.tag,
            s.description,
            s.signal_type,
            s.voltage or "24VDC",
            "TRUE" if s.is_intrinsic_safety else "FALSE",
            s.safety_integrity_level or "BPCS",
            s.multicore_cable_id or "",
            s.cable_pair_index or "",
            s.power_dissipation_watts,
            "TRUE" if s.locked else "FALSE",
            s.assigned_position_id or ""
        ]
        
        fill = alt_fill if r_idx % 2 == 0 else PatternFill(fill_type=None)
        
        for col_idx, val in enumerate(row_values, start=1):
            cell = ws_data.cell(row=r_idx, column=col_idx, value=val)
            cell.font = body_font
            cell.border = thin_border
            if fill.fill_type:
                cell.fill = fill
            if col_idx in [1, 3, 4, 5, 6, 7, 8, 10, 11]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align

    # Freeze header
    ws_data.freeze_panes = "A2"
    ws_data.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(signals) + 1}"

    # Auto-adjust column widths
    for col in ws_data.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_data.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
