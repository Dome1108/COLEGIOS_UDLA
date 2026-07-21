"""Funnel de captación UDLA (Graduados -> Leads -> Afluentes -> Documentados)
cruzado con los colegios de origen, desde DwhStage..DocumentadosColegiosMINEDU."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import cargar_documentados_detalle, cargar_documentados_resumen
from utils.theme import COLOR_PRIMARIO, COLOR_SECUNDARIO, inject_css

st.set_page_config(page_title="Captación UDLA", layout="wide")
inject_css()

COLOR_TERCIARIO = "#5D9BD5"
COLOR_ALERTA = "#B0745A"
COLOR_EXITO = "#4C8C6B"

st.title("Captación UDLA — Funnel por colegio de origen")
st.caption(
    "Fuente: DwhStage..DocumentadosColegiosMINEDU (autenticación Windows). "
    "codigo_colegio = CodColegioBanner_Sales, y si no hay dato, CodColegioAMIED."
)

resumen = cargar_documentados_resumen()
detalle = cargar_documentados_detalle()
detalle["codigo_colegio"] = detalle["CodColegioBanner_Sales"].fillna(detalle["CodColegioAMIED"])

# --- Filtros (selección múltiple; vacío = sin filtrar / todas las opciones) ---
cols_filtro = st.columns([2, 1.6, 1, 1, 1, 1, 1])
with cols_filtro[0]:
    colegios_nombres = sorted(resumen["nombre_institucion"].dropna().unique().tolist())
    colegio_sel = st.multiselect("Colegio", colegios_nombres)
with cols_filtro[1]:
    periodos_todos = sorted(resumen["PeriodoBanner_Sales"].unique())
    periodos_sel = st.multiselect("Periodo", periodos_todos, default=periodos_todos)
with cols_filtro[2]:
    provincias = sorted(resumen["provincia"].dropna().unique().tolist())
    provincia_sel = st.multiselect("Provincia", provincias)
with cols_filtro[3]:
    resumen_canton = resumen if not provincia_sel else resumen[resumen["provincia"].isin(provincia_sel)]
    cantones = sorted(resumen_canton["canton"].dropna().unique().tolist())
    canton_sel = st.multiselect("Cantón", cantones)
with cols_filtro[4]:
    sostenimientos = sorted(resumen["sostenimiento"].dropna().unique().tolist())
    sostenimiento_sel = st.multiselect("Sostenimiento", sostenimientos)
with cols_filtro[5]:
    clusters = sorted(resumen["cluster"].dropna().unique().tolist())
    cluster_sel = st.multiselect("Cluster", clusters)
with cols_filtro[6]:
    rangos_pension = sorted(resumen["rango_pension"].dropna().unique().tolist())
    rango_pension_sel = st.multiselect("Rango pensión", rangos_pension)


def _filtro_periodo(df):
    """Vacío en el multiselect de Periodo = sin filtrar (todos los periodos)."""
    return df if not periodos_sel else df[df["PeriodoBanner_Sales"].isin(periodos_sel)]


filtrado = _filtro_periodo(resumen)
for col, sel in [
    ("nombre_institucion", colegio_sel),
    ("provincia", provincia_sel), ("canton", canton_sel),
    ("sostenimiento", sostenimiento_sel), ("cluster", cluster_sel),
    ("rango_pension", rango_pension_sel),
]:
    if sel:
        filtrado = filtrado[filtrado[col].isin(sel)]

if filtrado.empty:
    st.warning("No hay datos que cumplan estos filtros.")
    st.stop()

colegio_unico = filtrado["codigo_colegio"].nunique() == 1

# --- Cobertura: Leads/Afluentes/Documentados con colegio identificado vs. sin ninguno ---
# Solo respeta el filtro de Periodo (no los de Colegio/Provincia/etc., ya que
# los registros sin codigo_colegio no tienen esos atributos y no se pueden
# ubicar en ningun grafico por colegio -- ver documentados_colegios_detalle.parquet).
resumen_periodo = _filtro_periodo(resumen)
detalle_sin_colegio = _filtro_periodo(detalle[detalle["codigo_colegio"].isna()])
grp_sin_colegio = detalle_sin_colegio.groupby(["PeriodoBanner_Sales", "CodBanner"], dropna=False)[["L", "A", "D"]].first()

tabla_cobertura = pd.DataFrame({
    "Etapa": ["Leads", "Afluentes", "Documentados"],
    "Con colegio identificado": [
        resumen_periodo["leads"].sum(), resumen_periodo["afluentes"].sum(), resumen_periodo["documentados_d"].sum(),
    ],
    "Sin colegio identificado (null)": [
        grp_sin_colegio["L"].sum(), grp_sin_colegio["A"].sum(), grp_sin_colegio["D"].sum(),
    ],
})
tabla_cobertura["Total nacional"] = tabla_cobertura["Con colegio identificado"] + tabla_cobertura["Sin colegio identificado (null)"]
tabla_cobertura["% sin colegio"] = (
    tabla_cobertura["Sin colegio identificado (null)"] / tabla_cobertura["Total nacional"] * 100
).round(1)

st.subheader("Cobertura de identificación de colegio")
st.caption(
    "Refleja solo el filtro de Periodo (no Colegio/Provincia/etc., ya que los registros sin colegio "
    "no tienen esos atributos). Un registro sin `CodColegioBanner_Sales` ni `CodColegioAMIED` no se puede "
    "ubicar en ningún gráfico por colegio y queda fuera del resto de esta página."
)
st.dataframe(
    tabla_cobertura.style.format({
        "Con colegio identificado": "{:,.0f}", "Sin colegio identificado (null)": "{:,.0f}",
        "Total nacional": "{:,.0f}", "% sin colegio": "{:.1f}%",
    }),
    width="stretch", hide_index=True,
)

# --- Funnel por periodo ---
# "documentados" usa el campo D (funnel L-A-D, corregido para sumar entre
# CodBanner -- ver etl/build_documentados_colegios.py). TotalDocumentadosPeriodo
# es un campo aparte, no forma parte de esta secuencia L->A->D.
por_periodo = (
    filtrado.groupby("PeriodoBanner_Sales")
    .agg(
        graduados=("graduados_total", "sum"),
        leads=("leads", "sum"),
        afluentes=("afluentes", "sum"),
        documentados=("documentados_d", "sum"),
    )
    .reset_index()
    .sort_values("PeriodoBanner_Sales")
)
por_periodo["tasa_leads"] = (por_periodo["leads"] / por_periodo["graduados"] * 100).round(1)
por_periodo["tasa_afluentes"] = (por_periodo["afluentes"] / por_periodo["graduados"] * 100).round(1)
por_periodo["tasa_documentados"] = (por_periodo["documentados"] / por_periodo["graduados"] * 100).round(1)

st.subheader("Funnel en el tiempo: Graduados → Leads → Afluentes → Documentados")

# Valor de pensión para el hover -- solo aplica si el filtro quedo en UN colegio
# y ese colegio tiene un valor de pension registrado; si no, no se muestra nada.
pension_valor = None
if colegio_unico:
    detalle_colegio = _filtro_periodo(detalle[detalle["codigo_colegio"].isin(filtrado["codigo_colegio"].unique())])
    pension_serie = pd.to_numeric(detalle_colegio["BACHILLERATO PENSIÓN"], errors="coerce").dropna()
    if not pension_serie.empty:
        pension_valor = pension_serie.iloc[0]
sufijo_pension = f"<br>Pensión: ${pension_valor:,.2f}" if pension_valor is not None else ""

fig_funnel = go.Figure()
fig_funnel.add_trace(
    go.Scatter(
        x=por_periodo["PeriodoBanner_Sales"], y=por_periodo["graduados"], mode="lines+markers", name="Graduados",
        line=dict(width=2, color=COLOR_SECUNDARIO),
        marker=dict(size=7, color=COLOR_SECUNDARIO, line=dict(width=2, color="white")),
        customdata=por_periodo[["graduados"]],
        hovertemplate="Graduados: %{y:,.0f}<extra></extra>",
    )
)
for nombre, col_valor, col_tasa, color in [
    ("Leads", "leads", "tasa_leads", COLOR_TERCIARIO),
    ("Afluentes", "afluentes", "tasa_afluentes", COLOR_PRIMARIO),
    ("Documentados", "documentados", "tasa_documentados", COLOR_ALERTA),
]:
    sufijo = sufijo_pension if nombre == "Documentados" else ""
    fig_funnel.add_trace(
        go.Scatter(
            x=por_periodo["PeriodoBanner_Sales"], y=por_periodo[col_valor], mode="lines+markers", name=nombre,
            line=dict(width=2, color=color),
            marker=dict(size=7, color=color, line=dict(width=2, color="white")),
            customdata=por_periodo[[col_tasa]],
            hovertemplate=f"{nombre}: " + "%{y:,.0f} (%{customdata[0]:.1f}% de Graduados)" + sufijo + "<extra></extra>",
        )
    )
fig_funnel.update_layout(
    template="plotly_white", yaxis_type="log", yaxis_title="Personas (escala log)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(l=10, r=10, t=40, b=10),
)
st.plotly_chart(fig_funnel, width="stretch")

if colegio_unico:
    st.info(
        "Filtro reducido a **un solo colegio** — el % de documentados que ves arriba "
        "es exactamente la captación de ESE colegio en cada periodo exacto, sobre sus propios graduados. "
        + ("El valor de pensión de este colegio aparece al final del hover de Documentados." if pension_valor is not None
           else "Este colegio no tiene un valor de pensión registrado.")
    )

# --- Tabla anual (solo periodo 10): valores + % de variación interanual ---
st.subheader("Tabla anual (solo periodo 10)")
st.caption(
    "Compara únicamente el primer ciclo de admisión de cada año (periodos que terminan en \"10\") "
    "para una serie anual limpia, sin el ruido de tener 2 ciclos de admisión por año. "
    "Ordenable por cualquier columna (clic en el encabezado)."
)
filtrado_p10 = filtrado[filtrado["PeriodoBanner_Sales"].str.endswith("10")].copy()
filtrado_p10["anio"] = filtrado_p10["PeriodoBanner_Sales"].str[:4]

if filtrado_p10.empty:
    st.info("No hay datos de periodo 10 para este filtro.")
else:
    por_anio = (
        filtrado_p10.groupby("anio")
        .agg(
            colegios=("codigo_colegio", "nunique"),
            graduados=("graduados_total", "sum"),
            leads=("leads", "sum"),
            afluentes=("afluentes", "sum"),
            documentados=("documentados_d", "sum"),
        )
        .reset_index()
        .sort_values("anio")
    )
    tabla_anual = por_anio[["anio", "colegios", "graduados", "leads", "afluentes", "documentados"]].copy()
    for col in ["graduados", "leads", "afluentes", "documentados"]:
        tabla_anual[f"var_{col}_pct"] = tabla_anual[col].pct_change().mul(100).round(1)
    tabla_anual = tabla_anual.sort_values("anio", ascending=False).rename(columns={
        "anio": "Año", "colegios": "Colegios", "graduados": "Graduados", "leads": "Leads",
        "afluentes": "Afluentes", "documentados": "Documentados",
        "var_graduados_pct": "% var. Graduados", "var_leads_pct": "% var. Leads",
        "var_afluentes_pct": "% var. Afluentes", "var_documentados_pct": "% var. Documentados",
    })[[
        "Año", "Colegios", "Graduados", "% var. Graduados", "Leads", "% var. Leads",
        "Afluentes", "% var. Afluentes", "Documentados", "% var. Documentados",
    ]]
    st.dataframe(
        tabla_anual.style.format({
            "Colegios": "{:,.0f}", "Graduados": "{:,.0f}", "Leads": "{:,.0f}",
            "Afluentes": "{:,.0f}", "Documentados": "{:,.0f}",
            "% var. Graduados": "{:+.1f}%", "% var. Leads": "{:+.1f}%",
            "% var. Afluentes": "{:+.1f}%", "% var. Documentados": "{:+.1f}%",
        }, na_rep="—"),
        width="stretch", hide_index=True,
    )
