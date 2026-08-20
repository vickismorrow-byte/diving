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


    completed_score_goals = {}

    if not results_df.empty:

        meet_scores = (
            results_df.groupby(
                ["meet"],
                as_index=False
            )
            .agg(
                TotalScore=("score", "sum"),
                DiveCount=("score", "count")
            )
        )

        meet_scores = meet_scores[
            meet_scores["meet"]
            .astype(str)
            .str[:4]
            == current_diving_year
        ]

        six_dive_best = 0.0
        eleven_dive_best = 0.0

        six_scores = meet_scores[
            meet_scores["DiveCount"] == 6
        ]

        eleven_scores = meet_scores[
            meet_scores["DiveCount"] == 11
        ]

        if not six_scores.empty:
            six_dive_best = float(
                six_scores["TotalScore"].max()
            )

        if not eleven_scores.empty:
            eleven_dive_best = float(
                eleven_scores["TotalScore"].max()
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

    # Keep a copy of ALL goals for history
    all_goals_df = goals_df.copy()

    if not goals_df.empty:
        goals_df["date_added"] = pd.to_datetime(
            goals_df["date_added"]
        )

        all_goals_df["date_added"] = pd.to_datetime(
            all_goals_df["date_added"]
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

                    goal_score = float(record["goal_score"])

                    completed = False

                    if (
                        record["goal_type"]
                        == "6-Dive Score"
                    ):
                        completed = (
                            six_dive_best >= goal_score
                        )

                    elif (
                        record["goal_type"]
                        == "11-Dive Score"
                    ):
                        completed = (
                            eleven_dive_best >= goal_score
                        )

                    if completed:
                        row["Goal"] = (
                            f"{goal_score:.2f} ✅"
                        )
                    else:
                        row["Goal"] = (
                            f"{goal_score:.2f}"
                        )

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

    # -------------------------
    # Completed Goals History
    # -------------------------
    completed_goal_rows = []

    # results_df already loaded earlier
    if not results_df.empty:
        results_df["meet"] = results_df["meet"].astype(str)

    for _, record in all_goals_df.iterrows():
        completed_date = None
        goal_value = ""

        if pd.notna(record.get("goal_dive_number")):
            dive_number = str(record["goal_dive_number"])

            matching_results = results_df[
                (results_df["dive_number"].astype(str) == dive_number)
                & (results_df["score"] > 0)
                & (
                    results_df["meet"].str[:4]
                    == current_diving_year
                )
            ].sort_values("meet")

            if not matching_results.empty:
                completed_date = matching_results.iloc[0]["meet"]

            goal_value = dive_number

        elif pd.notna(record.get("goal_score")):
            goal_score = float(record["goal_score"])
            goal_value = f"{goal_score:.2f}"

            if record["goal_type"] == "6-Dive Score":
                qualifying_meets = meet_scores[
                    (meet_scores["DiveCount"] == 6)
                    & (meet_scores["TotalScore"] >= goal_score)
                ].sort_values("meet")

            elif record["goal_type"] == "11-Dive Score":
                qualifying_meets = meet_scores[
                    (meet_scores["DiveCount"] == 11)
                    & (meet_scores["TotalScore"] >= goal_score)
                ].sort_values("meet")
            else:
                qualifying_meets = pd.DataFrame()

            if not qualifying_meets.empty:
                completed_date = qualifying_meets.iloc[0]["meet"]

        if completed_date:
            completed_goal_rows.append(
                {
                    "First Competed At": completed_date,
                    "Type": record["goal_type"],
                    "Goal": goal_value,
                }
            )

    with st.expander("All Completed Goals This Season"):
        if completed_goal_rows:
            completed_df = pd.DataFrame(completed_goal_rows)

            completed_df = completed_df.sort_values(
                "First Competed At",
                ascending=False
            )

            st.dataframe(
                completed_df,
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info(
                "No completed goals found for the current diving year."
            )