"""Punto de entrada del dashboard y configuración de la navegación visible."""

import streamlit as st


pagina = st.navigation(
    [
        st.Page(
            "pages/0_Contexto_Macro.py",
            title="Contexto macro",
            default=True,
        ),
        st.Page(
            "pages/1_Universo_Colegios.py",
            title="Universo de Colegios",
        ),
        st.Page(
            "pages/2_Captacion_UDLA.py",
            title="Captación UDLA",
        ),
        st.Page(
            "pages/3_Mercado_Alertas.py",
            title="Mercado Alertas",
        ),
        st.Page(
            "pages/4_Concentracion_Colegios.py",
            title="Concentración por colegio",
        ),
    ]
)

pagina.run()
