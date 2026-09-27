"""General-purpose helpers shared across multiple pages: history tracking,
the recommendation bar chart, product-frequency reporting, and Excel
file loading (used on several of the Advanced pipeline pages plus the
Simple "Get Recommendations" flow)."""
import io
from collections import Counter
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def save_to_history(df, name):
    """Saves the generated rules to the history session state."""
    entry = {
        'id': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'name': name,
        'data': df.copy()
    }
    st.session_state.history.append(entry)

def render_recommendation_chart(df):
    """Renders a professional horizontal bar chart with a purple-to-pink gradient."""
    fig, ax = plt.subplots(figsize=(8, 4))
    
    # Sort for chart
    df_sorted = df.sort_values('Match Score', ascending=True)
    products = df_sorted['Recommend'].astype(str).tolist()
    values = df_sorted['Match Score'].tolist()
    
    # Create gradient colors matching the app theme
    cmap = plt.get_cmap('plasma')
    colors = [cmap(i) for i in np.linspace(0.2, 0.8, max(1, len(products)))]
    
    bars = ax.barh(products, values, color=colors, edgecolor='none')
    
    # Value labels
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.05, bar.get_y() + bar.get_height()/2, 
                f'{width:.2f}', ha='left', va='center', fontsize=10, color='#1e1b2e')
    
    # Clean spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e4e1ec')
    ax.spines['bottom'].set_color('#e4e1ec')
    
    ax.set_title("Match Strength Profile", fontsize=12, pad=15, color='#5b21b6', fontweight='bold')
    ax.set_xlabel("Lift Score", color='#5b21b6')
    
    return fig

def reset_analysis():
    """Clears everything downstream of the dataset — the transaction/
    basket build, plus anything derived from it — so a newly uploaded
    or re-cleaned dataset never inherits stale results or stale
    column choices from a previous, differently-shaped dataset.

    transaction_column / product_column matter here even though they
    look like simple settings: they're written by a widget `key` on
    the Data Transformation page, so once set they persist across
    reruns and across page switches for the rest of the session. If
    they're left pointing at a column name from a previous dataset
    that the new one doesn't have, other pages that trust them
    (Best Time to Sell, Time-Aware Recommendations) either crash with
    a KeyError, or — worse — Streamlit silently resets an invalid
    selectbox value to its first option, which can make Transaction
    and Product silently resolve to the very same column with no
    error at all."""

    st.session_state.transactions = None
    st.session_state.basket_df = None
    st.session_state.frequent_itemsets = None
    st.session_state.rules_df = None

    # These are Streamlit widget keys (Data Transformation's selectboxes),
    # so pop them instead of setting to None — a selectbox bound to a key
    # holding None returns None with no options selected, whereas an
    # absent key makes the widget fall back to its normal, safe default
    # (the first column), the same as a brand-new session would see.
    st.session_state.pop("transaction_column", None)
    st.session_state.pop("product_column", None)

    st.session_state.btts_slice_rules = None
    st.session_state.btts_overall_rules = None
    st.session_state.btts_period_label = None


def format_itemset(itemset):

    return ", ".join(
        sorted(
            [str(item) for item in itemset]
        )
    )


def get_product_frequency(transactions):

    counter = Counter()

    for transaction in transactions:

        counter.update(transaction)

    freq_df = pd.DataFrame(
        counter.items(),
        columns=["Product", "Frequency"]
    )

    freq_df = (
        freq_df
        .sort_values(
            "Frequency",
            ascending=False
        )
        .reset_index(drop=True)
    )

    return freq_df


def render_product_frequency_section(transactions, key_prefix):

    st.subheader("📊 Product Frequency Count")

    st.write(
        """
        How many transactions each product appears in.
        A higher frequency means the product shows up in
        more baskets, which drives its support value.
        """
    )

    freq_df = get_product_frequency(transactions)

    max_available = len(freq_df)

    if max_available <= 1:

        top_freq = freq_df

    else:

        top_n = st.slider(
            "Number of products to show",
            min_value=min(5, max_available),
            max_value=max_available,
            value=min(20, max_available),
            step=5 if max_available >= 5 else 1,
            key=f"{key_prefix}_freq_top_n"
        )

        top_freq = freq_df.head(top_n)

    col1, col2 = st.columns([2, 3])

    with col1:

        st.dataframe(
            top_freq,
            use_container_width=True,
            height=380
        )

    with col2:

        chart_data = (
            top_freq
            .set_index("Product")
        )

        st.bar_chart(
            chart_data["Frequency"]
        )

    with st.expander("📋 View full product frequency table"):

        st.dataframe(
            freq_df,
            use_container_width=True
        )

        freq_csv = (
            freq_df
            .to_csv(index=False)
            .encode("utf-8")
        )

        st.download_button(
            label="⬇️ Download Product Frequency (CSV)",
            data=freq_csv,
            file_name="Product_Frequency.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"{key_prefix}_freq_download"
        )

    st.markdown("---")


def is_csv_file(filename):
    return str(filename).strip().lower().endswith(".csv")


@st.cache_data(show_spinner=False)
def load_csv_file(file_bytes):
    """Reads an uploaded .csv file. CSV has no sheets and no XML to
    parse, so this is typically 10-70x faster than reading the same
    data as .xlsx — worth using directly if your source data can be
    exported as CSV instead of Excel."""

    try:
        return pd.read_csv(io.BytesIO(file_bytes))
    except UnicodeDecodeError:
        # Some exports (Excel's own "CSV" export, in particular) use
        # a Windows-1252/Latin-1 encoding instead of UTF-8.
        return pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")


@st.cache_data(show_spinner=False)
def load_excel_sheet(file_bytes, sheet_name):
    """Reads one sheet from an uploaded .xlsx file. Tries the calamine
    engine first — it's a Rust-based xlsx parser that's typically
    5-10x faster than the default openpyxl engine, which matters a
    lot once a file has hundreds of thousands of rows. Falls back to
    openpyxl automatically if calamine isn't installed."""

    try:
        return pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=sheet_name,
            engine="calamine"
        )
    except (ImportError, ValueError):
        return pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=sheet_name
        )


def load_dataset(file_bytes, filename, sheet_name=None):
    """Single entry point used by the upload pages: dispatches to the
    CSV or Excel reader based on the uploaded file's extension."""

    if is_csv_file(filename):
        return load_csv_file(file_bytes)

    return load_excel_sheet(file_bytes, sheet_name)


@st.cache_data(show_spinner=False)
def get_sheet_names(file_bytes, filename="workbook.xlsx"):
    """Returns the list of sheet names for an Excel file. CSV files
    have no sheets, so a single placeholder name is returned instead
    — callers can treat it exactly like a one-sheet workbook."""

    if is_csv_file(filename):
        return ["CSV Data"]

    try:
        return pd.ExcelFile(
            io.BytesIO(file_bytes),
            engine="calamine"
        ).sheet_names
    except (ImportError, ValueError):
        return pd.ExcelFile(
            io.BytesIO(file_bytes)
        ).sheet_names


