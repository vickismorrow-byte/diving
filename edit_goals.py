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

DIVE_GOAL_TYPES = [
    "Forward",
    "Backward",
    "Reverse",
    "Inward",
    "Twister",
]

SCORE_GOAL_TYPES = [
    "6-Dive Score",
    "11-Dive Score",
]


def render_edit_goals_page(supabase):
    st.title("View & Edit Goals")

    # -------------------------
    # Load Lookup Data
    # -------------------------
    divers_rows = (
        supabase.table("divers")
        .select("diver, season")
        .order("diver")
        .execute()
        .data
    )

    dives_rows = (
        supabase.table("dives")
        .select("dive_number")
        .order("dive_number")
        .execute()
        .data
    )


    # -------------------------
    # Filters
    # -------------------------
    col1, col2 = st.columns(2)

    with col1:
        season_filter = st.selectbox(
            "Season",
            ["All", "Boys", "Girls"],
        )

    filtered_divers = divers_rows.copy()

    if season_filter != "All":
        filtered_divers = [
            d
            for d in filtered_divers
            if d["season"] == season_filter
        ]

    available_divers = sorted(
        {
            d["diver"]
            for d in filtered_divers
        }
    )

    with col2:
        selected_diver = st.selectbox(
            "Diver",
            ["Select Diver"] + available_divers,
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


    goals_rows = (
        supabase.table("goals")
        .select("*")
        .execute()
        .data
    )

    dive_numbers = [d["dive_number"] for d in dives_rows]

    # -------------------------
    # Completed Dives
    # -------------------------
    results_rows = (
        supabase.table("results")
        .select("dive_number,score,meet")
        .eq("diver", selected_diver)
        .execute()
        .data
    )

    completed_dives = set()

    results_df = pd.DataFrame(results_rows)

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

    six_dive_best = 0.0
    eleven_dive_best = 0.0

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
    # Build Fixed 7 Goal Rows
    # -------------------------

    # -------------------------
    # Build Fixed 7 Goal Rows
    # -------------------------
    diver_goals = [
        g
        for g in goals_rows
        if g["diver"] == selected_diver
    ]

    rows = []

    for goal_type in GOAL_TYPES:
        matching = [
            g
            for g in diver_goals
            if g.get("goal_type") == goal_type
        ]

        if matching:
            newest = sorted(
                matching,
                key=lambda x: str(x.get("date_added") or ""),
                reverse=True,
            )[0]

            goal_dive_number = newest.get("goal_dive_number")

            goal_score = newest.get("goal_score")

            status = ""

            if goal_type in [
                "Forward",
                "Backward",
                "Reverse",
                "Inward",
                "Twister",
            ]:
                if (
                    goal_dive_number
                    and str(goal_dive_number)
                    in completed_dives
                ):
                    status = "✅ Completed"

            elif goal_type == "6-Dive Score":
                if (
                    goal_score is not None
                    and float(goal_score)
                    <= six_dive_best
                ):
                    status = "✅ Completed"

            elif goal_type == "11-Dive Score":
                if (
                    goal_score is not None
                    and float(goal_score)
                    <= eleven_dive_best
                ):
                    status = "✅ Completed"

            rows.append(
                {
                    "goal_id": newest.get("goal_id"),
                    "diver": selected_diver,
                    "goal_type": goal_type,
                    "goal_dive_number": goal_dive_number,
                    "goal_score": goal_score,
                    "status": status,
                    "date_added": newest.get("date_added"),
                }
            )
            
        else:
            rows.append(
                {
                    "goal_id": None,
                    "diver": selected_diver,
                    "goal_type": goal_type,
                    "goal_dive_number": None,
                    "goal_score": None,
                    "status": "",
                    "date_added": None,
                }
            )

    df = pd.DataFrame(rows)

    st.subheader("Goals")

    edited_df = st.data_editor(
        df,
        key="goals_editor",
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=[
            "goal_id",
            "date_added",
            "goal_type",
            "status",
        ],
        column_config={
            "diver": st.column_config.TextColumn(
                "Diver",
                disabled=True,
            ),
            "goal_type": st.column_config.TextColumn(
                "Goal Type",
            ),
            "goal_dive_number": st.column_config.SelectboxColumn(
                "Dive Number",
                options=dive_numbers,
            ),
            "goal_score": st.column_config.NumberColumn(
                "Goal Score",
                format="%.2f",
            ),
            "status": st.column_config.TextColumn(
                "Status",
                help="Completed in current diving year",
            ),
        },
    )

    # -------------------------
    # Save Changes
    # -------------------------
    if st.button(
        "Save Changes",
        type="primary",
    ):
        try:
            inserts_made = 0

            editor_state = st.session_state.get(
                "goals_editor",
                {}
            )

            edited_rows = editor_state.get(
                "edited_rows",
                {}
            )

            # Nothing changed
            if not edited_rows:
                st.info("No changes detected.")
                return

            for row_index in edited_rows.keys():

                row = edited_df.iloc[row_index]

                goal_type = row["goal_type"]

                goal_dive_number = row["goal_dive_number"]
                goal_score = row["goal_score"]

                if pd.isna(goal_dive_number):
                    goal_dive_number = None

                if pd.isna(goal_score):
                    goal_score = None

                # -------------------------
                # Dive Goals
                # -------------------------
                if goal_type in DIVE_GOAL_TYPES:

                    goal_score = None

                    if not goal_dive_number:
                        continue

                # -------------------------
                # Score Goals
                # -------------------------
                elif goal_type in SCORE_GOAL_TYPES:

                    goal_dive_number = None

                    if goal_score is None:
                        continue

                insert_record = {
                    "diver": selected_diver,
                    "goal_type": goal_type,
                    "goal_dive_number": goal_dive_number,
                    "goal_score": goal_score,
                }

                (
                    supabase.table("goals")
                    .insert(insert_record)
                    .execute()
                )

                inserts_made += 1

            st.success(
                f"{inserts_made} goal(s) inserted successfully."
            )

            st.rerun()

        except Exception as ex:
            st.error(f"Save failed: {ex}")