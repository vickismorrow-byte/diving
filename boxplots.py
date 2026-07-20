import pandas as pd
import streamlit as st
import plotly.express as px


def extract_year(meet_name):
    try:
        return str(meet_name)[:4]
    except Exception:
        return None


def build_dive_distribution_dataframe(supabase):
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

    if not results or not meets:
        return pd.DataFrame()

    results_df = pd.DataFrame(results)
    meets_df = pd.DataFrame(meets)

    if results_df.empty or meets_df.empty:
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


def build_stats_dataframe(df):
    stats = []

    for dive, group in df.groupby("dive_number"):
        min_idx = group["score"].idxmin()
        max_idx = group["score"].idxmax()

        stats.append({
            "dive_number": dive,
            "Count": len(group),
            "Min": group["score"].min(),
            "Median": group["score"].median(),
            "Max": group["score"].max(),
            "MinMeet": group.loc[min_idx, "meet"],
            "MaxMeet": group.loc[max_idx, "meet"]
        })

    stats_df = pd.DataFrame(stats)

    if stats_df.empty:
        return stats_df

    stats_df = stats_df.sort_values(
        "Median",
        ascending=False
    )

    return stats_df


def render_dive_score_distribution_page(supabase):
    st.header("Dive Score Distribution")

    df = build_dive_distribution_dataframe(supabase)

    if df.empty:
        st.warning("No data found.")
        return

    # --------------------------------------------------
    # REQUIRED DIVER FILTER
    # --------------------------------------------------

    available_divers = sorted(
        df["diver"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_divers = st.multiselect(
        "Diver *",
        available_divers
    )

    if not selected_divers:
        st.info("Select at least one diver.")
        return

    filtered = df[
        df["diver"].isin(selected_divers)
    ].copy()

    # --------------------------------------------------
    # OPTIONAL SEASON FILTER
    # --------------------------------------------------

    available_seasons = sorted(
        filtered["Season"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_season = st.selectbox(
        "Season (Optional)",
        ["All"] + available_seasons
    )

    if selected_season != "All":
        filtered = filtered[
            filtered["Season"] == selected_season
        ]

    # --------------------------------------------------
    # OPTIONAL YEAR FILTER
    # --------------------------------------------------

    available_years = sorted(
        filtered["Year"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_year = st.selectbox(
        "Year (Optional)",
        ["All"] + available_years
    )

    if selected_year != "All":
        filtered = filtered[
            filtered["Year"] == selected_year
        ]

    # --------------------------------------------------
    # OPTIONAL DIVE FILTER
    # --------------------------------------------------

    available_dives = sorted(
        filtered["dive_number"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_dives = st.multiselect(
        "Dive(s) (Optional)",
        available_dives
    )

    if selected_dives:
        filtered = filtered[
            filtered["dive_number"].isin(selected_dives)
        ]

    if filtered.empty:
        st.warning("No matching results found.")
        return

    # --------------------------------------------------
    # CALCULATE BOXPLOT STATS
    # --------------------------------------------------

    stats_df = build_stats_dataframe(filtered)

    if stats_df.empty:
        st.warning("No matching results found.")
        return

    median_order = stats_df["dive_number"].tolist()

    plot_df = filtered.merge(
        stats_df,
        on="dive_number",
        how="left"
    )

    plot_df["dive_number"] = pd.Categorical(
        plot_df["dive_number"],
        categories=median_order,
        ordered=True
    )

    plot_df = plot_df.sort_values(
        "dive_number"
    )

    # --------------------------------------------------
    # BOXPLOT
    # --------------------------------------------------

    fig = px.box(
        plot_df,
        x="dive_number",
        y="score",
        points="all",
        category_orders={
            "dive_number": median_order
        }
    )

    fig.update_traces(
        customdata=plot_df[
            [
                "Min",
                "Median",
                "Max",
                "MinMeet",
                "MaxMeet"
            ]
        ],
        hovertemplate=
        "<b>Dive %{x}</b><br>"
        "Score: %{y:.2f}<br>"
        "<br>"
        "Min: %{customdata.2f}<br>"
        "Min Meet: %{customdata[3]}<br>"
        "<br>"
        "Median: %{customdata.2f}<br>"
        "<br>"
        "Max: %{customdata.2f}<br>"
        "Max Meet: %{customdata[4]}"
        "<extra></extra>"
    )

    fig.update_layout(
        height=700,
        xaxis_title="Dive",
        yaxis_title="Score",
        showlegend=False
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # --------------------------------------------------
    # SUMMARY TABLE
    # --------------------------------------------------

    st.markdown("---")
    st.subheader("Dive Statistics")

    display_stats = stats_df[
        [
            "dive_number",
            "Count",
            "Min",
            "Median",
            "Max",
            "MinMeet",
            "MaxMeet"
        ]
    ].rename(
        columns={
            "dive_number": "Dive"
        }
    )

    st.dataframe(
        display_stats,
        hide_index=True,
        use_container_width=True
    )

    # --------------------------------------------------
    # RAW DATA
    # --------------------------------------------------

    st.markdown("---")
    st.subheader("Underlying Data")

    st.dataframe(
        filtered[
            [
                "diver",
                "meet",
                "dive_number",
                "score",
                "date"
            ]
        ].sort_values(
            [
                "dive_number",
                "score"
            ],
            ascending=[
                True,
                False
            ]
        ),
        hide_index=True,
        use_container_width=True
    )