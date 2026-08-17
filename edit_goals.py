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

    goals_rows = (
        supabase.table("goals")
        .select("*")
        .execute()
        .data
    )

    dive_numbers = [
        d["dive_number"]
        for d in dives_rows
    ]

    # -------------------------
    # Filters
    # -------------------------
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

    available_divers = sorted(
        {
            d["diver"]
            for d in filtered_divers
        }
    )

    with col2:
        selected_diver = st.selectbox(
            "Diver",
            ["Select Diver"] + available_divers
        )

    if selected_diver == "Select Diver":
        return

    # -------------------------
    # Existing Goals
    # -------------------------
    filtered_goals = [
        g
        for g in goals_rows
        if g["diver"] == selected_diver
    ]

    df = pd.DataFrame(filtered_goals)

    if df.empty:
        df = pd.DataFrame(
            columns=[
                "goal_id",
                "diver",
                "goal_type",
                "dive_number",
                "score_goal",
                "date_added",
            ]
        )

    st.subheader("Goals")

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        key="goals_editor",
        disabled=[
            "goal_id",
            "date_added",
        ],
        column_config={
            "diver": st.column_config.SelectboxColumn(
                "Diver",
                options=available_divers,
                required=True,
            ),
            "goal_type": st.column_config.SelectboxColumn(
                "Goal Type",
                options=GOAL_TYPES,
                required=True,
            ),
            "dive_number": st.column_config.SelectboxColumn(
                "Dive Number",
                options=dive_numbers,
            ),
            "score_goal": st.column_config.NumberColumn(
                "Score Goal",
                format="%.2f",
            ),
        },
    )

    # -------------------------
    # Save Changes
    # -------------------------
    # -------------------------
# Save Changes
# -------------------------
if st.button(
    "Save Changes",
    type="primary",
):

    try:

        existing_ids = {
            r["goal_id"]
            for r in goals_rows
            if r.get("goal_id") is not None
        }

        for _, row in edited_df.iterrows():

            record = row.to_dict()

            goal_id = record.get("goal_id")
            goal_type = record.get("goal_type")

            if not goal_type:
                continue

            # Convert NaN to None
            for k, v in record.items():
                if pd.isna(v):
                    record[k] = None

            # Apply constraint rules
            if goal_type in DIVE_GOAL_TYPES:

                record["score_goal"] = None

                if not record.get("dive_number"):
                    continue

            elif goal_type in SCORE_GOAL_TYPES:

                record["dive_number"] = None

                if record.get("score_goal") is None:
                    continue

            # UPDATE EXISTING
            if (
                goal_id is not None
                and goal_id in existing_ids
            ):

                update_record = {
                    "diver": record["diver"],
                    "goal_type": record["goal_type"],
                    "dive_number": record.get("dive_number"),
                    "score_goal": record.get("score_goal"),
                }

                (
                    supabase.table("goals")
                    .update(update_record)
                    .eq("goal_id", int(goal_id))
                    .execute()
                )

            # INSERT NEW
            else:

                insert_record = {
                    "diver": record["diver"],
                    "goal_type": record["goal_type"],
                    "dive_number": record.get("dive_number"),
                    "score_goal": record.get("score_goal"),
                }

                (
                    supabase.table("goals")
                    .insert(insert_record)
                    .execute()
                )

        st.success("Goals updated successfully.")
        st.rerun()

    except Exception as ex:
        st.error(f"Update failed: {ex}")