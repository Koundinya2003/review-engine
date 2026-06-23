"""
Streamlit dashboard with JWT authentication and role-based access.

Production-ready dashboard for Review Discovery Engine with:
- User authentication (login/register)
- Role-based access control
- Comprehensive analytics visualizations
- Search capabilities
- Admin panel for analysis jobs
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from functools import wraps
import os
from urllib.parse import urljoin

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
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

def init_session():
    """Initialize session state."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "token" not in st.session_state:
        st.session_state.token = None
    if "user" not in st.session_state:
        st.session_state.user = None
    if "role" not in st.session_state:
        st.session_state.role = "viewer"


init_session()


# ============================================================================
# API HELPER
# ============================================================================

def api_call(method: str, endpoint: str, max_retries: int = 2, **kwargs):
    """Make API call with error handling and retries."""
    url = urljoin(API_BASE_URL, endpoint)
    headers = kwargs.pop("headers", {})
    timeout = kwargs.pop("timeout", 10)  # Reduced from 30
    
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            response = requests.request(
                method, url, headers=headers, timeout=timeout, **kwargs
            )
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.Timeout:
            last_error = "Request timed out"
            if attempt < max_retries - 1:
                st.warning(f"⏳ Timeout, retrying... ({attempt + 1}/{max_retries})")
                continue
                
        except requests.ConnectionError:
            last_error = "Cannot connect to API"
            if attempt < max_retries - 1:
                st.warning(f"🔌 Connection failed, retrying... ({attempt + 1}/{max_retries})")
                continue
                
        except Exception as e:
            last_error = str(e)
            break
    
    st.error(f"❌ API Error: {last_error}")
    return None


# ============================================================================
# AUTHENTICATION
# ============================================================================

def show_login_page():
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
                
                if submit and username and password:
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
                    else:
                        st.error("❌ Invalid credentials")
        
        with tab2:
            with st.form("register_form"):
                st.write("**Create new account**")
                username = st.text_input("Username", key="reg_user")
                email = st.text_input("Email", key="reg_email")
                password = st.text_input("Password", type="password", key="reg_pass")
                password_confirm = st.text_input("Confirm Password", type="password", key="reg_pass_conf")
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
                        else:
                            st.error("❌ Registration failed")


def logout():
    """Logout user."""
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.user = None
    st.rerun()


# ============================================================================
# PAGES
# ============================================================================

def page_dashboard():
    """Dashboard overview."""
    st.title("📊 Dashboard")
    
    # Get analytics
    analytics = api_call("GET", "/api/v1/analytics/overview")
    
    if not analytics:
        st.warning("⚠️ No data available")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📝 Total Reviews", analytics.get("total_reviews", 0))
    with col2:
        avg = analytics.get("average_rating", 0)
        st.metric("⭐ Avg Rating", f"{avg:.2f}" if avg > 0 else "N/A")
    with col3:
        st.metric("🎯 Themes", analytics.get("unique_themes", 0))
    with col4:
        st.metric("📌 Sources", analytics.get("unique_sources", 0))
    
    st.divider()
    
    # Visualizations
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


def page_search():
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
            endpoint = f"/api/v1/search/semantic" if search_type == "Semantic" else f"/api/v1/search/hybrid"
            results = api_call("POST", endpoint, json={"query": query, "limit": limit})
            
            if results and "results" in results:
                st.success(f"✅ Found {len(results['results'])} results")
                
                for idx, result in enumerate(results["results"], 1):
                    col1, col2 = st.columns([0.7, 0.3])
                    with col1:
                        with st.expander(f"{idx}. {result['review'].get('title', 'Untitled')}", expanded=False):
                            st.write(f"**Score:** {result['score']:.3f} | **Rating:** {result['review'].get('rating', 'N/A')}")
                            st.write(result['review'].get('text', 'N/A'))
                    with col2:
                        st.caption(f"Source: {result['review'].get('source', '?')}")


def page_analytics():
    """Analytics view."""
    st.title("📈 Analytics")
    
    days = st.slider("Period (days):", 1, 365, 30)
    
    trends = api_call("GET", f"/api/v1/analytics/trends?days={days}")
    
    if trends and "trends" in trends:
        df = pd.DataFrame(trends["trends"])
        st.dataframe(df, use_container_width=True)
        
        if len(df) > 0:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df.get("date", []),
                y=df.get("count", []),
                mode='lines+markers',
                name='Reviews'
            ))
            fig.update_layout(title="Review Trends", xaxis_title="Date", yaxis_title="Count", height=400)
            st.plotly_chart(fig, use_container_width=True)


def page_admin():
    """Admin panel."""
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
                    result = api_call("POST", "/api/v1/analysis/discover-themes", json={"n_themes": n_themes})
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

def main():
    """Main application."""
    if not st.session_state.authenticated:
        show_login_page()
    else:
        # Sidebar
        with st.sidebar:
            st.title(APP_TITLE)
            
            # Fetch user info if not cached
            if not st.session_state.user:
                user = api_call("GET", "/api/v1/auth/me")
                if user:
                    st.session_state.user = user
                    st.session_state.role = user.get("role", "viewer")
            
            # User info
            if st.session_state.user:
                st.write(f"👤 **{st.session_state.user.get('username', 'User')}**")
                st.write(f"Role: **{st.session_state.role.upper()}**")
                st.divider()
            
            # Navigation
            pages = [
                ("📊 Dashboard", "dashboard"),
                ("🔍 Search", "search"),
                ("📈 Analytics", "analytics"),
            ]
            
            if st.session_state.role == "admin":
                pages.append(("⚙️ Admin", "admin"))
            
            pages.append(("🚪 Logout", "logout"))
            
            page = st.radio("Navigation", [p[0] for p in pages], format_func=str)
            
            page_key = next((p[1] for p in pages if p[0] == page), None)
            
            if page_key == "logout":
                logout()
                return
            
            st.session_state.current_page = page_key
        
        # Pages
        if st.session_state.get("current_page") == "dashboard":
            page_dashboard()
        elif st.session_state.get("current_page") == "search":
            page_search()
        elif st.session_state.get("current_page") == "analytics":
            page_analytics()
        elif st.session_state.get("current_page") == "admin":
            page_admin()
        else:
            page_dashboard()


if __name__ == "__main__":
    main()
