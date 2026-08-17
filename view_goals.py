import streamlit as st
import pandas as pd


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
                    row["Goal"] = str(record["goal_dive_number"])

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
    st.write(goals)