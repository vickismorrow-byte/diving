import streamlit as st
import pandas as pd


def render_edit_results_page(supabase):
    st.title("View & Edit Diver Results")

    # ---------------------------------
    # Load data for dynamic filters
    # ---------------------------------
    results_rows = (
        supabase.table("results")
        .select("entryid, diver, meet")
        .execute()
        .data
    )

    divers_rows = (
        supabase.table("divers")
        .select("diver, season")
        .execute()
        .data
    )

    meets_rows = (
        supabase.table("meets")
        .select("meet, season, date")
        .execute()
        .data
    )

    diver_season = {
        d["diver"]: d["season"]
        for d in divers_rows
    }

    meet_lookup = {
        m["meet"]: m
        for m in meets_rows
    }

    # ---------------------------------
    # Dynamic Filters
    # ---------------------------------
    col1, col2 = st.columns(2)

    with col1:
        season_filter = st.selectbox(
            "Season",
            ["All", "Boys", "Girls"],
        )

    filtered_rows = results_rows.copy()

    # Filter by Boys/Girls
    if season_filter != "All":
        filtered_rows = [
            r
            for r in filtered_rows
            if diver_season.get(r["diver"]) == season_filter
        ]

    # Build available years after season filter
    years = sorted(
        {
            r["meet"][:4]
            for r in filtered_rows
            if r.get("meet") and len(r["meet"]) >= 4
        },
        reverse=True,
    )

    with col2:
        year_filter = st.selectbox(
            "Year",
            ["All"] + years,
        )

    # Filter by year
    if year_filter != "All":
        filtered_rows = [
            r
            for r in filtered_rows
            if r.get("meet", "").startswith(year_filter)
        ]

    # ---------------------------------
    # Dynamic Diver List
    # ---------------------------------
    available_divers = sorted(
        {
            r["diver"]
            for r in filtered_rows
            if r.get("diver")
        }
    )

    selected_diver = st.selectbox(
        "Diver *",
        ["Select Diver"] + available_divers,
    )

    if selected_diver == "Select Diver":
        return

    # ---------------------------------
    # Dynamic Meet List
    # ---------------------------------
    available_meets = sorted(
        {
            r["meet"]
            for r in filtered_rows
            if r["diver"] == selected_diver
        }
    )

    selected_meet = st.selectbox(
        "Meet *",
        ["Select Meet"] + available_meets,
    )

    if selected_meet == "Select Meet":
        return

    # ---------------------------------
    # Load Results
    # ---------------------------------
    results_resp = (
        supabase.table("results")
        .select("*")
        .eq("diver", selected_diver)
        .eq("meet", selected_meet)
        .execute()
    )

    if not results_resp.data:
        st.warning("No results found.")
        return

    df = pd.DataFrame(results_resp.data)

    st.subheader("Current Results")

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="fixed",
        key="edit_results_table",
    )

    # ---------------------------------
    # Save Changes
    # ---------------------------------
    if st.button("Save Changes", type="primary"):
        try:
            for _, row in edited_df.iterrows():
                record = row.to_dict()

                entryid = record.pop("entryid")

                (
                    supabase.table("results")
                    .update(record)
                    .eq("entryid", entryid)
                    .execute()
                )

            st.success("Results updated successfully.")

        except Exception as ex:
            st.error(f"Update failed: {ex}")