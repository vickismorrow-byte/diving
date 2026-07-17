import pandas as pd
import streamlit as st
import plotly.express as px


def extract_year(meet_name):
    try:
        return str(meet_name)[:4]
    except Exception:
        return None


def build_score_progression_dataframe(supabase):
    results = (
        supabase
        .table("results")
        .select("*")
        .execute()
        .data
    )

    meets = (
        supabase
        .table("meets")
        .select("*")
        .execute()
        .data
    )

    results_df = pd.DataFrame(results)
    meets_df = pd.DataFrame(meets)

    if results_df.empty:
        return pd.DataFrame()

    if meets_df.empty:
        return pd.DataFrame()

    df = results_df.merge(
        meets_df[["meet", "date"]],
        on="meet",
        how="left"
    )

    df["date"] = pd.to_datetime(df["date"])
    df["Year"] = df["meet"].apply(extract_year)

    try:
        season_code = df["meet"].str.split("_").str[1]

        df["Season"] = season_code.map({
            "G": "Girls",
            "B": "Boys"
        })
    except Exception:
        df["Season"] = None

    return df


def build_6_dive_scores(df):
    meet_scores = (
        df.groupby(
            ["diver", "meet", "date"],
            as_index=False
        )
        .agg(
            Score=("score", "sum"),
            DiveCount=("score", "count")
        )
    )

    meet_scores = meet_scores[
        meet_scores["DiveCount"] == 6
    ]

    return meet_scores.rename(
        columns={
            "diver": "Diver",
            "meet": "Meet",
            "date": "Date"
        }
    )


def build_11_dive_scores(df):
    meet_scores = (
        df.groupby(
            ["diver", "meet", "date"],
            as_index=False
        )
        .agg(
            Score=("score", "sum"),
            DiveCount=("score", "count")
        )
    )

    meet_scores = meet_scores[
        meet_scores["DiveCount"] == 11
    ]

    return meet_scores.rename(
        columns={
            "diver": "Diver",
            "meet": "Meet",
            "date": "Date"
        }
    )


def build_specific_dive_scores(df, dive_number):
    dive_df = df[
        df["dive_number"] == dive_number
    ].copy()

    return dive_df.rename(
        columns={
            "diver": "Diver",
            "meet": "Meet",
            "date": "Date",
            "score": "Score"
        }
    )[
        ["Diver", "Meet", "Date", "Score"]
    ]


def render_score_progression_page(supabase):

    st.header("Score Progression")

    df = build_score_progression_dataframe(supabase)

    if df.empty:
        st.warning("No data found.")
        return

    # --------------------------------------------------
    # REQUIRED FILTERS
    # --------------------------------------------------

    season = st.selectbox(
        "Season",
        ["Girls", "Boys"]
    )

    format_type = st.selectbox(
        "Format",
        [
            "6-Dive",
            "11-Dive",
            "Specific Dive"
        ]
    )

    # --------------------------------------------------
    # FILTER DATA BY SEASON FIRST
    # --------------------------------------------------

    filtered = df[
        df["Season"] == season
    ].copy()

    # --------------------------------------------------
    # OPTIONAL YEAR FILTER
    # --------------------------------------------------

    years = sorted(
        filtered["Year"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_year = st.selectbox(
        "Year (Optional)",
        ["All"] + years
    )

    if selected_year != "All":
        filtered = filtered[
            filtered["Year"] == selected_year
        ]

    # --------------------------------------------------
    # OPTIONAL DATE FILTER
    # --------------------------------------------------

    if not filtered.empty:

        min_date = filtered["date"].min().date()
        max_date = filtered["date"].max().date()

        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input(
                "Start Date",
                value=min_date,
                min_value=min_date,
                max_value=max_date
            )

        with col2:
            end_date = st.date_input(
                "End Date",
                value=max_date,
                min_value=min_date,
                max_value=max_date
            )

        filtered = filtered[
            (filtered["date"].dt.date >= start_date)
            &
            (filtered["date"].dt.date <= end_date)
        ]

    # --------------------------------------------------
    # DIVE NUMBER FILTER
    # --------------------------------------------------

    dive_numbers = sorted(
        filtered["dive_number"]
        .dropna()
        .unique()
        .tolist()
    )

    if format_type == "Specific Dive":

        dive_number = st.selectbox(
            "Dive Number",
            dive_numbers
        )

    else:

        st.selectbox(
            "Dive Number",
            ["Disabled"],
            disabled=True
        )

        dive_number = None

    # --------------------------------------------------
    # DIVER FILTER
    # --------------------------------------------------

    available_divers = sorted(
        filtered["diver"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_divers = st.multiselect(
        "Diver",
        available_divers
    )

    if not selected_divers:
        st.info("Select at least one diver.")
        return

    filtered = filtered[
        filtered["diver"].isin(selected_divers)
    ]

    if filtered.empty:
        st.warning("No results found.")
        return

    # --------------------------------------------------
    # BUILD CHART DATA
    # --------------------------------------------------

    if format_type == "6-Dive":

        chart_df = build_6_dive_scores(filtered)

    elif format_type == "11-Dive":

        chart_df = build_11_dive_scores(filtered)

    else:

        if not dive_number:
            st.warning("Dive Number is required.")
            return

        chart_df = build_specific_dive_scores(
            filtered,
            dive_number
        )

    if chart_df.empty:
        st.warning("No matching results found.")
        return

    chart_df = chart_df.sort_values(
        ["Diver", "Date"]
    )

    chart_df["Label"] = chart_df["Score"].round(2)

    # --------------------------------------------------
    # CHART
    # --------------------------------------------------

    fig = px.line(
        chart_df,
        x="Date",
        y="Score",
        color="Diver",
        markers=True,
        text="Label"
    )

    fig.update_traces(
        textposition="top center",
        customdata=chart_df[["Meet"]]
    )

    fig.update_traces(
        hovertemplate=
        "<b>%{fullData.name}</b><br>"
        "Date: %{x|%Y-%m-%d}<br>"
        "Meet: %{customdata[0]}<br>"
        "Score: %{y:.2f}"
        "<extra></extra>"
    )

    fig.update_layout(
        height=700,
        xaxis_title="Date",
        yaxis_title="Score",
        hovermode="closest",
        legend_title_text="Diver"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # --------------------------------------------------
    # OPTIONAL DATA TABLE
    # --------------------------------------------------

    st.markdown("---")

    st.subheader("Underlying Data")

    display_df = chart_df[
        ["Diver", "Date", "Meet", "Score"]
    ].sort_values(
        ["Diver", "Date"]
    )

    st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True
    )