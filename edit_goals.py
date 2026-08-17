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

            rows.append(
                {
                    "goal_id": newest.get("goal_id"),
                    "diver": selected_diver,
                    "goal_type": goal_type,
                    "goal_dive_number": newest.get("goal_dive_number"),
                    "goal_score": newest.get("goal_score"),
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
                    "date_added": None,
                }
            )

    df = pd.DataFrame(rows)

    st.subheader("Goals")

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="goals_editor",
        disabled=[
            "goal_id",
            "date_added",
            "goal_type",
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

            for idx, row in edited_df.iterrows():
                record = row.to_dict()

                for k, v in record.items():
                    if pd.isna(v):
                        record[k] = None

                goal_type = record.get("goal_type")

                if not goal_type:
                    continue

                # -------------------------
                # Dive Goals
                # -------------------------
                if goal_type in DIVE_GOAL_TYPES:
                    record["goal_score"] = None

                    if not record.get("goal_dive_number"):
                        continue

                # -------------------------
                # Score Goals
                # -------------------------
                elif goal_type in SCORE_GOAL_TYPES:
                    record["goal_dive_number"] = None

                    if record.get("goal_score") is None:
                        continue

                insert_record = {
                    "diver": selected_diver,
                    "goal_type": goal_type,
                    "goal_dive_number": record.get("goal_dive_number"),
                    "goal_score": record.get("goal_score"),
                }

                goal_id = record.get("goal_id")

                # -------------------------
                # EXISTING ROW
                # Insert only if changed
                # -------------------------
                if goal_id is not None:
                    original_row = df.iloc[idx]

                    original_record = {
                        "diver": selected_diver,
                        "goal_type": original_row.get("goal_type"),
                        "goal_dive_number": original_row.get("goal_dive_number"),
                        "goal_score": original_row.get("goal_score"),
                    }

                    if insert_record != original_record:
                        (
                            supabase.table("goals")
                            .insert(insert_record)
                            .execute()
                        )
                        inserts_made += 1

                # -------------------------
                # NEW ROW
                # -------------------------
                else:
                    (
                        supabase.table("goals")
                        .insert(insert_record)
                        .execute()
                    )
                    inserts_made += 1

            st.success(f"{inserts_made} goal(s) inserted successfully.")

            # Refresh editor with latest data
            st.rerun()

        except Exception as ex:
            st.error(f"Save failed: {ex}")