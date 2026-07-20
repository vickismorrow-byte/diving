import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from power_rankings import render_power_rankings_page
from score_progression import render_score_progression_page
from edit_results import render_edit_results_page
from boxplots import render_dive_score_distribution_page
from add_results import render_add_results_page

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Huskie Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("Huskie Analytics - NNHS Diving Database")
st.write("This app showcases the historical results of all Naperville North divers.")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "is_approved" not in st.session_state:
    st.session_state.is_approved = False

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "first_name" not in st.session_state:
    st.session_state.first_name = ""

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

from werkzeug.security import check_password_hash

def authenticate_user(email, password):

    response = (
        supabase.table("users")
        .select("*")
        .eq(
            "email",
            email.lower().strip()
        )
        .execute()
    )

    if not response.data:
        st.error("Invalid email or password.")
        return None

    user = response.data[0]

    if not check_password_hash(
        user["password"],
        password
    ):
        st.error("Invalid email or password.")
        return None

    if not user["is_approved"]:
        st.error(
            "Your account has not yet been approved."
        )
        return None

    return user


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

# =====================================================
# AUTHENTICATION GATE
# =====================================================

if not st.session_state.authenticated:

    tab1, tab2 = st.tabs(["Login", "Create Account"])

    # --------------------------
    # LOGIN
    # --------------------------

    with tab1:

        st.header("Login")

        login_email = st.text_input(
            "Email",
            key="login_email"
        )

        login_password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button("Login"):

            user = authenticate_user(
                login_email,
                login_password
            )

            if user:

                st.session_state.authenticated = True
                st.session_state.user_email = user["email"]
                st.session_state.is_admin = user["is_admin"]
                st.session_state.is_approved = user["is_approved"]

                st.rerun()

    # --------------------------
    # CREATE ACCOUNT
    # --------------------------

    with tab2:

        st.header("Create Account")

        with st.form("create_account_form"):

            first_name = st.text_input(
                "First Name"
            )

            last_name = st.text_input(
                "Last Name"
            )

            email = st.text_input(
                "Email Address"
            )

            password = st.text_input(
                "Password",
                type="password"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password"
            )

            create_submit = st.form_submit_button(
                "Create Account",
                use_container_width=True
            )

        if create_submit:

            first_name = first_name.strip()
            last_name = last_name.strip()
            email = email.strip().lower()

            if not first_name:
                st.error("First name is required.")

            elif not last_name:
                st.error("Last name is required.")

            elif not email:
                st.error("Email is required.")

            elif not password:
                st.error("Password is required.")

            elif not confirm_password:
                st.error("Please confirm your password.")

            elif password != confirm_password:
                st.error("Passwords do not match.")

            else:

                existing_user = (
                    supabase.table("users")
                    .select("email")
                    .eq("email", email)
                    .execute()
                )

                if existing_user.data:

                    st.error("Account already exists.")

                else:

                    (
                        supabase.table("users")
                        .insert(
                            {
                                "email": email,
                                "first_name": first_name.title(),
                                "last_name": last_name.title(),

                                # IMPORTANT
                                "password": generate_password_hash(
                                    password
                                ),

                                "is_admin": False,
                                "is_approved": False,
                            }
                        )
                        .execute()
                    )

                    st.success(
                        "Account created successfully. "
                        "Awaiting administrator approval."
                    )

    st.stop()

with st.sidebar:

    if st.button("Logout"):

        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.is_admin = False
        st.session_state.is_approved = False

        st.rerun()


if "page" not in st.session_state:
    st.session_state.page = "Power Rankings"

with st.sidebar:

    with st.expander("📊 Analytics", expanded=True):
        if st.button("Top Scores"):
            st.session_state.page = "Top Scores"

        if st.button("Score Progression"):
            st.session_state.page = "Score Progression"

        if st.button("Power Rankings"):
            st.session_state.page = "Power Rankings"

        if st.button("Dive Analysis"):
            st.session_state.page = "Dive Analysis"

    if st.session_state.is_admin:
        with st.expander("⚙️ Administration"):
            if st.button("Approve Users"):
                st.session_state.page = "Approve Users"

            if st.button("Add Meet"):
                st.session_state.page = "Add Meet"
            if st.button("Add Diver"):
                st.session_state.page = "Add Diver"
            if st.button("Add Results"):
                st.session_state.page = "Add Results"
            if st.button("View/Edit Results"):
                st.session_state.page = "View/Edit Results"

page = st.session_state.page


# =====================================================
# ADD DIVER
# =====================================================

if page == "Add Diver":

    if not st.session_state.is_admin:
        st.error("Admin access required")
        st.stop()


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

    if not st.session_state.is_admin:
        st.error("Admin access required")
        st.stop()


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

    if not st.session_state.is_admin:
        st.error("Admin access required")
        st.stop()

    render_add_results_page(supabase)


    
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

            top_frames = []

            six_df = df[df["6-Dive Score"].notna()]

            if not six_df.empty:

                idx = (
                    six_df.groupby("diver")["6-Dive Score"]
                    .idxmax()
                )

                best6 = six_df.loc[idx].copy()

                best6["Format"] = "6-Dive"

                best6["Score"] = best6["6-Dive Score"]

                top_frames.append(
                    best6[
                        ["diver", "meet", "Format", "Score"]
                    ]
                )

            eleven_df = df[df["11-Dive Score"].notna()]

            if not eleven_df.empty:

                idx = (
                    eleven_df.groupby("diver")["11-Dive Score"]
                    .idxmax()
                )

                best11 = eleven_df.loc[idx].copy()

                best11["Format"] = "11-Dive"

                best11["Score"] = best11["11-Dive Score"]

                top_frames.append(
                    best11[
                        ["diver", "meet", "Format", "Score"]
                    ]
                )

            if top_frames:

                display = pd.concat(
                    top_frames,
                    ignore_index=True
                )

            else:

                display = pd.DataFrame(
                    columns=[
                        "diver",
                        "meet",
                        "Format",
                        "Score"
                    ]
                )

            display = display.rename(
                columns={
                    "diver": "Diver",
                    "meet": "Meet"
                }
            )

            rank_col = "Score"

    if score_type == "Top Scores" and format_filter == "All":

        pass

    elif format_filter == "6-Dive":

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

    if "Score" in display.columns:
        display = display.sort_values(
            "Score",
            ascending=False
        ).reset_index(drop=True)

        display["Rank"] = range(
            1,
            len(display) + 1
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

elif page == "Power Rankings":
    render_power_rankings_page(supabase)

elif page == "Score Progression":
    render_score_progression_page(supabase)

if page == "Approve Users":

    st.title("User Approvals")

    pending_users = (
        supabase.table("users")
        .select("*")
        .eq("is_approved", False)
        .order("last_name")
        .execute()
    )

    if not pending_users.data:

        st.success(
            "No users awaiting approval."
        )

    for user in pending_users.data:

        col1, col2, col3 = st.columns(
            [5, 1, 1]
        )

        with col1:

            st.write(
                f"{user['first_name']} "
                f"{user['last_name']} "
                f"({user['email']})"
            )

        with col2:

            if st.button(
                "Approve",
                key=f"approve_{user['email']}"
            ):

                (
                    supabase.table("users")
                    .update({
                        "is_approved": True
                    })
                    .eq(
                        "email",
                        user["email"]
                    )
                    .execute()
                )

                st.rerun()

        with col3:

            if st.button(
                "Delete",
                key=f"delete_{user['email']}"
            ):

                (
                    supabase.table("users")
                    .delete()
                    .eq(
                        "email",
                        user["email"]
                    )
                    .execute()
                )

                st.rerun()

elif page == "View/Edit Results":
    render_edit_results_page(supabase)

elif page == "Dive Analysis":
    render_dive_score_distribution_page(supabase)