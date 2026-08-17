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
        .dat*
    )

    dive_numbers = [
        d["dive_number"]
        for d in dives_rows
    ]

    # ---------*---------------
    # Filters
    * -------------------------
    col*, col2 = st.columns(2)

    with c*l1:
        season_filter = st.sel*ctbox(
            "Season",
     *      ["All", "Boys", "Girls"]
   *    )

    filtered_divers = diver*_rows.copy()

    if season_filter*!= "All":
        filtered_divers * [
            d
            for d in filtered_divers
            if d["season"] == season_filter
        ]

    available_divers = sorted(*        {
            d["diver"]
 *          for d in filtered_divers*        }
    )

    with col2:
  *     selected_diver = st.selectbox*
            "Diver *",
          * ["Select Diver"] + available_dive*s
        )

    if selected_diver*== "Select Diver":
        return
*    # -------------------------
  * # Existing Goals
    # ----------*--------------
    filtered_goals * [
        g
        for g in goals_rows
        if g["diver"] == selected_diver
    ]

    df = pd.Data*rame(filtered_goals)

    if df.em*ty:
        df = pd.DataFrame(
   *        columns=[
                "goal_id",
                "diver",
                "goal_type",
                "dive_number",
                "score_goal",
                "date_added",
            ]
     *  )

    st.subheader("Goals")

  * edited_df = st.data_editor(
     *  df,
        use_container_width=*rue,
        num_rows="dynamic",
 *      key="goals_editor",
        *isabled=[
            "goal_id",
            "date_added",
        ],*        column_config={
          * "diver": st.column_config.Selectb*xColumn(
                "Diver",
*               options=available_d*vers,
                required=Tru*,
            ),
            "goal*type": st.column_config.SelectboxC*lumn(
                "Goal Type",*                options=GOAL_TYPES*
                required=True,
  *         ),
            "dive_numb*r": st.column_config.SelectboxColu*n(
                "Dive Number",
*               options=dive_number*,
            ),
            "scor*_goal": st.column_config.NumberCol*mn(
                "Score Goal",
*               format="%.2f",
    *       ),
        },
    )

    # *------------------------
    # Sav* Changes
    # -------------------*-----
    if st.button(
        "S*ve Changes",
        type="primary*
    ):

        try:

           *existing_ids = {
                r*w["goal_id"]
                for r*w in goals_rows
            }

   *        for _, row in edited_df.it*rrows():

                record =*row.to_dict()

                goa*_id = record.get("goal_id")

     *          goal_type = record.get("*oal_type")

                if not*goal_type:
                    con*inue

                # Apply cons*raint rules

                if go*l_type in DIVE_GOAL_TYPES:

      *             record["score_goal"] * None

                    if not *ecord.get("dive_number"):
        *               continue

         *      elif goal_type in SCORE_GOAL*TYPES:

                    record["dive_number"] = None

                    if pd.isna(record.get("score_goal")):
                        continue

                # UPDATE
                if (
                    pd.notna(goal_id)
                    and goal_id in existing_ids
                ):

                    record.pop(
                        "goal_id",
                        None
                    )

                    record.pop(
                        "date_added",
                        None
                    )

                    (
                        supabase.table("goals")
                        .update(record)
                        .eq("goal_id", int(goal_id))
                        .execute()
                    )

                # INSERT
                else:

                    insert_record = {
                        "diver": record["diver"],
                        "goal_type": record["goal_type"],
                        "dive_number": record.get(
                            "dive_number"
                        ),
                        "score_goal": record.get(
                            "score_goal"
                        ),
                    }

                    (
                        supabase.table("goals")
                        .insert(insert_record)
                        .execute()
                    )

            st.success(
                "Goals updated successfully."
            )

            st.rerun()

        except Exception as ex:
            st.error(
                f"Update failed: {ex}"
            )

    st.divider()

    st.subheader("Delete Goal")

    goal_options = {}

    for g in filtered_goals:

        goal_options[
            f"{g['goal_id']} | {g['goal_type']} | {g['date_added']}"
        ] = g["goal_id"]

    if goal_options:

        selected_goal = st.selectbox(
            "Select Goal",
            list(goal_options.keys())
        )

        confirm_delete = st.checkbox(
            "I understand this action cannot be undone"
        )

        if st.button("Delete Goal"):

            if not confirm_delete:

                st.error(
                    "Confirmation required."
                )

            else:

                goal_id = goal_options[
                    selected_goal
                ]

                (
                    supabase.table("goals")
                    .delete()
                    .eq("goal_id", goal_id)
                    .execute()
                )

                st.success(
                    "Goal deleted successfully."
                )

                st.rerun()