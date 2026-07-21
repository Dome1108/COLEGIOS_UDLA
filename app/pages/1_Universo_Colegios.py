"""Universo de colegios con oferta de Bachillerato (MINEDUC/MINEDEC) y su
captación hacia UDLA — inspirado en el dashboard de Datos Abiertos del
Ministerio de Educación."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import cargar_pension_mineduc, cargar_universo_colegios
from utils.theme import COLOR_PRIMARIO, COLOR_SECUNDARIO, inject_css

st.set_page_config(page_title="Universo de Colegios", layout="wide")
inject_css()

COLOR_TERCIARIO = "#5D9BD5"
COLOR_ALERTA = "#B0745A"

st.title("Universo de Colegios con Bachillerato — Ecuador")
st.caption(
    "Fuente: Registros Administrativos MINEDUC/MINEDEC, periodos 2009-2010 a 2024-2025 Fin. "
    "Incluye instituciones cuyo Nivel de Educación ofrece Bachillerato en alguna combinación."
)

universo = cargar_universo_colegios()

# --- Filtros (selección múltiple; vacío = sin filtrar / todas las opciones) ---
fila1 = st.columns(4)
fila2 = st.columns(4)

with fila1[0]:
    periodos = sorted(universo["periodo"].unique())
    periodos_sel = st.multiselect("Periodo (para KPIs)", periodos, default=[periodos[-1]])
with fila1[1]:
    tipos = sorted(universo["tipo_educacion"].dropna().unique().tolist())
    tipo_sel = st.multiselect("Tipo de educación", tipos)
with fila1[2]:
    zonas = sorted(universo["zona"].dropna().unique().tolist())
    zona_sel = st.multiselect("Zona de planificación", zonas)
with fila1[3]:
    provincias = sorted(universo["provincia"].dropna().unique().tolist())
    provincia_sel = st.multiselect("Provincia", provincias)

with fila2[0]:
    universo_canton = universo if not provincia_sel else universo[universo["provincia"].isin(provincia_sel)]
    cantones = sorted(universo_canton["canton"].dropna().unique().tolist())
    canton_sel = st.multiselect("Cantón", cantones)
with fila2[1]:
    universo_parroquia = universo_canton if not canton_sel else universo_canton[universo_canton["canton"].isin(canton_sel)]
    parroquias = sorted(universo_parroquia["parroquia"].dropna().unique().tolist())
    parroquia_sel = st.multiselect("Parroquia", parroquias)
with fila2[2]:
    areas = sorted(universo["area"].dropna().unique().tolist())
    area_sel = st.multiselect("Urbano/Rural", areas)
with fila2[3]:
    sostenimientos = sorted(universo["sostenimiento"].dropna().unique().tolist())
    sostenimiento_sel = st.multiselect("Sostenimiento", sostenimientos)

fila3 = st.columns(2)
with fila3[0]:
    jurisdicciones = sorted(universo["jurisdiccion"].dropna().unique().tolist())
    jurisdiccion_sel = st.multiselect("Intercultural/Intercultural bilingüe", jurisdicciones)
with fila3[1]:
    regimenes = sorted(universo["regimen_escolar"].dropna().unique().tolist())
    regimen_sel = st.multiselect("Régimen escolar", regimenes)

filtrado = universo.copy()
for col, sel in [
    ("tipo_educacion", tipo_sel), ("zona", zona_sel), ("provincia", provincia_sel),
    ("canton", canton_sel), ("parroquia", parroquia_sel), ("area", area_sel),
    ("sostenimiento", sostenimiento_sel), ("jurisdiccion", jurisdiccion_sel),
    ("regimen_escolar", regimen_sel),
]:
    if sel:
        filtrado = filtrado[filtrado[col].isin(sel)]

if filtrado.empty:
    st.warning("No hay instituciones que cumplan estos filtros.")
    st.stop()

if not periodos_sel:
    etiqueta_periodo = "todos los periodos"
    filtrado_periodo = filtrado
elif len(periodos_sel) == 1:
    etiqueta_periodo = periodos_sel[0]
    filtrado_periodo = filtrado[filtrado["periodo"].isin(periodos_sel)]
else:
    etiqueta_periodo = f"{len(periodos_sel)} periodos seleccionados (sumado)"
    filtrado_periodo = filtrado[filtrado["periodo"].isin(periodos_sel)]

# --- KPIs (snapshot del periodo seleccionado) ---
st.subheader(f"Datos globales — {etiqueta_periodo}")
if not periodos_sel or len(periodos_sel) > 1:
    st.caption("Con varios periodos (o ninguno) seleccionados, los KPIs suman entre periodos — no es una fotografía de un solo momento.")
estudiantes_3bach_m = filtrado_periodo["estudiantes_3bach_mujeres"].sum()
estudiantes_3bach_h = filtrado_periodo["estudiantes_3bach_hombres"].sum()
kpi = st.columns(4)
kpi[0].metric("Instituciones educativas (IE)", f"{filtrado_periodo['AMIE'].nunique():,.0f}")
kpi[1].metric("Estudiantes 3er Bach — Mujeres", f"{estudiantes_3bach_m:,.0f}")
kpi[2].metric("Estudiantes 3er Bach — Hombres", f"{estudiantes_3bach_h:,.0f}")
kpi[3].metric("Estudiantes 3er Bach — Total", f"{estudiantes_3bach_m + estudiantes_3bach_h:,.0f}")

# --- Tendencias historicas (todos los periodos, con el resto de filtros aplicados) ---
por_periodo = (
    filtrado.groupby("periodo")
    .agg(
        n_instituciones=("AMIE", "nunique"),
        estudiantes_3bach_mujeres=("estudiantes_3bach_mujeres", "sum"),
        estudiantes_3bach_hombres=("estudiantes_3bach_hombres", "sum"),
        promovidos=("total_promovidos", "sum"),
        no_promovidos=("total_no_promovidos", "sum"),
        abandono=("total_abandono", "sum"),
    )
    .reset_index()
    .sort_values("periodo")
)
por_periodo["estudiantes"] = por_periodo["estudiantes_3bach_mujeres"] + por_periodo["estudiantes_3bach_hombres"]
denominador = por_periodo["promovidos"] + por_periodo["no_promovidos"] + por_periodo["abandono"]
por_periodo["tasa_promocion"] = (por_periodo["promovidos"] / denominador * 100).round(2)
por_periodo["tasa_no_promocion"] = (por_periodo["no_promovidos"] / denominador * 100).round(2)
por_periodo["tasa_abandono"] = (por_periodo["abandono"] / denominador * 100).round(2)

st.subheader("Tendencias históricas")

col_izq, col_der = st.columns(2)

with col_izq:
    fig_matricula = go.Figure(
        go.Scatter(
            x=por_periodo["periodo"], y=por_periodo["estudiantes"],
            mode="lines+markers",
            line=dict(color=COLOR_PRIMARIO, width=2),
            marker=dict(size=7, color=COLOR_PRIMARIO, line=dict(width=2, color="white")),
        )
    )
    fig_matricula.update_layout(
        template="plotly_white", title="Estudiantes 3er año Bachillerato matriculados",
        hovermode="x unified", showlegend=False, margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig_matricula, width="stretch")

with col_der:
    fig_ie = go.Figure(
        go.Scatter(
            x=por_periodo["periodo"], y=por_periodo["n_instituciones"],
            mode="lines+markers",
            line=dict(color=COLOR_TERCIARIO, width=2),
            marker=dict(size=7, color=COLOR_TERCIARIO, line=dict(width=2, color="white")),
        )
    )
    fig_ie.update_layout(
        template="plotly_white", title="Instituciones educativas",
        hovermode="x unified", showlegend=False, margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig_ie, width="stretch")

fig_tasas = go.Figure()
for nombre, col, color in [
    ("Tasa de promoción", "tasa_promocion", COLOR_PRIMARIO),
    ("Tasa de no promoción", "tasa_no_promocion", COLOR_TERCIARIO),
    ("Tasa de abandono", "tasa_abandono", COLOR_ALERTA),
]:
    fig_tasas.add_trace(
        go.Scatter(
            x=por_periodo["periodo"], y=por_periodo[col], mode="lines+markers", name=nombre,
            line=dict(width=2, color=color),
            marker=dict(size=7, color=color, line=dict(width=2, color="white")),
        )
    )
fig_tasas.update_layout(
    template="plotly_white", title="Tasas de promoción / no promoción / abandono",
    yaxis_title="%", hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(l=10, r=10, t=60, b=10),
)
st.plotly_chart(fig_tasas, width="stretch")

st.caption(
    "Tasas calculadas sobre el total de estudiantes con desenlace conocido "
    "(promovido + no promovido + abandono) de todas las instituciones y periodos que cumplen los filtros de arriba."
)

# --- Pensiones (Bachillerato) -- Ministerio, snapshot mayo 2026 ---
st.subheader("Pensiones (Bachillerato) — Ministerio")
st.caption(
    "Fuente: `matricula-pension-mayo-2026.xlsx` (Ministerio, snapshot único — no varía por periodo), "
    "cruzado por AMIE con las instituciones del filtro actual. Colegios fiscales/gratuitos quedan en 0 o sin dato."
)

pension = cargar_pension_mineduc()
amies_filtrados = set(filtrado_periodo["AMIE"].unique())
pension_filtrado = pension[pension["AMIE"].isin(amies_filtrados) & (pension["pension_bachillerato"] > 0)]

if pension_filtrado.empty:
    st.info("Ninguna institución de este filtro tiene pensión de Bachillerato registrada (> 0).")
else:
    kpi_pension = st.columns(2)
    kpi_pension[0].metric("Pensión Bachillerato — promedio", f"${pension_filtrado['pension_bachillerato'].mean():,.2f}")
    kpi_pension[1].metric("Matrícula Bachillerato — promedio", f"${pension_filtrado['matricula_bachillerato'].mean():,.2f}")

    tabla_pension = pension_filtrado.merge(
        filtrado_periodo[["AMIE", "nombre_institucion", "provincia", "canton"]].drop_duplicates("AMIE"),
        on="AMIE", how="left",
    )[["nombre_institucion", "provincia", "canton", "AMIE", "matricula_bachillerato", "pension_bachillerato"]]
    tabla_pension = tabla_pension.sort_values("pension_bachillerato", ascending=False)
    st.dataframe(tabla_pension, width="stretch", height=350)
