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

def dive_group(dive_number):
    # First digit identifies the group:
    # 1=Forward, 2=Back, 3=Reverse, 4=Inward, 5=Twisting
    return str(dive_number)[0]

def dive_base_number(dive_number):
    # 101A and 101B count as the same dive number
    return str(dive_number)[:-1]


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
            meets,
            key="selected_meet"
        )

        selected_diver = st.selectbox(
            "Diver",
            divers,
            index=None,
            placeholder="Select Diver",
            key="selected_diver"
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
            },
            key=f"results_editor_{st.session_state.get('results_editor_counter', 0)}"
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

            # Skip all validation if 999D exists
            all_dives = [str(r["dive_number"]) for r in rows_to_insert]

            if "999D" not in all_dives:

                if dive_count == 6:
                    voluntary = [r for r in rows_to_insert if r["type"] == "V"]
                    optional = [r for r in rows_to_insert if r["type"] == "O"]

                    if len(voluntary) != 1:
                        raise ValueError(
                            "6-dive meet requires exactly 1 voluntary dive."
                        )

                    if len(optional) != 5:
                        raise ValueError(
                            "6-dive meet requires exactly 5 optional dives."
                        )

                    categories = {
                        dive_group(r["dive_number"])
                        for r in rows_to_insert
                    }

                    if len(categories) < 4:
                        raise ValueError(
                            "6-dive meet must contain dives from at least 4 categories."
                        )

                elif dive_count == 11:

                    voluntary = [r for r in rows_to_insert if r["type"] == "V"]
                    optional = [r for r in rows_to_insert if r["type"] == "O"]

                    if len(voluntary) != 5:
                        raise ValueError(
                            "11-dive meet requires 5 voluntary dives."
                        )

                    if len(optional) != 6:
                        raise ValueError(
                            "11-dive meet requires 6 optional dives."
                        )

                    # Rule 2
                    voluntary_dd = sum(
                        dd_lookup[r["dive_number"]]
                        for r in voluntary
                    )

                    if voluntary_dd > 9.0:
                        raise ValueError(
                            "Voluntary DD total must be 9.0 or less."
                        )

                    # Rule 3
                    vol_groups = {
                        dive_group(r["dive_number"])
                        for r in voluntary
                    }

                    if len(vol_groups) != 5:
                        raise ValueError(
                            "The 5 voluntary dives must be from all 5 dive groups."
                        )

                    # Rule 4
                    opt_groups = [
                        dive_group(r["dive_number"])
                        for r in optional
                    ]

                    if set(opt_groups) != {"1", "2", "3", "4", "5"}:
                        raise ValueError(
                            "Optional dives must include all 5 dive groups."
                        )

                    # Rule 6
                    first8 = rows_to_insert[:8]

                    first8_groups = {
                        dive_group(r["dive_number"])
                        for r in first8
                    }

                    if len(first8_groups) != 5:
                        raise ValueError(
                            "All 5 dive groups must be represented in the first 8 dives."
                        )

                    # Rule 7
                    first8_optional = [
                        r for r in first8
                        if r["type"] == "O"
                    ]

                    first8_optional_groups = [
                        dive_group(r["dive_number"])
                        for r in first8_optional
                    ]

                    if len(first8_optional_groups) != len(set(first8_optional_groups)):
                        raise ValueError(
                            "Optional dives in the first 8 rounds must all be from different groups."
                        )

                    # Rule 8
                    base_numbers = [
                        dive_base_number(r["dive_number"])
                        for r in rows_to_insert
                    ]

                    if len(base_numbers) != len(set(base_numbers)):
                        raise ValueError(
                            "All 11 dive numbers must be different."
                        )


            supabase.table("results").insert(
                rows_to_insert
            ).execute()

            st.success(
              f"Successfully inserted {len(rows_to_insert)} result records."
            )

            st.session_state.pop("selected_diver", None)
            st.session_state["results_editor_counter"] = (st.session_state.get("results_editor_counter", 0) + 1)

            st.rerun()

    except Exception as e:
        st.error(f"Unable to load results page: {e}")