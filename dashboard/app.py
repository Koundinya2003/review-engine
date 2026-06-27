"""
Streamlit dashboard with JWT authentication and role-based access.

Production-ready dashboard for Review Discovery Engine with:
- User authentication (login/register)
- Role-based access control
- Comprehensive analytics visualizations
- Search capabilities
- Admin panel for analysis jobs
"""

import os
import time

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
APP_TITLE = "📊 Review Discovery Engine"
PAGE_ICON = "📊"

st.set_page_config(
    page_title="Review Discovery",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# SESSION STATE
# ============================================================================

def init_session() -> None:
    """Initialize session state."""
    defaults = {
        "authenticated": False,
        "token": None,
        "user": None,
        "role": "viewer",
        "current_page": "dashboard",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session()


# ============================================================================
# API HELPER
# ============================================================================

def _build_url(endpoint: str) -> str:
    """Join the API base URL with an endpoint path.

    Plain string concatenation rather than urljoin(): urljoin() treats any
    endpoint starting with "/" as an absolute path and replaces the entire
    path component of the base URL - so if API_BASE_URL ever includes a
    prefix (e.g. behind a reverse proxy at "http://host/api-gateway"),
    urljoin would silently drop that prefix and hit the wrong path.
    """
    return f"{API_BASE_URL}/{endpoint.lstrip('/')}"


def api_call(method: str, endpoint: str, max_retries: int = 2, **kwargs):
    """Make an API call with error handling, retries, and session expiry."""
    url = _build_url(endpoint)
    headers = kwargs.pop("headers", {})
    timeout = kwargs.pop("timeout", 10)

    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    last_error = None

    for attempt in range(max_retries):
        try:
            response = requests.request(
                method, url, headers=headers, timeout=timeout, **kwargs
            )

            if response.status_code == 401:
                # Token missing/expired/invalid - no point retrying, and a
                # generic "API Error" here would just confuse the user into
                # thinking the request failed rather than their session.
                st.warning("🔒 Your session has expired. Please log in again.")
                logout()
                return None

            response.raise_for_status()
            return response.json() if response.content else {}

        except requests.Timeout:
            last_error = "Request timed out"
        except requests.ConnectionError:
            last_error = "Cannot connect to API"
        except requests.HTTPError as e:
            last_error = f"{e.response.status_code} error: {e.response.text[:200]}"
            break  # Non-401 HTTP errors (404, 422, 500...) won't be fixed by retrying
        except Exception as e:
            last_error = str(e)
            break

        if attempt < max_retries - 1:
            st.warning(f"⏳ {last_error}, retrying... ({attempt + 1}/{max_retries})")
            time.sleep(0.5 * (attempt + 1))  # small backoff between retries

    st.error(f"❌ API Error: {last_error}")
    return None


# ============================================================================
# AUTHENTICATION
# ============================================================================

def show_login_page() -> None:
    """Display login/register interface."""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.title(APP_TITLE)
        st.write("Turn reviews into actionable product insights with AI")
        st.divider()

        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            with st.form("login_form"):
                st.write("**Login to your account**")
                username = st.text_input("Username", key="login_user")
                password = st.text_input("Password", type="password", key="login_pass")
                submit = st.form_submit_button("🔓 Login", use_container_width=True)

                if submit:
                    if not username or not password:
                        st.error("❌ Please enter both username and password")
                    else:
                        result = api_call(
                            "POST",
                            "/api/v1/auth/login",
                            json={"username": username, "password": password},
                        )
                        if result and "access_token" in result:
                            st.session_state.authenticated = True
                            st.session_state.token = result["access_token"]
                            st.success("✅ Login successful!")
                            st.rerun()
                        elif result is not None:
                            st.error("❌ Invalid credentials")

        with tab2:
            with st.form("register_form"):
                st.write("**Create new account**")
                username = st.text_input("Username", key="reg_user")
                email = st.text_input("Email", key="reg_email")
                password = st.text_input("Password", type="password", key="reg_pass")
                password_confirm = st.text_input(
                    "Confirm Password", type="password", key="reg_pass_conf"
                )
                submit = st.form_submit_button("📝 Register", use_container_width=True)

                if submit:
                    if not all([username, email, password]):
                        st.error("❌ Please fill all fields")
                    elif password != password_confirm:
                        st.error("❌ Passwords don't match")
                    elif len(password) < 8:
                        st.error("❌ Password must be 8+ characters")
                    else:
                        result = api_call(
                            "POST",
                            "/api/v1/auth/register",
                            json={"username": username, "email": email, "password": password},
                        )
                        if result and "access_token" in result:
                            st.session_state.authenticated = True
                            st.session_state.token = result["access_token"]
                            st.success("✅ Registration successful! Logged in.")
                            st.rerun()
                        elif result is not None:
                            st.error("❌ Registration failed")


def logout() -> None:
    """Clear session and return to the login screen."""
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.role = "viewer"
    st.session_state.current_page = "dashboard"
    st.rerun()


# ============================================================================
# PAGES
# ============================================================================

def page_dashboard() -> None:
    """Dashboard overview."""
    st.title("📊 Dashboard")

    analytics = api_call("GET", "/api/v1/analytics/overview")
    if not analytics:
        st.warning("⚠️ No data available")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📝 Total Reviews", analytics.get("total_reviews", 0))
    with col2:
        # analytics.get(..., 0) only applies the default when the key is
        # MISSING - if the API returns average_rating: null explicitly,
        # `avg` is None and `avg > 0` raises a TypeError. `or 0` covers both.
        avg = analytics.get("average_rating") or 0
        st.metric("⭐ Avg Rating", f"{avg:.2f}" if avg > 0 else "N/A")
    with col3:
        st.metric("🎯 Themes", analytics.get("unique_themes", 0))
    with col4:
        st.metric("📌 Sources", analytics.get("unique_sources", 0))

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        sentiment = analytics.get("sentiment_breakdown", {})
        if sentiment:
            fig = go.Figure([go.Bar(
                x=list(sentiment.keys()),
                y=list(sentiment.values()),
                marker=dict(color=['#00CC96', '#EF553B', '#AB63FA', '#636EFA']),
            )])
            fig.update_layout(title="Sentiment", xaxis_title="", yaxis_title="Count", height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        ratings = analytics.get("rating_breakdown", {})
        if ratings:
            fig = go.Figure([go.Bar(
                x=list(ratings.keys()),
                y=list(ratings.values()),
                marker_color='#636EFA',
            )])
            fig.update_layout(title="Ratings Distribution", xaxis_title="Rating", yaxis_title="Count", height=300)
            st.plotly_chart(fig, use_container_width=True)


def page_search() -> None:
    """Search reviews."""
    st.title("🔍 Search Reviews")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Search query:", placeholder="e.g., 'app crashes frequently'")
    with col2:
        search_type = st.selectbox("Type:", ["Semantic", "Hybrid"])

    limit = st.slider("Results:", 5, 50, 20)

    if query:
        with st.spinner("Searching..."):
            endpoint = (
                "/api/v1/search/semantic" if search_type == "Semantic"
                else "/api/v1/search/hybrid"
            )
            results = api_call("POST", endpoint, json={"query": query, "limit": limit})

            if results and "results" in results:
                st.success(f"✅ Found {len(results['results'])} results")

                for idx, result in enumerate(results["results"], 1):
                    col1, col2 = st.columns([0.7, 0.3])
                    review = result.get("review", {})
                    with col1:
                        with st.expander(f"{idx}. {review.get('title', 'Untitled')}", expanded=False):
                            st.write(
                                f"**Score:** {result.get('score', 0):.3f} | "
                                f"**Rating:** {review.get('rating', 'N/A')}"
                            )
                            st.write(review.get('text', 'N/A'))
                    with col2:
                        st.caption(f"Source: {review.get('source', '?')}")
            elif results is not None:
                st.info("No results found.")


def page_analytics() -> None:
    """Analytics view."""
    st.title("📈 Analytics")

    days = st.slider("Period (days):", 1, 365, 30)

    trends = api_call("GET", f"/api/v1/analytics/trends?days={days}")

    if trends and "trends" in trends:
        df = pd.DataFrame(trends["trends"])
        st.dataframe(df, use_container_width=True)

        if len(df) > 0 and "date" in df.columns and "count" in df.columns:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"],
                y=df["count"],
                mode='lines+markers',
                name='Reviews',
            ))
            fig.update_layout(title="Review Trends", xaxis_title="Date", yaxis_title="Count", height=400)
            st.plotly_chart(fig, use_container_width=True)


def page_admin() -> None:
    """Admin panel.

    Note: this client-side role check is a UX convenience only - real
    enforcement happens server-side (the API rejects non-admin/analyst
    tokens), so a user can't actually gain access by tampering with the
    frontend.
    """
    if st.session_state.role != "admin":
        st.error("🔒 Admin access required")
        return

    st.title("⚙️ Admin Panel")

    tab1, tab2 = st.tabs(["Theme Discovery", "Embeddings"])

    with tab1:
        st.subheader("🎯 Discover Themes")
        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            n_themes = st.slider("Number of themes:", 2, 20, 8)
        with col2:
            if st.button("Run", use_container_width=True, type="primary"):
                with st.spinner("Discovering themes..."):
                    result = api_call(
                        "POST", "/api/v1/analysis/discover-themes", json={"n_themes": n_themes}
                    )
                    if result:
                        st.success(f"✅ Found {result.get('themes_found', 0)} themes")
                        st.json(result)

    with tab2:
        st.subheader("🔄 Embedding Index")
        if st.button("Index Embeddings", use_container_width=True, type="primary"):
            with st.spinner("Indexing..."):
                result = api_call("POST", "/api/v1/analysis/index-embeddings", json={})
                if result:
                    st.success(f"✅ Indexed {result.get('indexed_count', 0)} embeddings")


# ============================================================================
# MAIN
# ============================================================================

PAGES = [
    ("📊 Dashboard", "dashboard", page_dashboard),
    ("🔍 Search", "search", page_search),
    ("📈 Analytics", "analytics", page_analytics),
]
ADMIN_PAGE = ("⚙️ Admin", "admin", page_admin)


def main() -> None:
    """Main application."""
    if not st.session_state.authenticated:
        show_login_page()
        return

    with st.sidebar:
        st.title(APP_TITLE)

        if not st.session_state.user:
            user = api_call("GET", "/api/v1/auth/me")
            if user:
                st.session_state.user = user
                st.session_state.role = user.get("role", "viewer")

        if st.session_state.user:
            st.write(f"👤 **{st.session_state.user.get('username', 'User')}**")
            st.write(f"Role: **{st.session_state.role.upper()}**")
            st.divider()

        pages = list(PAGES)
        if st.session_state.role == "admin":
            pages.append(ADMIN_PAGE)

        labels = [p[0] for p in pages]
        current_label = next(
            (p[0] for p in pages if p[1] == st.session_state.current_page), labels[0]
        )
        selected_label = st.radio(
            "Navigation", labels, index=labels.index(current_label), key="nav_radio"
        )
        st.session_state.current_page = next(
            p[1] for p in pages if p[0] == selected_label
        )

        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            return

    page_fn = next(
        (p[2] for p in pages if p[1] == st.session_state.current_page),
        page_dashboard,
    )
    page_fn()


if __name__ == "__main__":
    main()