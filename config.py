"""Streamlit page configuration — must run before any other st.* call."""
import streamlit as st


def configure_page():
    st.set_page_config(
        page_title="Market Basket Analysis",
        page_icon="🛒",
        layout="wide"
    )
