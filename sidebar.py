"""Sidebar navigation: the Simple/Advanced mode toggle, page selector,
and the pipeline-progress checklist."""
import streamlit as st


def render_sidebar():
    st.sidebar.title("🛒 Market Basket")

    st.sidebar.markdown("---")

    advanced_mode = st.sidebar.toggle(
        "🔧 Advanced / Developer View",
        value=False,
        key="advanced_mode",
        help=(
            "Off: just upload a file and get recommendations. "
            "On: step through every technical stage of the pipeline."
        )
    )

    st.sidebar.markdown("---")

    if advanced_mode:

        page = st.sidebar.radio(
            "📂 Navigation",
            [
                "🏠 Home",
                "📈 Sales Overview",
                "📂 Data Preparation",
                "📈 EDA",
                "🔄 Data Transformation",
                "🧠 Apriori Algorithm",
                "📑 Association Rules",
                "🛍 Product Recommendation",
                "🎁 Bundle Creation",
                "🕒 Time-Aware Recommendations",
                "📊 Dashboard",
                "🕘 History"
            ]
        )

    else:

        page = st.sidebar.radio(
            "📂 Navigation", 
            [
                "🚀 Get Recommendations",
                "🕒 Best Time to Sell",
                "📈 Sales Overview",
                "🎁 Bundle Creation",
                "🕘 History"
            ]
        )

    st.sidebar.markdown("---")

    st.sidebar.info(
        """
        **Market Basket Analysis**

        Cross-Sell Engine
        """
    )

    if advanced_mode:

        st.sidebar.markdown("---")

        st.sidebar.markdown("#### 🚦 Pipeline Progress")

        pipeline_steps = [
            ("Data Loaded", st.session_state.data is not None),
            ("Basket Created", st.session_state.basket_df is not None),
            ("Itemsets Found", st.session_state.frequent_itemsets is not None),
            ("Rules Generated", st.session_state.rules_df is not None),
        ]

        for step_label, is_done in pipeline_steps:

            icon = "✅" if is_done else "⬜"

            st.sidebar.markdown(f"{icon} {step_label}")


    return page
