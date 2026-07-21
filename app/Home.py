"""Página de bienvenida — resumen de qué contiene cada página del dashboard."""
import streamlit as st

from utils.theme import inject_css

st.set_page_config(page_title="Captación UDLA — Colegios", layout="wide")
inject_css()

st.title("Captación universitaria de bachilleres — UDLA")
st.caption("Dashboard local (no publicado). Usa el menú de la izquierda para navegar.")

st.markdown(
    """
### Páginas disponibles

**Universo de Colegios** — universo nacional de instituciones con oferta de
Bachillerato (MINEDUC/MINEDEC), con filtros de ubicación/sostenimiento/régimen
y tendencias de matrícula, instituciones y tasas de promoción/no
promoción/abandono.

**Captación UDLA** — funnel Graduados → Leads → Afluentes → Documentados por
colegio de origen (fuente: `DwhStage..DocumentadosColegiosMINEDU`), con % de
captación sobre graduados y tabla de pensiones/colegiatura.

**Mercado Alertas** — cuadrante que compara, por colegio, si su mercado de
graduados creció o cayó vs. si la captación de UDLA ahí creció o cayó,
con vista de tabla y alertas para los casos en caída en ambos frentes.
"""
)
