import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Diving Database",
    page_icon="🏊",
    layout="wide"
)

# =====================================================
# SUPABASE
# =====================================================

supabase = create_client(
    st.secrets["supabase"]["url"],
    st.secrets["supabase"]["key"]
)

# =====================================================
# HELPERS
# =====================================================

@st.cache_data(ttl=60)
def get_divers():
    response = (
        supabase.table("divers")
        .select("diver")
        .order("diver")
        .execute()
    )
    return response.data


@st.cache_data(ttl=60)
def get_meets():
    response = (
        supabase.table("meets")
        .select("meet")
        .order("meet")
        .execute()
    )
    return response.data


@st.cache_data(ttl=60)
def get_dives():
    response = (
        supabase.table("dives")
        .select("dive_number, dd")
        .order("dive_number")
        .execute()
    )
    return response.data


def clear_cache():
    st.cache_data.clear()


def build_dd_lookup():
    dives = get_dives()

    return {
        row["dive_number"]: float(row["dd"])
        for row in dives
    }


# =====================================================
# SIDEBAR
# =====================================================

page = st.sidebar.radio(
    "Navigation",
    [
        "Add Diver",
        "Add Meet",
        "Add Results",
        "Top Scores"
    ]
)

# =====================================================
# ADD DIVER
# =====================================================

if page == "Add Diver":

    st.title("Add Diver")

    with st.form("add_diver"):

        last_name = st.text_input(
            "Last Name",
            max_chars=50
        )

        first_name = st.text_input(
            "First Name",
            max_chars=50
        )

        season = st.selectbox(
            "Season",
            [
                "Boys",
                "Girls"
            ]
        )

        submit = st.form_submit_button(
            "Add Diver",
            use_container_width=True
        )

    if submit:

        try:

            if not last_name.strip():
                raise ValueError("Last Name is required.")

            if not first_name.strip():
                raise ValueError("First Name is required.")

            supabase.table("divers").insert(
                {
                    "last_name": last_name.strip(),
                    "first_name": first_name.strip(),
                    "season": season
                }
            ).execute()

            clear_cache()

            st.success(
                f"Successfully added {first_name.strip()} {last_name.strip()}."
            )

        except Exception as e:
            st.error(f"Failed to add diver: {e}")

# =====================================================
# ADD MEET
# =====================================================

elif page == "Add Meet":

    st.title("Add Meet")

    with st.form("add_meet"):

        meet_date = st.date_input(
            "Date",
            value=date.today()
        )

        season = st.selectbox(
            "Season",
            [
                "Boys",
                "Girls"
            ]
        )

        opponent = st.text_input(
            "Opponent"
        )

        meet_type = st.selectbox(
            "Type",
            [
                "Dual",
                "Invite",
                "Championship"
            ]
        )

        submit = st.form_submit_button(
            "Add Meet",
            use_container_width=True
        )

    if submit:

        try:

            opponent_clean = opponent.strip()

            if not opponent_clean:
                raise ValueError(
                    "Opponent is required."
                )

            if " " in opponent_clean:
                raise ValueError(
                    "Opponent cannot contain spaces due to database rules."
                )

            supabase.table("meets").insert(
                {
                    "date": str(meet_date),
                    "season": season,
                    "opponent": opponent_clean,
                    "type": meet_type
                }
            ).execute()

            clear_cache()

            st.success(
                f"Successfully added meet versus {opponent_clean}."
            )

        except Exception as e:
            st.error(f"Failed to add meet: {e}")

# =====================================================
# ADD RESULTS
# =====================================================

elif page == "Add Results":

    st.title("Add Results")

    try:

        meets = [
            m["meet"]
            for m in get_meets()
        ]

        divers = [
            d["diver"]
            for d in get_divers()
        ]

        dives = get_dives()

        dive_numbers = [
            d["dive_number"]
            for d in dives
        ]

        dd_lookup = build_dd_lookup()

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
                "Type": ["V"] * dive_count,
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

# =====================================================
# TOP SCORES
# =====================================================

elif page == "Top Scores":

    from io import BytesIO
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
    )
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet

    st.title("🏆 Top Scores")

    @st.cache_data(ttl=60)
    def get_results_summary():

        response = (
            supabase.table("results")
            .select("meet,diver,score")
            .execute()
        )

        df = pd.DataFrame(response.data)

        if df.empty:
            return df

        summary = (
            df.groupby(["meet", "diver"], as_index=False)
            .agg(
                total_score=("score", "sum"),
                dives=("score", "size")
            )
        )

        summary["format"] = summary["dives"].apply(
            lambda x: "6-Dive" if x == 6 else (
                "11-Dive" if x == 11 else None
            )
        )

        score_6 = (
            summary[summary["format"] == "6-Dive"]
            [["meet", "diver", "total_score"]]
            .rename(columns={"total_score": "6-Dive Score"})
        )

        score_11 = (
            summary[summary["format"] == "11-Dive"]
            [["meet", "diver", "total_score"]]
            .rename(columns={"total_score": "11-Dive Score"})
        )

        return score_6.merge(
            score_11,
            on=["meet", "diver"],
            how="outer"
        )

    def build_pdf(df):

        buffer = BytesIO()

        doc = SimpleDocTemplate(buffer)

        styles = getSampleStyleSheet()

        elements = [
            Paragraph("Top Scores Report", styles["Title"]),
            Spacer(1, 12)
        ]

        table = Table(
            [df.columns.tolist()] + df.values.tolist()
        )

        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.navy),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ])
        )

        elements.append(table)

        doc.build(elements)

        buffer.seek(0)

        return buffer

    scores = get_results_summary()

    if scores.empty:
        st.info("No results found.")
        st.stop()

    scores["Year"] = scores["meet"].str[:4]

    scores["Season"] = scores["meet"].str[5].map({
        "G": "Girls",
        "B": "Boys"
    })

    years = sorted(
        scores["Year"].dropna().unique(),
        reverse=True
    )

    st.markdown("### 🎯 Required Filters")

    with st.container(border=True):

        col1, col2, col3 = st.columns(3)

        with col1:
            year = st.selectbox(
                "Year",
                years
            )

        with col2:
            season = st.selectbox(
                "Season",
                ["Girls", "Boys"],
                index=0
            )

        with col3:
            score_type = st.selectbox(
                "Type",
                ["Top Scores", "All Scores"]
            )

    with st.expander("⚙️ Optional Filters", expanded=False):

        col1, col2, col3 = st.columns(3)

        with col1:
            meet = st.selectbox(
                "Meet",
                ["All"] + sorted(
                    scores["meet"].dropna().unique().tolist()
                )
            )

        with col2:
            diver = st.selectbox(
                "Diver",
                ["All"] + sorted(
                    scores["diver"].dropna().unique().tolist()
                )
            )

        with col3:
            format_filter = st.selectbox(
                "Format",
                ["All", "6-Dive", "11-Dive"]
            )

    df = scores.copy()

    df = df[
        (df["Year"] == year) &
        (df["Season"] == season)
    ]

    if meet != "All":
        df = df[df["meet"] == meet]

    if diver != "All":
        df = df[df["diver"] == diver]

    if format_filter == "6-Dive":
        df = df[df["6-Dive Score"].notna()]

    elif format_filter == "11-Dive":
        df = df[df["11-Dive Score"].notna()]

    if score_type == "Top Scores":

        if format_filter == "6-Dive":

            idx = (
                df.groupby("diver")["6-Dive Score"]
                .idxmax()
            )

            df = df.loc[idx]

        elif format_filter == "11-Dive":

            idx = (
                df.groupby("diver")["11-Dive Score"]
                .idxmax()
            )

            df = df.loc[idx]

        else:

            df["Best Score"] = df[
                ["6-Dive Score", "11-Dive Score"]
            ].max(axis=1)

            idx = (
                df.groupby("diver")["Best Score"]
                .idxmax()
            )

            df = df.loc[idx]

    if format_filter == "6-Dive":

        display = (
            df[
                ["diver", "meet", "6-Dive Score"]
            ]
            .rename(columns={
                "diver": "Diver",
                "meet": "Meet",
                "6-Dive Score": "Score"
            })
        )

        rank_col = "Score"

    elif format_filter == "11-Dive":

        display = (
            df[
                ["diver", "meet", "11-Dive Score"]
            ]
            .rename(columns={
                "diver": "Diver",
                "meet": "Meet",
                "11-Dive Score": "Score"
            })
        )

        rank_col = "Score"

    else:

        display = (
            df[
                [
                    "diver",
                    "meet",
                    "6-Dive Score",
                    "11-Dive Score"
                ]
            ]
            .rename(columns={
                "diver": "Diver",
                "meet": "Meet"
            })
        )

        display["Ranking Score"] = display[
            ["6-Dive Score", "11-Dive Score"]
        ].max(axis=1)

        rank_col = "Ranking Score"

    display = (
        display
        .sort_values(rank_col, ascending=False)
        .reset_index(drop=True)
    )

    display.insert(
        0,
        "Rank",
        range(1, len(display) + 1)
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Divers",
        display["Diver"].nunique()
    )

    c2.metric(
        "Rows",
        len(display)
    )

    c3.metric(
        "Highest Score",
        f"{display[rank_col].max():.2f}"
    )

    export_df = display.copy()

    if "Ranking Score" in export_df.columns:
        export_df = export_df.drop(
            columns=["Ranking Score"]
        )

    col1, col2 = st.columns(2)

    with col1:

        st.download_button(
            "📥 Export CSV",
            export_df.to_csv(index=False),
            file_name="top_scores.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col2:

        pdf_buffer = build_pdf(export_df)

        st.download_button(
            "📄 Export PDF",
            pdf_buffer,
            file_name="top_scores.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    st.dataframe(
        export_df,
        use_container_width=True,
        hide_index=True
    )