"""Inyecta el CSS global del dashboard: tipografía Century Gothic y paleta institucional."""
import streamlit as st

COLOR_PRIMARIO = "#1F4E79"
COLOR_SECUNDARIO = "#8C9BAB"
COLOR_FONDO = "#F2F4F7"


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        @font-face {{
            font-family: 'Century Gothic';
            src: local('Century Gothic'), local('CenturyGothic');
            font-weight: normal;
            font-style: normal;
        }}

        html, body, [class*="css"] {{
            font-family: 'Century Gothic', 'Segoe UI', sans-serif;
        }}

        .stApp {{
            background-color: {COLOR_FONDO};
        }}

        h1, h2, h3, h4, h5, h6 {{
            color: {COLOR_PRIMARIO};
            font-family: 'Century Gothic', 'Segoe UI', sans-serif;
        }}

        [data-testid="stMetric"] {{
            background-color: white;
            border: 1px solid {COLOR_SECUNDARIO};
            border-radius: 8px;
            padding: 1rem;
        }}

        [data-testid="stMetricLabel"] {{
            color: {COLOR_SECUNDARIO};
        }}

        [data-testid="stMetricValue"] {{
            color: {COLOR_PRIMARIO};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
