"""Concentración y variación de leads, afluentes y documentados por colegio."""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data_loader import cargar_documentados_detalle
from utils.theme import COLOR_PRIMARIO, inject_css

st.set_page_config(page_title="Concentración por colegio", layout="wide")
inject_css()

st.title("Concentración por colegio")
st.caption(
    "Compara leads, afluentes y estudiantes documentados en 202610 y 202710 "
    "con el periodo anterior. L y A se deduplican por cuenta Banner; "
    "documentados se cuentan por IdBanner único."
)

detalle = cargar_documentados_detalle()
periodo_col = "PeriodoBanner_Sales"
periodos_requeridos = {"202510", "202610", "202710"}
detalle[periodo_col] = detalle[periodo_col].astype(str).str.strip()
detalle = detalle[detalle[periodo_col].isin(periodos_requeridos)].copy()

banner = detalle["CodColegioBanner_Sales"].astype("string").str.strip()
amie = detalle["CodColegioAMIED"].astype("string").str.strip()
detalle["codigo_colegio"] = banner.mask(banner.eq("ND").fillna(False)).fillna(
    amie.mask(amie.eq("ND").fillna(False))
)
detalle = detalle[detalle["codigo_colegio"].notna()].copy()
detalle["codigo_cuenta"] = detalle["HomologadoCodBannerColegio"].astype("string").fillna("SIN CUENTA")
detalle["colegio"] = detalle["NombreInstitucionAMIED"].fillna(detalle["codigo_colegio"])

# L y A son totales a nivel de cuenta Banner y pueden repetirse en cada estudiante.
por_cuenta = (
    detalle.groupby([periodo_col, "codigo_colegio", "codigo_cuenta"], dropna=False)
    .agg(
        colegio=("colegio", "first"),
        leads=("L", lambda s: pd.to_numeric(s, errors="coerce").max()),
        afluentes=("A", lambda s: pd.to_numeric(s, errors="coerce").max()),
    )
    .reset_index()
)
por_colegio = (
    por_cuenta.groupby([periodo_col, "codigo_colegio"], dropna=False)
    .agg(colegio=("colegio", "first"), leads=("leads", "sum"), afluentes=("afluentes", "sum"))
    .reset_index()
)
documentados = (
    detalle.groupby([periodo_col, "codigo_colegio"], dropna=False)["IdBanner"]
    .nunique().rename("documentados").reset_index()
)
resumen = por_colegio.merge(documentados, on=[periodo_col, "codigo_colegio"], how="outer")
for columna in ["leads", "afluentes", "documentados"]:
    resumen[columna] = resumen[columna].fillna(0)
resumen["colegio"] = resumen["colegio"].fillna(resumen["codigo_colegio"])

if resumen.empty:
    st.warning("No hay registros para los periodos 202510, 202610 y 202710.")
    st.stop()

periodos_disponibles = sorted(resumen[periodo_col].unique())
periodos_objetivo = [p for p in ["202610", "202710"] if p in periodos_disponibles]
if not periodos_objetivo:
    st.warning("La tabla no contiene los periodos 202610 ni 202710.")
    st.stop()

periodo = st.selectbox(
    "Periodo a analizar",
    periodos_objetivo,
    format_func=lambda p: f"{p} (comparado con {'202510' if p == '202610' else '202610'})",
)
periodo_anterior = "202510" if periodo == "202610" else "202610"
metrica = st.selectbox(
    "Indicador",
    ["documentados", "leads", "afluentes"],
    format_func=lambda value: {
        "documentados": "Documentados",
        "leads": "Leads",
        "afluentes": "Afluentes",
    }[value],
    index=0,
)
modo_ranking = st.selectbox(
    "Qué quieres identificar",
    ["Mayor volumen en el periodo", "Mayores pérdidas vs. periodo anterior", "Mayores crecimientos vs. periodo anterior"],
)
top_n = st.slider("Colegios a mostrar", min_value=10, max_value=100, value=25, step=5)

actual = resumen[resumen[periodo_col] == periodo].copy()
anterior = resumen[resumen[periodo_col] == periodo_anterior].set_index("codigo_colegio")
for campo in ["leads", "afluentes", "documentados"]:
    actual[f"{campo}_anterior"] = actual["codigo_colegio"].map(anterior[campo])
    actual[f"cambio_{campo}"] = actual[campo] - actual[f"{campo}_anterior"]
    actual[f"cambio_{campo}_pct"] = (
        actual[f"cambio_{campo}"] / actual[f"{campo}_anterior"].replace(0, np.nan) * 100
    )
    actual[f"participacion_{campo}_pct"] = (
        actual[campo] / actual[campo].sum() * 100 if actual[campo].sum() else 0
    )
actual["conversion_leads_afluentes_pct"] = actual["afluentes"].div(actual["leads"].replace(0, np.nan)) * 100
actual["conversion_afluentes_documentados_pct"] = actual["documentados"].div(actual["afluentes"].replace(0, np.nan)) * 100
actual["variacion"] = actual["cambio_documentados_pct"].map(
    lambda v: "Sin base anterior" if pd.isna(v) else f"{v:+.1f}%"
)

columna_cambio = f"cambio_{metrica}"
if modo_ranking == "Mayores pérdidas vs. periodo anterior":
    datos_ranking = actual[actual[columna_cambio] < 0].copy()
    ranking = datos_ranking.sort_values(columna_cambio, ascending=True).head(top_n).copy()
    valor_grafico = columna_cambio
    titulo_ranking = f"Mayores pérdidas de {metrica} por colegio: {periodo_anterior} → {periodo}"
elif modo_ranking == "Mayores crecimientos vs. periodo anterior":
    datos_ranking = actual[actual[columna_cambio] > 0].copy()
    ranking = datos_ranking.sort_values(columna_cambio, ascending=False).head(top_n).copy()
    valor_grafico = columna_cambio
    titulo_ranking = f"Mayores crecimientos de {metrica} por colegio: {periodo_anterior} → {periodo}"
else:
    ranking = actual.sort_values(metrica, ascending=False).head(top_n).copy()
    valor_grafico = metrica
    titulo_ranking = f"Top {len(ranking)} colegios por {metrica} en {periodo}"

if ranking.empty:
    st.info(f"No hay colegios con {modo_ranking.lower()} para {metrica} en este periodo.")
    st.stop()

total_cols = st.columns(3)
for col, campo, label in zip(total_cols, ["leads", "afluentes", "documentados"], ["Leads", "Afluentes", "Documentados"]):
    col.metric(label, f"{actual[campo].sum():,.0f}")

fig = px.bar(
    ranking.sort_values(valor_grafico), x=valor_grafico, y="colegio", orientation="h",
    title=titulo_ranking,
    labels={valor_grafico: "Cambio vs. periodo anterior" if valor_grafico == columna_cambio else metrica.capitalize(), "colegio": "Colegio"},
    color=valor_grafico,
    color_continuous_scale="RdYlGn" if modo_ranking == "Mayores pérdidas vs. periodo anterior" else "Blues",
)
fig.update_layout(
    height=max(450, 24 * len(ranking)), yaxis_title="",
    xaxis_title="Cambio vs. periodo anterior" if valor_grafico == columna_cambio else metrica.capitalize(),
    coloraxis_showscale=False,
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Comparación por colegio")
st.caption(
    f"Participación calculada sobre el total identificable del periodo {periodo}. "
    f"El ranking muestra: {modo_ranking.lower()} para {metrica}. "
    "Las conversiones son afluentes/leads y documentados/afluentes. "
    "Si no existe valor previo, la variación porcentual se muestra vacía."
)
columnas = [
    "colegio", "codigo_colegio",
    "leads", "leads_anterior", "cambio_leads", "cambio_leads_pct", "participacion_leads_pct",
    "afluentes", "afluentes_anterior", "cambio_afluentes", "cambio_afluentes_pct", "participacion_afluentes_pct",
    "documentados", "documentados_anterior", "cambio_documentados", "cambio_documentados_pct", "participacion_documentados_pct",
    "conversion_leads_afluentes_pct", "conversion_afluentes_documentados_pct",
]
tabla = ranking[columnas].rename(columns={
    "colegio": "Colegio", "codigo_colegio": "Código",
    "leads": "Leads", "leads_anterior": "Leads periodo anterior", "cambio_leads": "Cambio leads", "cambio_leads_pct": "% cambio leads", "participacion_leads_pct": "% leads del periodo",
    "afluentes": "Afluentes", "afluentes_anterior": "Afluentes periodo anterior", "cambio_afluentes": "Cambio afluentes", "cambio_afluentes_pct": "% cambio afluentes", "participacion_afluentes_pct": "% afluentes del periodo",
    "documentados": "Documentados", "documentados_anterior": "Documentados periodo anterior", "cambio_documentados": "Cambio documentados", "cambio_documentados_pct": "% cambio documentados", "participacion_documentados_pct": "% documentados del periodo",
    "conversion_leads_afluentes_pct": "% leads a afluentes", "conversion_afluentes_documentados_pct": "% afluentes a documentados",
})
st.dataframe(
    tabla.style.format({c: "{:,.1f}%" for c in tabla.columns if c.startswith("%")}, na_rep="—")
    .format({c: "{:,.0f}" for c in tabla.columns if c in {
        "Leads", "Leads periodo anterior", "Cambio leads", "Afluentes", "Afluentes periodo anterior", "Cambio afluentes",
        "Documentados", "Documentados periodo anterior", "Cambio documentados",
    }}, na_rep="—"),
    use_container_width=True, hide_index=True,
)

with st.expander("Cómo se calculan los indicadores"):
    st.markdown(
        "- **Leads y afluentes:** máximo por periodo, colegio y cuenta Banner para no volver a sumar el mismo total repetido en filas de estudiantes; luego se suman las cuentas del colegio.\n"
        "- **Documentados:** cantidad de `IdBanner` únicos por periodo y colegio.\n"
        "- **Variación:** periodo seleccionado menos periodo anterior; el porcentaje divide el cambio para el valor anterior.\n"
        "- **Sin colegio identificable:** se excluye del ranking porque no se puede atribuir a una institución."
    )
