import streamlit as st
import pandas as pd
from datetime import date


GOAL_TYPES = [
    "Forward",
    "Backward",
    "Reverse",
    "Inward",
    "Twister",
    "6-Dive Score",
    "11-Dive Score",
]


def render_view_goals_page(supabase):
    st.title("View Goals")

    # -------------------------
    # Load Divers
    # -------------------------
    divers_rows = (
        supabase.table("divers")
        .select("diver, season")
        .order("diver")
        .execute()
        .data
    )

    col1, col2 = st.columns(2)

    with col1:
        season_filter = st.selectbox(
            "Season",
            ["All", "Boys", "Girls"]
        )

    filtered_divers = divers_rows.copy()

    if season_filter != "All":
        filtered_divers = [
            d
            for d in filtered_divers
            if d["season"] == season_filter
        ]

    diver_list = sorted(
        {
            d["diver"]
            for d in filtered_divers
            if d.get("diver")
        }
    )

    with col2:
        selected_diver = st.selectbox(
            "Diver *",
            ["Select Diver"] + diver_list,
        )

    if selected_diver == "Select Diver":
        return

    # -------------------------
    # Current Diving Year
    # -------------------------
    today = date.today()

    diver_season = next(
        (
            d["season"]
            for d in divers_rows
            if d["diver"] == selected_diver
        ),
        None,
    )

    if (
        diver_season == "Boys"
        and today.month >= 8
    ):
        current_diving_year = str(today.year + 1)
    else:
        current_diving_year = str(today.year)

    # -------------------------
    # Load Completed Dives
    # -------------------------
    results = (
        supabase.table("results")
        .select("dive_number,score,meet")
        .eq("diver", selected_diver)
        .execute()
        .data
    )

    completed_dives = set()

    results_df = pd.DataFrame(results)

    if not results_df.empty:
        results_df["meet"] = results_df["meet"].astype(str)

        completed_dives = set(
            results_df[
                (results_df["score"] > 0)
                & (
                    results_df["meet"].str[:4]
                    == current_diving_year
                )
            ]["dive_number"]
        )

    # -------------------------
    # Load Goals
    # -------------------------
    goals = (
        supabase.table("goals")
        .select("*")
        .eq("diver", selected_diver)
        .order("date_added", desc=True)
        .execute()
        .data
    )

    goals_df = pd.DataFrame(goals)

    if not goals_df.empty:
        goals_df["date_added"] = pd.to_datetime(
            goals_df["date_added"]
        )

        goals_df = (
            goals_df
            .sort_values("date_added", ascending=False)
            .drop_duplicates("goal_type")
        )

    table_rows = []

    for goal_type in GOAL_TYPES:

        row = {
            "Type": goal_type,
            "Goal": "",
            "Date Added": ""
        }

        if not goals_df.empty:

            match = goals_df[
                goals_df["goal_type"] == goal_type
            ]

            if not match.empty:

                record = match.iloc[0]

                if pd.notna(record.get("goal_score")):
                    row["Goal"] = f"{float(record['goal_score']):.2f}"

                elif pd.notna(record.get("goal_dive_number")):
                    dive_number = str(record["goal_dive_number"])

                    if dive_number in completed_dives:
                        row["Goal"] = f"{dive_number} ✅"
                    else:
                        row["Goal"] = dive_number

                if pd.notna(record.get("date_added")):
                    row["Date Added"] = (
                        pd.to_datetime(
                            record["date_added"]
                        ).strftime("%Y-%m-%d")
                    )

        table_rows.append(row)

    display_df = pd.DataFrame(table_rows)

    st.subheader(f"{selected_diver} Goals")

    st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True
    )
