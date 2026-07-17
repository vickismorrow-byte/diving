import io
import re
import pandas as pd
import streamlit as st

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
)

from reportlab.lib import colors
from reportlab.lib import pagesizes
from reportlab.lib.styles import getSampleStyleSheet


CATEGORY_MAP = {
    "1": "Front",
    "2": "Back",
    "3": "Rev",
    "4": "Inw",
    "5": "Tw"
}


METRICS = [
    "Front Vol",
    "Front Opt",
    "Back Vol",
    "Back Opt",
    "Rev Vol",
    "Rev Opt",
    "Inw Vol",
    "Inw Opt",
    "Tw Vol",
    "Tw Opt",
    "11th Dive",
    "11-Dive Best",
    "11-Dive Proj"
]


def dive_base(dive_number):
    """
    103B -> 103
    5152D -> 5152
    """
    return re.sub(r"[A-Z]$", "", dive_number)


def extract_year(meet_name):
    try:
        return str(meet_name).split("_")[0]
    except:
        return None


def extract_season(meet_name):
    try:
        val = str(meet_name).split("_")[1]
        return "Girls" if val == "G" else "Boys"
    except:
        return None


def build_results_dataframe(supabase):

    results = (
        supabase
        .table("results")
        .select("*")
        .execute()
        .data
    )

    meets = (
        supabase
        .table("meets")
        .select("*")
        .execute()
        .data
    )

    results_df = pd.DataFrame(results)
    meets_df = pd.DataFrame(meets)

    if results_df.empty:
        return pd.DataFrame()

    if meets_df.empty:
        return pd.DataFrame()

    df = results_df.merge(
        meets_df[["meet"]],
        on="meet",
        how="left"
    )

    df["Year"] = df["meet"].apply(extract_year)
    df["Season"] = df["meet"].apply(extract_season)

    df["Category"] = (
        df["dive_number"]
        .astype(str)
        .str[0]
        .map(CATEGORY_MAP)
    )

    return df


def best_category_pair(category_df):

    if category_df.empty:
        return None

    dives = []

    for dive_number, dive_rows in category_df.groupby("dive_number"):

        dives.append({
            "Dive": dive_number,
            "Base": dive_base(dive_number),
            "TopScore": float(dive_rows["score"].max()),
            "HasV": (dive_rows["type"] == "V").any(),
            "HasO": (dive_rows["type"] == "O").any(),
            "Meet": dive_rows.loc[
                dive_rows["score"].idxmax(),
                "meet"
            ]
        })

    dives = pd.DataFrame(dives)

    vols = dives[dives["HasV"]]
    opts = dives[dives["HasO"]]

    best_combo = None
    best_total = -1

    for _, vol in vols.iterrows():

        for _, opt in opts.iterrows():

            if vol["Dive"] == opt["Dive"]:
                continue

            if vol["Base"] == opt["Base"]:
                continue

            total = vol["TopScore"] + opt["TopScore"]

            if total > best_total:

                best_total = total

                best_combo = {
                    "VolDive": vol["Dive"],
                    "VolScore": vol["TopScore"],
                    "VolMeet": vol["Meet"],
                    "OptDive": opt["Dive"],
                    "OptScore": opt["TopScore"],
                    "OptMeet": opt["Meet"]
                }

    return best_combo


def calculate_best_meet(df_diver):
    meet_scores = (
        df_diver
        .groupby("meet")
        .agg(
            score=("score", "sum"),
            dives=("score", "count")
        )
    )

    valid_meets = meet_scores[meet_scores["dives"] == 11]

    if valid_meets.empty:
        return 0

    return float(valid_meets["score"].max())



def build_diver_projection(df_diver):

    result = {}

    selected_dives = set()

    projection_total = 0

    for cat in ["Front", "Back", "Rev", "Inw", "Tw"]:

        pair = best_category_pair(
            df_diver[df_diver["Category"] == cat]
        )

        if pair is None:

            result[f"{cat} Vol"] = 0
            result[f"{cat} Opt"] = 0

            continue

        result[f"{cat} Vol"] = pair["VolScore"]
        result[f"{cat} Opt"] = pair["OptScore"]

        result[f"{cat} Vol Dive"] = pair["VolDive"]
        result[f"{cat} Opt Dive"] = pair["OptDive"]

        result[f"{cat} Vol Meet"] = pair["VolMeet"]
        result[f"{cat} Opt Meet"] = pair["OptMeet"]

        selected_dives.add(pair["VolDive"])
        selected_dives.add(pair["OptDive"])

        projection_total += pair["VolScore"]
        projection_total += pair["OptScore"]

    all_dives = (
        df_diver
        .groupby(["dive_number"])
        .agg(
            TopScore=("score", "max"),
            BestMeet=("meet", "first")
        )
        .reset_index()
    )

    remaining = all_dives[
        ~all_dives["dive_number"].isin(selected_dives)
    ]

    if not remaining.empty:

        remaining = remaining.sort_values(
            "TopScore",
            ascending=False
        )

        eleventh = remaining.iloc[0]

        result["11th Dive"] = float(eleventh["TopScore"])
        result["11th Dive Dive"] = eleventh["dive_number"]
        result["11th Dive Meet"] = eleventh["BestMeet"]

        projection_total += float(eleventh["TopScore"])

    else:

        result["11th Dive"] = 0

    result["11-Dive Proj"] = projection_total

    result["11-Dive Best"] = calculate_best_meet(df_diver)

    return result


def assign_points(rank_df, metric):
    scores = (
        rank_df[["Diver", metric]]
        .sort_values(metric, ascending=False)
        .reset_index(drop=True)
    )

    mapping = {}
    rank_position = 1

    for _, row in scores.iterrows():
        score = row[metric]

        if score <= 0:
            mapping[row["Diver"]] = 0
            continue

        mapping[row["Diver"]] = max(0, 51 - rank_position)
        rank_position += 1

    return mapping


def render_power_rankings_page(supabase):

    st.header("Power Rankings")

    df = build_results_dataframe(supabase)

    if df.empty:
        st.warning("No data found.")
        return

    years = sorted(df["Year"].dropna().unique())

    year = st.selectbox(
        "Year",
        years
    )

    season = st.selectbox(
        "Season",
        ["Girls", "Boys"]
    )

    filtered = df[
        (df["Year"] == year)
        &
        (df["Season"] == season)
    ]

    if filtered.empty:
        st.warning("No results found.")
        return

    rows = []

    for diver, diver_df in filtered.groupby("diver"):

        r = build_diver_projection(diver_df)

        r["Diver"] = diver

        rows.append(r)

    rankings = pd.DataFrame(rows)

    for metric in METRICS:

        rankings[f"{metric} Pts"] = (
            rankings["Diver"]
            .map(assign_points(rankings, metric))
        )

    point_cols = [
        c for c in rankings.columns
        if c.endswith("Pts")
    ]

    rankings["Power Points"] = rankings[
        point_cols
    ].sum(axis=1)

    rankings = rankings.sort_values(
        "Power Points",
        ascending=False
    ).reset_index(drop=True)

    rankings["Power Ranking"] = (
        rankings["Power Points"]
        .rank(
            method="min",
            ascending=False
        )
        .astype(int)
    )

    display_cols = [
        "Power Ranking",
        "Diver",
        *point_cols,
        "Power Points"
    ]

    st.subheader("Display")

    st.dataframe(
        rankings[display_cols],
        use_container_width=True
    )

    # -------------------------
    # CSV MEDIUM
    # -------------------------

    csv_medium = rankings[display_cols].to_csv(
        index=False
    )

    st.download_button(
        "CSV - Medium",
        csv_medium,
        file_name=f"power_rankings_{year}_{season}.csv",
        mime="text/csv"
    )

    # -------------------------
    # CSV DETAILED
    # -------------------------

    detailed = rankings.copy()

    detailed_csv = detailed.to_csv(index=False)

    st.download_button(
        "CSV - Detailed",
        detailed_csv,
        file_name=f"power_rankings_detailed_{year}_{season}.csv",
        mime="text/csv"
    )

    # -------------------------
    # PDF SIMPLE
    # -------------------------

    simple_buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        simple_buffer,
        pagesize=pagesizes.portrait(
            pagesizes.letter
        )
    )

    table_data = [
        ["Power Ranking", "Diver", "Power Points"]
    ]

    for _, row in rankings.iterrows():

        table_data.append([
            row["Power Ranking"],
            row["Diver"],
            row["Power Points"]
        ])

    tbl = Table(table_data)

    tbl.setStyle(
        TableStyle([
            ("GRID", (0,0), (-1,-1), 1, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)
        ])
    )

    doc.build([tbl])

    st.download_button(
        "PDF - Simple",
        simple_buffer.getvalue(),
        file_name=f"power_rankings_simple_{year}_{season}.pdf",
        mime="application/pdf"
    )

    # -------------------------
    # PDF MEDIUM
    # -------------------------

    medium_buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        medium_buffer,
        pagesize=pagesizes.landscape(
            pagesizes.letter
        )
    )

    pdf_table = [display_cols]

    for _, row in rankings.iterrows():

        pdf_table.append([
            row[col]
            for col in display_cols
        ])

    tbl = Table(pdf_table)

    tbl.setStyle(
        TableStyle([
            ("GRID", (0,0), (-1,-1), 1, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("FONTSIZE", (0,0), (-1,-1), 7)
        ])
    )

    doc.build([tbl])

    st.download_button(
        "PDF - Medium",
        medium_buffer.getvalue(),
        file_name=f"power_rankings_medium_{year}_{season}.pdf",
        mime="application/pdf"
    )