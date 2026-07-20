import io
import re
import pandas as pd
import streamlit as st
from datetime import date

@st.cache_data(ttl=60)
def get_divers(_supabase):
    response = (
        _supabase.table("divers")
        .select("diver")
        .order("diver")
        .execute()
    )
    return response.data


@st.cache_data(ttl=60)
def get_meets(_supabase):
    response = (
        _supabase.table("meets")
        .select("meet")
        .order("meet")
        .execute()
    )
    return response.data


@st.cache_data(ttl=60)
def get_dives(_supabase):
    response = (
        _supabase.table("dives")
        .select("dive_number, dd")
        .order("dive_number")
        .execute()
    )
    return response.data


def clear_cache():
    st.cache_data.clear()


def build_dd_lookup(supabase):
    dives = get_dives(supabase)

    return {
        row["dive_number"]: float(row["dd"])
        for row in dives
    }


def render_add_results_page(supabase):
    st.title("Add Results")

    try:

        meets = [
            m["meet"]
            for m in get_meets(supabase)
        ]

        divers = [
            d["diver"]
            for d in get_divers(supabase)
        ]

        dives = get_dives(supabase)

        dive_numbers = [
            d["dive_number"]
            for d in dives
        ]

        dd_lookup = build_dd_lookup(supabase)

        if not meets:
            st.warning(
                "No meets found. Add a meet first."
            )
            st.stop()

        if not divers:
            st.warning(
                "No divers found. Add a diver first."
            )
            st.stop()

        selected_meet = st.selectbox(
            "Meet",
            meets
        )

        selected_diver = st.selectbox(
            "Diver",
            divers
        )

        dive_count = st.radio(
            "Number of Dives",
            [6, 11],
            horizontal=True
        )

        default_df = pd.DataFrame(
            {
                "Dive Number": [None] * dive_count,
                "Type": ["O"] * dive_count,
                "Award": [None] * dive_count,
                "Score": [None] * dive_count
            }
        )

        edited_df = st.data_editor(
            default_df,
            hide_index=True,
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "Dive Number": st.column_config.SelectboxColumn(
                    "Dive Number",
                    options=dive_numbers,
                    required=True
                ),
                "Type": st.column_config.SelectboxColumn(
                    "Type",
                    options=["V", "O"],
                    required=True
                ),
                "Award": st.column_config.NumberColumn(
                    "Award",
                    min_value=0.00,
                    max_value=999.99,
                    step=0.01,
                    format="%.2f"
                ),
                "Score": st.column_config.NumberColumn(
                    "Score",
                    min_value=0.00,
                    max_value=999.99,
                    step=0.01,
                    format="%.2f"
                )
            }
        )

        if st.button(
            "Submit Results",
            type="primary",
            use_container_width=True
        ):

            rows_to_insert = []

            for idx, row in edited_df.iterrows():

                dive_number = row["Dive Number"]
                dive_type = row["Type"]

                award = row["Award"]
                score = row["Score"]

                if pd.isna(dive_number):
                    raise ValueError(
                        f"Row {idx + 1}: Dive Number required."
                    )

                award_exists = pd.notna(award)
                score_exists = pd.notna(score)

                if award_exists and score_exists:
                    raise ValueError(
                        f"Row {idx + 1}: Enter Award OR Score, not both."
                    )

                if not award_exists and not score_exists:
                    raise ValueError(
                        f"Row {idx + 1}: Enter Award OR Score."
                    )

                if score_exists:

                    dd = dd_lookup.get(dive_number)

                    if not dd:
                        raise ValueError(
                            f"Row {idx + 1}: No DD found for dive."
                        )

                    award = round(
                        float(score) / float(dd),
                        2
                    )

                award = round(float(award), 2)

                rows_to_insert.append(
                    {
                        "meet": selected_meet,
                        "diver": selected_diver,
                        "dive_number": dive_number,
                        "type": dive_type,

                        # ALWAYS STORE AWARD
                        "award": award,

                        # placeholder; trigger recalculates
                        "score": 0
                    }
                )

            supabase.table("results").insert(
                rows_to_insert
            ).execute()

            st.success(
                f"Successfully inserted {len(rows_to_insert)} result records."
            )

    except Exception as e:
        st.error(f"Unable to load results page: {e}")