"""Sales Overview rendering logic — shared by the standalone
'📈 Sales Overview' page (available in both Simple and Advanced mode)
and the Sales Overview tab inside '📊 Dashboard' (Advanced mode only).
Kept in one place so the two never show different numbers.
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from pipeline import detect_sales_columns


def render_funnel_chart(series, value_label):
    """Draws a horizontal funnel (centered, tapering bars, largest on
    top) from a pandas Series of value-by-category, in the app's
    existing purple/pink plasma gradient (same palette as the
    Match Strength chart on Product Recommendation)."""

    values = series.values.astype(float)
    labels = [str(label) for label in series.index]
    count = len(values)
    max_value = values.max() if count else 1

    fig, ax = plt.subplots(figsize=(8, 0.55 * count + 1.2))

    cmap = plt.get_cmap("plasma")
    colors = [
        cmap(i) for i in np.linspace(0.15, 0.85, max(1, count))
    ]

    y_positions = list(range(count))[::-1]

    for y, value, label, color in zip(
        y_positions, values, labels, colors
    ):

        width = value / max_value if max_value else 0
        left = (1 - width) / 2

        ax.barh(
            y, width, left=left, height=0.6,
            color=color, edgecolor="none"
        )

        ax.text(
            -0.02, y, label,
            ha="right", va="center", fontsize=9, color="#1e1b2e"
        )

        ax.text(
            1.02, y, f"{value:,.0f}",
            ha="left", va="center", fontsize=8, color="#4b4560"
        )

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.6, count - 0.4)
    ax.axis("off")
    ax.set_title(
        value_label, fontsize=11, color="#5b21b6",
        fontweight="bold", pad=10
    )

    st.pyplot(fig)
    plt.close(fig)


def render_sales_overview(data, transactions):

    st.subheader("📈 Sales Overview")

    st.caption(
        "Same page as Power BI's **Sales Overview** — revenue, orders, "
        "customers, top products, and revenue by country."
    )

    columns = detect_sales_columns(data)

    has_revenue = columns["quantity"] and columns["price"]

    revenue_series = None
    total_revenue = None

    if has_revenue:
        revenue_series = data[columns["quantity"]] * data[columns["price"]]
        total_revenue = revenue_series.sum()

    total_orders = (
        data[columns["invoice"]].nunique()
        if columns["invoice"] else None
    )

    total_customers = (
        data[columns["customer"]].nunique()
        if columns["customer"] else None
    )

    total_quantity = (
        data[columns["quantity"]].sum()
        if columns["quantity"] else None
    )

    avg_order_value = (
        total_revenue / total_orders
        if total_revenue is not None and total_orders
        else None
    )

    if transactions:

        avg_basket_size = (
            sum(len(basket) for basket in transactions)
            / len(transactions)
        )

    elif columns["invoice"] and columns["product"]:

        avg_basket_size = (
            data.groupby(columns["invoice"])[columns["product"]]
            .nunique()
            .mean()
        )

    else:

        avg_basket_size = None

    # -------------------------------------------------
    # KPI CARDS
    # -------------------------------------------------

    row1 = st.columns(3)
    row2 = st.columns(3)

    with row1[0]:
        st.metric(
            "💰 Total Revenue",
            f"{total_revenue:,.0f}" if total_revenue is not None else "N/A"
        )

    with row1[1]:
        st.metric(
            "🧾 Total Orders",
            f"{total_orders:,}" if total_orders is not None else "N/A"
        )

    with row1[2]:
        st.metric(
            "👥 Total Customers",
            f"{total_customers:,}" if total_customers is not None else "N/A"
        )

    with row2[0]:
        st.metric(
            "📦 Total Quantity Sold",
            f"{total_quantity:,.0f}" if total_quantity is not None else "N/A"
        )

    with row2[1]:
        st.metric(
            "💳 Average Order Value",
            f"{avg_order_value:,.2f}" if avg_order_value is not None else "N/A"
        )

    with row2[2]:
        st.metric(
            "🧺 Average Basket Size",
            f"{avg_basket_size:,.2f} items" if avg_basket_size is not None else "N/A"
        )

    if not has_revenue:
        st.caption(
            "ℹ️ Revenue-based metrics need a quantity column and a "
            "unit-price column — one of those wasn't found in this "
            "dataset, so revenue metrics show N/A."
        )

    st.markdown("---")

    # -------------------------------------------------
    # NEW: KEY INSIGHTS — plain-English callouts, no chart-reading
    # required. Kept short on purpose so a non-technical reader gets
    # the headline before diving into any chart below.
    # -------------------------------------------------

    insight_lines = []

    if has_revenue and columns["country"] and total_revenue:

        country_totals = (
            revenue_series
            .groupby(data[columns["country"]])
            .sum()
            .sort_values(ascending=False)
        )

        if not country_totals.empty:

            top_country = country_totals.index[0]
            top_country_share = country_totals.iloc[0] / total_revenue * 100

            insight_lines.append(
                f"🌍 **{top_country}** is the top market — "
                f"**{top_country_share:.0f}%** of total revenue."
            )

    if has_revenue and columns["product"]:

        product_totals = (
            revenue_series
            .groupby(data[columns["product"]])
            .sum()
            .sort_values(ascending=False)
        )

        if not product_totals.empty:

            insight_lines.append(
                f"🏆 **{product_totals.index[0]}** is the best-selling "
                "product by revenue."
            )

    if has_revenue and columns["date"]:

        month_totals = (
            revenue_series
            .groupby(
                pd.to_datetime(
                    data[columns["date"]], errors="coerce"
                ).dt.to_period("M")
            )
            .sum()
            .sort_values(ascending=False)
        )

        if not month_totals.empty:

            insight_lines.append(
                f"📅 **{month_totals.index[0]}** was the best month "
                "for revenue."
            )

    if total_orders and total_customers and total_customers > 0:

        orders_per_customer = total_orders / total_customers

        if orders_per_customer > 1:

            insight_lines.append(
                f"🔁 Customers order about **{orders_per_customer:.1f}x** "
                "on average — repeat business is a meaningful part of sales."
            )

    if insight_lines:

        st.subheader("💡 Key Insights")

        for line in insight_lines:
            st.markdown(f"- {line}")

        st.markdown("---")

    # -------------------------------------------------
    # REVENUE TREND
    # -------------------------------------------------

    st.subheader("📅 Revenue Trend")

    if has_revenue and columns["date"]:

        trend_data = data[[columns["date"]]].copy()
        trend_data["_revenue"] = revenue_series

        trend_data["_period"] = (
            pd.to_datetime(trend_data[columns["date"]], errors="coerce")
            .dt.to_period("M")
            .astype(str)
        )

        trend = (
            trend_data
            .dropna(subset=["_period"])
            .groupby("_period")["_revenue"]
            .sum()
        )

        st.line_chart(trend)

    else:

        st.info(
            "No date column (and/or no revenue) detected — "
            "revenue trend unavailable for this dataset."
        )

    st.markdown("---")

    # -------------------------------------------------
    # TOP PRODUCTS
    # -------------------------------------------------

    top_products = None

    if has_revenue and columns["product"]:

        st.subheader("🏆 Top 10 Products by Revenue")

        product_data = data[[columns["product"]]].copy()
        product_data["_revenue"] = revenue_series

        top_products = (
            product_data
            .groupby(columns["product"])["_revenue"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        st.bar_chart(top_products)

    elif columns["product"] and columns["quantity"]:

        st.subheader("🏆 Top 10 Products by Quantity")

        top_products = (
            data
            .groupby(columns["product"])[columns["quantity"]]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        st.bar_chart(top_products)

    st.markdown("---")

    # -------------------------------------------------
    # REVENUE BY COUNTRY (funnel, matches the Power BI page)
    # -------------------------------------------------

    country_totals_display = None
    country_value_label = None

    if columns["country"]:

        st.subheader("🌍 By Country")

        if has_revenue:

            country_data = data[[columns["country"]]].copy()
            country_data["_revenue"] = revenue_series

            country_totals_display = (
                country_data
                .groupby(columns["country"])["_revenue"]
                .sum()
                .sort_values(ascending=False)
                .head(10)
            )

            country_value_label = "Revenue by Country"

        else:

            country_totals_display = (
                data[columns["country"]]
                .value_counts()
                .head(10)
            )

            country_value_label = "Orders by Country"

        render_funnel_chart(country_totals_display, country_value_label)

    # -------------------------------------------------
    # NEW: DOWNLOAD SALES SUMMARY — a friendly, self-contained
    # takeaway a non-technical user can save or forward, instead of
    # having to screenshot charts.
    # -------------------------------------------------

    summary_frames = []

    if top_products is not None:

        summary_frames.append(
            top_products
            .rename("Value")
            .reset_index()
            .rename(columns={top_products.index.name or "index": "Top Products"})
            .assign(Metric="Top 10 Products")
        )

    if country_totals_display is not None:

        summary_frames.append(
            country_totals_display
            .rename("Value")
            .reset_index()
            .rename(columns={country_totals_display.index.name or "index": "Top Products"})
            .assign(Metric=country_value_label)
        )

    if summary_frames:

        st.markdown("---")

        summary_csv = (
            pd.concat(summary_frames, ignore_index=True)
            [["Metric", "Top Products", "Value"]]
            .to_csv(index=False)
            .encode("utf-8")
        )

        st.download_button(
            "⬇️ Download Sales Summary (CSV)",
            data=summary_csv,
            file_name="Sales_Summary.csv",
            mime="text/csv",
            use_container_width=True,
            key="sales_overview_summary_download"
        )
