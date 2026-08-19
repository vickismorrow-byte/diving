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


def render_view_lists_page(supabase):
    st.title("View Current Lists")

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

    dives_rows = (
        supabase.table("dives")
        .select("dive_number, dd")
        .execute()
        .data
    )

    dd_lookup = {
        row["dive_number"]: row["dd"]
        for row in dives_rows
    }

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
            ["Select Diver"] + diver_list
        )

    if selected_diver == "Select Diver":
        return

    # -------------------------
    # Load Lists
    # -------------------------

    lists_rows = (
        supabase.table("lists")
        .select("*")
        .eq("diver", selected_diver)
        .order("date_added", desc=True)
        .execute()
        .data
    )

    rows = []

    for category in CATEGORIES:

        voluntary_dive = ""
        voluntary_dd = ""

        optional_dive = ""
        optional_dd = ""

        if category != "11th Dive":

            voluntary_record = next(
                (
                    row
                    for row in lists_rows
                    if row["category"] == category
                    and row["type"] == "V"
                ),
                None,
            )

            if voluntary_record:
                voluntary_dive = voluntary_record["dive_number"]
                voluntary_dd = dd_lookup.get(
                    voluntary_dive,
                    ""
                )

        optional_record = next(
            (
                row
                for row in lists_rows
                if row["category"] == category
                and row["type"] == "O"
            ),
            None,
        )

        if optional_record:
            optional_dive = optional_record["dive_number"]
            optional_dd = dd_lookup.get(
                optional_dive,
                ""
            )

        if category == "11th Dive":
            voluntary_dive = "XXXX"
            voluntary_dd = "XXX"

        if voluntary_dd is None or voluntary_dd == "":
            voluntary_dd_display = ""
        elif voluntary_dd == "XXX":
            voluntary_dd_display = "XXX"
        else:
            voluntary_dd_display = f"{float(voluntary_dd):.1f}"

        if optional_dd is None or optional_dd == "":
            optional_dd_display = ""
        elif optional_dd == "XXX":
            optional_dd_display = "XXX"
        else:
            optional_dd_display = f"{float(optional_dd):.1f}"
            
        rows.append(
             {
                "Category": category,
                "Voluntary": voluntary_dive,
                "Voluntary DD": voluntary_dd_display,
                "Optional": optional_dive,
                "Optional DD": optional_dd_display,
            }
        )

    display_df = pd.DataFrame(rows)

    st.subheader(f"{selected_diver} Current List")

    styled_df = (
            display_df.style
            .set_properties(
                subset=["Category"],
                **{"font-weight": "bold"}
            )
        )

    st.dataframe(
        styled_df,
        hide_index=True,
        use_container_width=True,
    )