import streamlit as st
import pandas as pd

CATEGORIES = [
    "Forward",
    "Backward",
    "Reverse",
    "Inward",
    "Twister",
    "11th Dive",
]


def render_edit_lists_page(supabase):
    st.title("View/Edit Current Lists")

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
        .select("dive_number, dd")
        .order("dive_number")
        .execute()
        .data
    )

    lists_rows = (
        supabase.table("lists")
        .select("*")
        .execute()
        .data
    )

    dive_numbers = [
        row["dive_number"]
        for row in dives_rows
    ]

    dd_lookup = {
        row["dive_number"]: row["dd"]
        for row in dives_rows
    }

    # -------------------------
    # Filters
    # ------------------------

    col1, col2 = st.columns(2)

    with col1:
       season_filter = st.selectbox(
            ["Season", "All", "Boys", "Girls"]
        )
    filtered_divers = divers_rows.copy()

    if season_filter != "All":
        filtered_divers = [
            d
            for d in filtered_divers
            if d["season"] == season_filter
        ]

    diver_list = sorted(
        {d["diver"]
            for d in filtered_divers
            if d.get("diver")
        }
    )

    with col2:
        selected_diver = st.selectbox(
            "Diver",
            ["Select Diver"]+ diver_list
        )

    if selected_diver == "Select Diver":
       return

    # -------------------------
    # Build Current List
    # -------------------------

    diver_lists = [
        row
        for row in lists_rows
        if row["diver"] == selected_diver
    ]

    rows = []

    for category in CATEGORIES:

        voluntary_dive = None
        voluntary_dd = None

        optional_dive = None
        optional_dd = None

        if category != "11th Dive":

            voluntary_matches = [
                row
                for row in diver_lists
                if row["category"] == category
                and row["type"] == "V"
            ]

            if voluntary_matches:
                newest = sorted(
                    voluntary_matches,
                    key=lambda x: str(x["date_added"]),
                    reverse=True,
                )[0]

                voluntary_dive = newest["dive_number"]
                voluntary_dd = dd_lookup.get(voluntary_dive)

        optional_matches = [
            row
            for row in diver_lists
            if row["category"] == category
            and row["type"] == "O"
        ]

        if optional_matches:
            newest = sorted(
                optional_matches,
                key=lambda x: str(x["date_added"]),
                reverse=True,
            )[0]

            optional_dive = newest["dive_number"]
            optional_dd = dd_lookup.get(optional_dive)

        rows.append(
             {
                "Category": category,
                "Voluntary": voluntary_dive,
                "Voluntary DD": voluntary_dd,
                "": "",
                "Optional": optional_dive,
                "Optional DD": optional_dd,
            }
        )

    df = pd.DataFrame(rows)

    st.subheader("Current List")

    edited_df = st.data_editor(
        df,
        key="lists_editor",
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        disabled=[
            "Category",
            "Voluntary DD",
            "",
            "Optional DD",
        ],
        column_config={
            "Voluntary": st.column_config.SelectboxColumn("Voluntary", options=dive_numbers, required=False, ),
            "Optional": st.column_config.SelectboxColumn("Optional", options=dive_numbers, required=False, ),
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

            editor_state = st.session_state.get(
                "lists_editor",
                {}
            )

            edited_rows = editor_state.get(
                "edited_rows",
                {}
            )

            if not edited_rows:
                st.info("No changes detected.")
                return

            inserts_made = 0

            for row_index in edited_rows.keys():

                original_row = df.iloc[row_index]
                edited_row = edited_df.iloc[row_index]

                category = edited_row["Category"]

                # -------------------------
                # Voluntary
                # -------------------------

                if category != "11th Dive":

                    if (
                        original_row["Voluntary"]
                        != edited_row["Voluntary"]
                    ):

                        if pd.notna(
                            edited_row["Voluntary"]
                        ):

                            (
                                supabase.table("lists")
                                .insert(
                                    {
                                        "diver": selected_diver,
                                        "category": category,
                                        "type": "V",
                                        "dive_number": edited_row["Voluntary"],
                                    }
                                )
                                .execute()
                            )

                            inserts_made += 1

                # -------------------------
                # Optional
                # -------------------------

                if (
                    original_row["Optional"]
                    != edited_row["Optional"]
                ):

                    if pd.notna(
                        edited_row["Optional"]
                    ):

                        (
                            supabase.table("lists")
                            .insert(
                                {
                                    "diver": selected_diver,
                                    "category": category,
                                    "type": "O",
                                    "dive_number": edited_row["Optional"],
                                }
                            )
                            .execute()
                        )

                        inserts_made += 1

            st.success(
                f"{inserts_made} list record(s) inserted successfully."
            )

            st.rerun()

        except Exception as ex:
            st.error(
                f"Save failed: {ex}"
            )