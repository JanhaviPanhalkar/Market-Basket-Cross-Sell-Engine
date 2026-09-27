"""
Market Basket Analysis & Cross-Sell Engine
--------------------------------------------
Entry point only. Each concern lives in its own file:

    config.py     -> st.set_page_config
    theme.py      -> CSS
    state.py      -> session_state defaults
    db.py         -> MySQL save
    helpers.py    -> history, chart, product-frequency helpers
    pipeline.py   -> Excel loading, cleaning, transactions, Apriori, rules
    sidebar.py    -> mode toggle + page navigation
    views/*.py    -> one file per page, each exposing render()

Run with:  streamlit run app.py
"""
import streamlit as st

from config import configure_page
from theme import inject_theme
from state import init_session_state
from sidebar import render_sidebar

from views import (
    get_recommendations,
    best_time_to_sell,
    home,
    sales_overview,
    data_preparation,
    eda,
    data_transformation,
    apriori_algorithm,
    association_rules,
    product_recommendation,
    bundle_creation,
    time_aware_recommendations,
    dashboard,
    history,
)

# ---------------------------------------------------------
# STARTUP
# ---------------------------------------------------------

configure_page()
inject_theme()
init_session_state()

page = render_sidebar()

# ---------------------------------------------------------
# ROUTING
# ---------------------------------------------------------

PAGES = {
    "🚀 Get Recommendations": get_recommendations.render,
    "🕒 Best Time to Sell": best_time_to_sell.render,
    "🏠 Home": home.render,
    "📈 Sales Overview": sales_overview.render,
    "📂 Data Preparation": data_preparation.render,
    "📈 EDA": eda.render,
    "🔄 Data Transformation": data_transformation.render,
    "🧠 Apriori Algorithm": apriori_algorithm.render,
    "📑 Association Rules": association_rules.render,
    "🛍 Product Recommendation": product_recommendation.render,
    "🎁 Bundle Creation": bundle_creation.render,
    "🕒 Time-Aware Recommendations": time_aware_recommendations.render,
    "📊 Dashboard": dashboard.render,
    "🕘 History": history.render,
}

PAGES[page]()

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.markdown("---")
st.caption("🛒 Market Basket Analysis & Cross-Sell Engine")
