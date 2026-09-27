"""Central session-state initialization. Every page reads/writes these keys,
so this must run once before any page renders."""
import streamlit as st


def init_session_state():
    if "data" not in st.session_state:
        st.session_state.data = None

    if "original_data" not in st.session_state:
        st.session_state.original_data = None

    if "transactions" not in st.session_state:
        st.session_state.transactions = None

    if "basket_df" not in st.session_state:
        st.session_state.basket_df = None

    if "frequent_itemsets" not in st.session_state:
        st.session_state.frequent_itemsets = None

    if "rules_df" not in st.session_state:
        st.session_state.rules_df = None
    
    if "history" not in st.session_state:
        st.session_state.history = []

    if "created_bundles" not in st.session_state:
        st.session_state.created_bundles = []

    # Seasonal / Time-Aware Recommendations page
    if "ta_slice_rules" not in st.session_state:
        st.session_state.ta_slice_rules = None

    if "ta_overall_rules" not in st.session_state:
        st.session_state.ta_overall_rules = None

    if "ta_used_support" not in st.session_state:
        st.session_state.ta_used_support = None

    if "ta_validation_results" not in st.session_state:
        st.session_state.ta_validation_results = None

    # Best Time to Sell page (Simple Mode's plain-language version)
    if "btts_slice_rules" not in st.session_state:
        st.session_state.btts_slice_rules = None

    if "btts_overall_rules" not in st.session_state:
        st.session_state.btts_overall_rules = None

    if "btts_period_label" not in st.session_state:
        st.session_state.btts_period_label = None

