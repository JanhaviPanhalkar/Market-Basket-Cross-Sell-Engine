"""CSS theme injected once at startup. Colors/layout only — no logic here.

Design tokens:
  Ink      #1E1B2E  headings / high-emphasis text
  Primary  #5B21B6  deep violet — buttons, active accents, left-border detail
  Sidebar  #2E1065  solid deep indigo-violet (not a gradient)
  Success  #047857  download / export actions
  Border   #E4E1EC  neutral hairline border
  Surface  #FFFFFF  card / panel background
  Type     Inter — one family, weight does the differentiating
"""
import streamlit as st


def inject_theme():

    st.markdown(
        """
        <style>

        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, .stApp, [data-testid="stAppViewContainer"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                'Segoe UI', sans-serif;
        }

        /* Page background */
        .stApp {
            background: #fbfafd;
        }

        /* Sidebar — solid, not a gradient */
        [data-testid="stSidebar"] {
            background: #2e1065;
        }
        [data-testid="stSidebar"] * {
            color: #ece9f7 !important;
            font-family: 'Inter', sans-serif;
        }
        [data-testid="stSidebar"] .stRadio > div {
            gap: 0.25rem;
        }
        [data-testid="stSidebar"] .stRadio label {
            background: rgba(255,255,255,0.06);
            border-radius: 6px;
            padding: 6px 10px;
            transition: background 0.15s ease;
        }
        [data-testid="stSidebar"] .stRadio label:hover {
            background: rgba(255,255,255,0.14);
        }

        /* Headings — solid ink, weight carries the hierarchy, no gradient-text */
        h1 {
            color: #1e1b2e;
            font-weight: 800;
            letter-spacing: -0.02em;
            border-bottom: 3px solid #5b21b6;
            padding-bottom: 0.35rem;
            display: inline-block;
        }
        h2, h3 {
            color: #1e1b2e;
            font-weight: 700;
        }

        /* Metric cards */
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e4e1ec;
            border-left: 4px solid #5b21b6;
            border-radius: 8px;
            padding: 12px 14px;
            box-shadow: 0 1px 3px rgba(30,27,46,0.06);
        }
        [data-testid="stMetricLabel"] {
            color: #5b21b6;
            font-weight: 600;
        }

        /* Recommendation cards (Top 3 medals, etc.) */
        .metric-card {
            border: 1px solid #e4e1ec;
            border-left: 4px solid #5b21b6;
            border-radius: 8px;
            padding: 15px;
            background-color: #ffffff;
            text-align: center;
            box-shadow: 0 1px 3px rgba(30,27,46,0.06);
            margin-bottom: 1rem;
        }
        .metric-card h3 {
            margin: 0;
            font-size: 1.15rem;
            font-weight: 700;
            color: #1e1b2e;
        }
        .metric-card p {
            margin: 5px 0 0 0;
            color: #4b4560;
        }

        /* Primary buttons — solid, not gradient; subtle hover, no lift */
        .stButton > button {
            background: #5b21b6;
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            transition: background 0.15s ease, box-shadow 0.15s ease;
        }
        .stButton > button:hover {
            background: #4c1d95;
            box-shadow: 0 2px 8px rgba(91,33,182,0.25);
        }

        /* Download buttons — solid emerald, same shape language as primary */
        .stDownloadButton > button {
            background: #047857;
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            transition: background 0.15s ease;
        }
        .stDownloadButton > button:hover {
            background: #036c4e;
        }

        /* Alerts */
        [data-testid="stAlert"] {
            border-radius: 8px;
        }

        /* Section dividers — a plain hairline, not a rainbow bar */
        hr {
            border: none;
            height: 1px;
            background: #e4e1ec;
        }

        /* Dataframes */
        [data-testid="stDataFrame"] {
            border-radius: 8px;
            overflow: hidden;
        }

        /* Visible keyboard focus, for accessibility */
        .stButton > button:focus-visible,
        .stDownloadButton > button:focus-visible {
            outline: 2px solid #5b21b6;
            outline-offset: 2px;
        }

        /* Time picker (Best Time to Sell — custom range) */
        [data-testid="stTimeInput"] > div {
            border-radius: 8px;
        }
        [data-testid="stTimeInput"] input {
            font-weight: 600;
            color: #1e1b2e;
            border-radius: 8px !important;
        }
        [data-testid="stTimeInput"]:focus-within > div {
            box-shadow: 0 0 0 1px #5b21b6;
            border-color: #5b21b6 !important;
        }

        /* Bordered containers (e.g. the custom time-window card) —
           echo the metric-card language instead of Streamlit's default */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 10px !important;
            border-color: #e4e1ec !important;
            box-shadow: 0 1px 3px rgba(30,27,46,0.05);
        }

        </style>
        """,
        unsafe_allow_html=True
    )


