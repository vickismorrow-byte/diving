import streamlit as st
import pandas as pd


def render_edit_results_page(supabase):
    st.title("View & Edit Diver Results")

    # ---------------------------------
    # Load dropdown values
    # ---------------------------------
    divers_resp = (
        supabase.table("results")
        .select("diver")
        .order("diver")
        .execute()
    )

    divers = sorted(
        list(
            {
                row["diver"]
                for row in divers_resp.data
                if row.get("diver")
            }
        )
    )

    # ---------------------------------
    # Optional Filters
    # ---------------------------------
    col1, col2 = st.columns(2)

    with col1:
        year_filter = st.selectbox(
            "Year (Optional)",
            ["All"] + sorted(
                list(
                    {
                        r["meet"][:4]
                        for r in divers_resp.data
                        if r.get("meet") and len(r["meet"]) >= 4
                    }
                ),
                reverse=True,
            ),
        )

    with col2:
        season_filter = st.selectbox(
            "Season (Optional)",
            ["All", "Girls", "Boys"],
        )

    # ---------------------------------
    # Required Diver Filter
    # ---------------------------------
    selected_diver = st.selectbox(
        "Diver *",
        ["Select Diver"] + divers,
    )

    if selected_diver == "Select Diver":
        return

    meet_query = (
        supabase.table("results")
        .select("*")
        .eq("diver", selected_diver)
    )

    meet_rows = meet_query.execute().data

    if year_filter != "All":
        meet_rows = [
            r
            for r in meet_rows
            if r.get("meet", "").startswith(year_filter)
        ]

    if season_filter != "All":
        season_code = "G" if season_filter == "Girls" else "B"

        meet_rows = [
            r
            for r in meet_rows
            if f"_{season_code}_" in r.get("meet", "")
        ]

    meets = sorted(
        list(
            {
                r["meet"]
                for r in meet_rows
                if r.get("meet")
            }
        )
    )

    # ---------------------------------
    # Required Meet Filter
    # ---------------------------------
    selected_meet = st.selectbox(
        "Meet *",
        ["Select Meet"] + meets,
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

                result_id = record.pop("id")

                (
                    supabase.table("results")
                    .update(record)
                    .eq("id", result_id)
                    .execute()
                )

            st.success("Results updated successfully.")

        except Exception as ex:
            st.error(f"Update failed: {ex}")