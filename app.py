import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path
from datetime import datetime

# Import your existing pipeline pieces
from pipeline.staffing_plan import build_staffing_plan_from_rules
from pipeline.position_control import build_position_control, compare_plan_vs_resources
from pipeline.scheduler import assign_staff_to_shifts
from pipeline.census_loader import load_census_with_season
from pipeline.excel_v010 import load_staffing_rules_from_excel, load_resources_from_excel, load_shifts_from_excel

# --- App title ---
st.set_page_config(page_title="HIRA Light – Shift Manager", layout="wide")
st.title("📘 HIRA Light – Master Shift Manager")

# --- Upload input file ---
uploaded_file = st.file_uploader("Upload your input workbook", type=["xlsx"])
if uploaded_file:
    st.success(f"Loaded: {uploaded_file.name}")

    # Save to a temp path for pandas/openpyxl
    temp_path = Path("data") / f"uploaded_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())

    # Load inputs
    census_df = load_census_with_season(str(temp_path), sheet_name="Census Input")
    rules_df = load_staffing_rules_from_excel(str(temp_path), sheet_name="Staffing Grid")
    resources_df = load_resources_from_excel(str(temp_path), sheet_name="Resource Input")
    shifts_df = load_shifts_from_excel(str(temp_path), sheet_name="Shifts Input")

    # --- Run pipeline ---
    plan_df = build_staffing_plan_from_rules(census_df, rules_df)
    pos_ctrl_df = build_position_control(resources_df)
    comp_df = compare_plan_vs_resources(plan_df, pos_ctrl_df)
    schedule_df = assign_staff_to_shifts(plan_df, shifts_df, yaml_path="config/settings.yaml")

        # --- Clean numeric columns to prevent Arrow conversion errors ---
    for col in ["Start", "End", "Hours", "Assigned"]:
        if col in schedule_df.columns:
            schedule_df[col] = pd.to_numeric(schedule_df[col], errors="coerce")

    # --- Normalize all Date columns to YYYY-MM-DD ---
    for df in [plan_df, comp_df, schedule_df]:
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"]).dt.date

    # --- Format shift times as HH:MM ---
    for col in ["Start", "End"]:
        if col in schedule_df.columns:
            schedule_df[col] = schedule_df[col].apply(
                lambda v: f"{int(v):02d}:00" if pd.notna(v) else ""
            )

    # --- KPIs for Summary ---
    total_shortages = comp_df["Shortage"].sum()
    total_surpluses = comp_df["Surplus"].sum()
    total_assigned = schedule_df["Assigned"].sum() if "Assigned" in schedule_df.columns else 0
    unique_dates = plan_df["Date"].nunique() if "Date" in plan_df.columns else 0

    # --- Build summary dataframe ---
    summary_data = {
        "Run Date": [datetime.now().strftime("%Y-%m-%d %H:%M")],
        "Input Workbook": [uploaded_file.name],
        "Staffing Plan Rows": [len(plan_df)],
        "Staffing vs Resources Rows": [len(comp_df)],
        "Staffing Schedule Rows": [len(schedule_df)],
        "Total Shortages": [total_shortages],
        "Total Surpluses": [total_surpluses],
        "Total Staff Assigned": [total_assigned],
        "Unique Dates Planned": [unique_dates],
    }
    summary_df = pd.DataFrame(summary_data)

    # --- Tabs for navigation ---
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Summary", "📝 Staffing Plan", "📉 Staffing vs Resources", "⏰ Staffing Schedule"]
    )

    with tab1:
        st.subheader("📊 Run Summary")
        st.table(summary_df)

        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📉 Total Shortages", int(total_shortages))
        col2.metric("📈 Total Surpluses", int(total_surpluses))
        col3.metric("👥 Total Staff Assigned", int(total_assigned))
        col4.metric("📅 Unique Dates Planned", int(unique_dates))

        # --- Shortages vs Surpluses Over Time ---
    if "Date" in comp_df.columns and "Gap" in comp_df.columns:
        st.subheader("📉 Shortages vs Surpluses Over Time")

        gap_over_time = (
            comp_df.groupby("Date", as_index=False)[["Shortage", "Surplus"]].sum()
        )
        
        gap_melted = gap_over_time.melt(
            id_vars="Date",
            value_vars=["Shortage", "Surplus"],
            var_name="Type",
            value_name="Count"
        )

        # Toggle: line vs area
        chart_type = st.radio(
            "Chart Style", ["Line", "Area"], horizontal=True, index=0, key="gap_chart"
        )

        if chart_type == "Line":
            chart = (
                alt.Chart(gap_melted)
                .mark_line(point=True)
                .encode(
                    x="Date:T",
                    y="Count:Q",
                    color=alt.Color("Type:N", scale=alt.Scale(domain=["Shortages", "Surpluses"], range=["red", "green"])),
                    tooltip=["Date:T", "Type:N", "Count:Q"]
                )
                .properties(width="container", height=300)
            )
        else:  # Area chart
            chart = (
                alt.Chart(gap_melted)
                .mark_area(opacity=0.6)
                .encode(
                    x="Date:T",
                    y="Count:Q",
                    color=alt.Color("Type:N", scale=alt.Scale(domain=["Shortages", "Surpluses"], range=["red", "green"])),
                    tooltip=["Date:T", "Type:N", "Count:Q"]
                )
                .properties(width="container", height=300)
            )

        st.altair_chart(chart, use_container_width=True)

        st.caption(
            "This chart shows daily staffing balance:\n"
            "- **Line chart**: Emphasizes trend direction (day-to-day changes).\n"
            "- **Area chart**: Emphasizes magnitude (how big shortages/surpluses are)."
        )

    # --- Staff Assigned by Role & Season ---
    if {"Role", "SeasonLabel", "Assigned"}.issubset(schedule_df.columns):
        st.subheader("👥 Staff Assigned by Role & Season")

        role_season = (
            schedule_df.groupby(["SeasonLabel", "Role"])["Assigned"]
            .sum()
            .reset_index()
        )

        # Toggle: grouped vs stacked
        chart_style = st.radio(
            "Chart Style", ["Grouped", "Stacked"], horizontal=True, index=0
        )

        if chart_style == "Grouped":
            chart2 = (
                alt.Chart(role_season)
                .mark_bar()
                .encode(
                    x="Role:N",
                    y="Assigned:Q",
                    color="SeasonLabel:N",
                    column="SeasonLabel:N",  # side-by-side bars
                    tooltip=["Role:N", "SeasonLabel:N", "Assigned:Q"]
                )
                .properties(width=100, height=300)
            )
        else:  # Stacked
            chart2 = (
                alt.Chart(role_season)
                .mark_bar()
                .encode(
                    x="Role:N",
                    y="Assigned:Q",
                    color="SeasonLabel:N",
                    tooltip=["Role:N", "SeasonLabel:N", "Assigned:Q"]
                )
                .properties(width="container", height=300)
            )

        st.altair_chart(chart2, use_container_width=True)

        st.caption(
            "This chart compares total staff assigned per role (RN, NA, etc.) across different seasons.\n"
            "- **Grouped**: Shows separate bars per season (good for comparing seasonal variation).\n"
            "- **Stacked**: Shows total per role with seasonal breakdown (good for overall totals)."
        )

    with tab2:
        st.subheader("📝 Staffing Plan")
        styled_plan = plan_df.style.map(
            lambda v: "background-color: #c6efce" if isinstance(v, (int, float)) else "",
            subset=["Census"]
        )
        st.write(styled_plan.to_html(), unsafe_allow_html=True)

    with tab3:
        st.subheader("📉 Staffing vs Resources")
        styled_comp = comp_df.style.map(
            lambda v: "background-color: #f4cccc" if isinstance(v, (int, float)) and v < 0
            else ("background-color: #d9ead3" if isinstance(v, (int, float)) and v > 0 else ""),
            subset=["Gap"]
        )
        st.write(styled_comp.to_html(), unsafe_allow_html=True)

    with tab4:
        st.subheader("⏰ Staffing Schedule")
        st.dataframe(schedule_df)

    # --- Download results as Excel ---
    out_path = Path("data") / "staffing_outputs_streamlit.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        plan_df.to_excel(writer, sheet_name="Staffing Plan", index=False)
        comp_df.to_excel(writer, sheet_name="Staffing vs Resources", index=False)
        schedule_df.to_excel(writer, sheet_name="Staffing Schedule", index=False)

    with open(out_path, "rb") as f:
        st.download_button(
            label="📥 Download Full Results (Excel)",
            data=f,
            file_name="staffing_outputs.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("👆 Upload an Excel workbook to get started")
