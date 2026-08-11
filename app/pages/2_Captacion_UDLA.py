"""Funnel de captación UDLA (Graduados -> Leads -> Afluentes -> Documentados)
cruzado con los colegios de origen, desde DwhStage..DocumentadosColegiosMINEDU."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import cargar_documentados_detalle, cargar_documentados_resumen
from utils.theme import COLOR_PRIMARIO, COLOR_SECUNDARIO, inject_css

st.set_page_config(page_title="Captación UDLA", layout="wide")
inject_css()

COLOR_TERCIARIO = "#5D9BD5"
# Bucket con el que el ETL agrega los registros que no se pudieron atribuir a
# ningun colegio (ver etl/build_documentados_colegios.py).
CODIGO_SIN_COLEGIO = "ND"
COLOR_ALERTA = "#B0745A"
COLOR_EXITO = "#4C8C6B"

st.title("Captación UDLA — Funnel por colegio de origen")
st.caption(
    "Fuente: DwhStage..DocumentadosColegiosMINEDU (autenticación Windows). "
    "codigo_colegio = CodColegioBanner_Sales, y si no hay dato, CodColegioAMIED."
)


######################################
## CARGA DE DATOS
######################################
resumen = cargar_documentados_resumen()
detalle = cargar_documentados_detalle()
# Mismo criterio que etl/build_documentados_colegios.py: el centinela "ND"
# ("SIN INFORMACION DE COLEGIO") cuenta como sin colegio, no como un codigo mas.
detalle["codigo_colegio"] = (
    detalle["CodColegioBanner_Sales"]
    .mask(detalle["CodColegioBanner_Sales"] == CODIGO_SIN_COLEGIO)
    .fillna(detalle["CodColegioAMIED"].mask(detalle["CodColegioAMIED"] == CODIGO_SIN_COLEGIO))
)

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

#################################
## TABLA COBERTURA DE IDENTIFICACIÓN COLEGIO
#################################

# --- Cobertura: Leads/Afluentes/Documentados con colegio identificado vs. sin ninguno ---
# Solo respeta el filtro de Periodo (no los de Colegio/Provincia/etc., ya que
# los registros sin codigo_colegio no tienen esos atributos y no se pueden
# ubicar en ningun grafico por colegio).
# El resumen ya trae los registros sin colegio agregados en el bucket
# CODIGO_SIN_COLEGIO (una fila por periodo), asi que la cobertura sale de ahi
# y no hay que recalcularla desde el detalle.
resumen_periodo = _filtro_periodo(resumen)
es_bucket = resumen_periodo["codigo_colegio"] == CODIGO_SIN_COLEGIO
con_colegio = resumen_periodo[~es_bucket]
sin_colegio = resumen_periodo[es_bucket]

ETAPAS = [("Leads", "leads"), ("Afluentes", "afluentes"), ("Documentados", "documentados")]
tabla_cobertura = pd.DataFrame({
    "Etapa": [etiqueta for etiqueta, _ in ETAPAS],
    "Con colegio identificado": [con_colegio[col].sum() for _, col in ETAPAS],
    "Sin colegio identificado": [sin_colegio[col].sum() for _, col in ETAPAS],
})
tabla_cobertura["Total nacional"] = (
    tabla_cobertura["Con colegio identificado"] + tabla_cobertura["Sin colegio identificado"]
)
tabla_cobertura["% sin colegio"] = (
    tabla_cobertura["Sin colegio identificado"] / tabla_cobertura["Total nacional"] * 100
).round(1)

st.subheader("Cobertura de identificación de colegio")
st.caption(
    "Refleja solo el filtro de Periodo (no Colegio/Provincia/etc., ya que los registros sin colegio "
    "no tienen esos atributos). Sin colegio identificado = registros con el centinela `ND` "
    "(«SIN INFORMACIÓN DE COLEGIO») o sin `CodColegioBanner_Sales` ni `CodColegioAMIED`. Entran en los "
    "totales de esta página agrupados en un solo colegio, pero no se pueden desagregar por "
    "provincia, sostenimiento ni ningún otro atributo del colegio."
)
st.dataframe(
    tabla_cobertura.style.format({
        "Con colegio identificado": "{:,.0f}", "Sin colegio identificado": "{:,.0f}",
        "Total nacional": "{:,.0f}", "% sin colegio": "{:.1f}%",
    }),
    width="stretch", hide_index=True,
)

###############################
## GRÁFICO SERIE DE TIEMPO
###############################

# --- Funnel por periodo ---
# "documentados" = conteo de IdBanner por periodo+colegio (ver
# etl/build_documentados_colegios.py) -- cada fila de la tabla origen ya es
# un estudiante documentado. Sumar entre periodos/colegios es correcto porque
# es un conteo, no un agregado repetido.
por_periodo = (
    filtrado.groupby("PeriodoBanner_Sales")
    .agg(
        graduados=("graduados_total", "sum"),
        leads=("leads", "sum"),
        afluentes=("afluentes", "sum"),
        documentados=("documentados", "sum"),
    )
    .reset_index()
    .sort_values("PeriodoBanner_Sales")
)
por_periodo["tasa_leads"] = (por_periodo["leads"] / por_periodo["graduados"] * 100).round(1)
por_periodo["tasa_afluentes"] = (por_periodo["afluentes"] / por_periodo["graduados"] * 100).round(1)
por_periodo["tasa_documentados"] = (por_periodo["documentados"] / por_periodo["graduados"] * 100).round(1)

st.subheader("Funnel en el tiempo: Graduados → Leads → Afluentes → Documentados")

escala_funnel = st.radio(
    "Escala del eje vertical",
    options=["Lineal", "Logarítmica"],
    horizontal=True,
    help=(
        "La escala lineal muestra las diferencias absolutas. La logarítmica "
        "facilita comparar series con cantidades muy distintas."
    ),
)
tipo_eje_funnel = "linear" if escala_funnel == "Lineal" else "log"
titulo_eje_funnel = (
    "Personas" if escala_funnel == "Lineal" else "Personas (escala logarítmica)"
)

# Valor de pensión -- solo aplica si el filtro quedo en UN colegio
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
        line=dict(width=2.2, color=COLOR_SECUNDARIO, shape="spline", smoothing=0.8),
        marker=dict(size=6, color="white", line=dict(width=2, color=COLOR_SECUNDARIO)),
        fill="tozeroy",
        fillcolor="rgba(140, 155, 171, 0.13)",
        customdata=por_periodo[["graduados"]],
        hovertemplate="Graduados: %{y:,.0f}<extra></extra>",
    )
)
for nombre, col_valor, col_tasa, color, color_relleno in [
    ("Leads", "leads", "tasa_leads", COLOR_TERCIARIO, "rgba(93, 155, 213, 0.11)"),
    ("Afluentes", "afluentes", "tasa_afluentes", COLOR_PRIMARIO, "rgba(31, 78, 121, 0.08)"),
    ("Documentados", "documentados", "tasa_documentados", COLOR_ALERTA, "rgba(176, 116, 90, 0.08)"),
]:
    sufijo = sufijo_pension if nombre == "Documentados" else ""
    fig_funnel.add_trace(
        go.Scatter(
            x=por_periodo["PeriodoBanner_Sales"], y=por_periodo[col_valor], mode="lines+markers", name=nombre,
            line=dict(width=2.2, color=color, shape="spline", smoothing=0.8),
            marker=dict(size=6, color="white", line=dict(width=2, color=color)),
            fill="tozeroy",
            fillcolor=color_relleno,
            customdata=por_periodo[[col_tasa]],
            hovertemplate=f"{nombre}: " + "%{y:,.0f} (%{customdata[0]:.1f}% de Graduados)" + sufijo + "<extra></extra>",
        )
    )
fig_funnel.update_layout(
    template="plotly_white", yaxis_type=tipo_eje_funnel, yaxis_title=titulo_eje_funnel,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(l=10, r=10, t=40, b=10),
    height=400,
)

############################
## LISTADO COLEGIOS 
############################

col_grafico, col_ranking = st.columns([2.2, 1.8])
with col_grafico:
    st.markdown("**Funnel**")
    st.plotly_chart(fig_funnel, width="stretch")
with col_ranking:
    st.markdown("**Listado Colegios**")
    # graduados_total es constante por (anio, colegio) -- se repite igual entre
    # los periodos 10 y 20 del mismo año. Colapsar primero a (anio, colegio) con
    # "first" evita duplicarlo al sumar sobre el rango de periodos filtrado.
    filtrado_anio = filtrado.copy()
    filtrado_anio["anio"] = filtrado_anio["PeriodoBanner_Sales"].str[:4]
    por_anio_nombre = (
        filtrado_anio.groupby(["anio", "nombre_institucion"])
        .agg(graduados=("graduados_total", "first"), documentados=("documentados", "sum"))
        .reset_index()
    )
    ranking_colegios = (
        por_anio_nombre.groupby("nombre_institucion")
        .agg(documentados=("documentados", "sum"), graduados=("graduados", "sum"))
        .reset_index()
    )
    graduados_seguro = ranking_colegios["graduados"].mask(ranking_colegios["graduados"] == 0)
    ranking_colegios["captacion_pct"] = (ranking_colegios["documentados"] / graduados_seguro * 100).round(1)
    ranking_colegios = ranking_colegios.sort_values("documentados", ascending=False).rename(columns={
        "nombre_institucion": "Colegio", "graduados": "Graduados",
        "documentados": "Documentados", "captacion_pct": "% Captación",
    })

    def _fondo_variacion_ranking(val):
        if pd.isna(val):
            return ""
        if val < 0:
            return "background-color: rgba(176, 116, 90, 0.20)"  # rojo tenue (tono COLOR_ALERTA)
        if val > 0:
            return "background-color: rgba(76, 140, 107, 0.20)"  # verde tenue (tono COLOR_EXITO)
        return ""

    st.dataframe(
        ranking_colegios[["Colegio", "Graduados", "Documentados", "% Captación"]].style
        .map(_fondo_variacion_ranking, subset=["% Captación"])
        .set_properties(subset=["Colegio"], **{"font-size": "0.8em"})
        .format({"Graduados": "{:,.0f}", "Documentados": "{:,.0f}", "% Captación": "{:.1f}%"}, na_rep="—"),
        width="stretch", height=400, hide_index=True,
    )

if colegio_unico:
    st.info(
        "Filtro reducido a **un solo colegio** — el % de documentados que ves arriba "
        "es exactamente la captación de ESE colegio en cada periodo exacto, sobre sus propios graduados. "
        + ("El valor de pensión de este colegio aparece al final del hover de Documentados." if pension_valor is not None
           else "Este colegio no tiene un valor de pensión registrado.")
    )


##################################
# --- Tabla anual (solo periodo 10): valores + % de variación interanual ---
##################################
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
            documentados=("documentados", "sum"),
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
    def _fondo_variacion(val):
        if pd.isna(val):
            return ""
        if val < 0:
            return "background-color: rgba(176, 116, 90, 0.20)"  # rojo tenue (tono COLOR_ALERTA)
        if val > 0:
            return "background-color: rgba(76, 140, 107, 0.20)"  # verde tenue (tono COLOR_EXITO)
        return ""

    COLUMNAS_VARIACION = ["% var. Graduados", "% var. Leads", "% var. Afluentes", "% var. Documentados"]
    st.dataframe(
        tabla_anual.style.map(_fondo_variacion, subset=COLUMNAS_VARIACION).format({
            "Colegios": "{:,.0f}", "Graduados": "{:,.0f}", "Leads": "{:,.0f}",
            "Afluentes": "{:,.0f}", "Documentados": "{:,.0f}",
            "% var. Graduados": "{:+.1f}%", "% var. Leads": "{:+.1f}%",
            "% var. Afluentes": "{:+.1f}%", "% var. Documentados": "{:+.1f}%",
        }, na_rep="—"),
        width="stretch", hide_index=True,
    )

##################################
# --- Tabla anual (solo periodo 20): valores + % de variación interanual ---
##################################
st.subheader("Tabla anual (solo periodo 20)")
st.caption(
    "Compara únicamente el segundo ciclo de admisión de cada año (periodos que terminan en \"20\") "
    "y calcula la variación respecto al periodo 20 del año anterior. "
    "Ordenable por cualquier columna (clic en el encabezado)."
)
filtrado_p20 = filtrado[filtrado["PeriodoBanner_Sales"].str.endswith("20")].copy()
filtrado_p20["anio"] = filtrado_p20["PeriodoBanner_Sales"].str[:4]

if filtrado_p20.empty:
    st.info("No hay datos de periodo 20 para este filtro.")
else:
    por_anio_p20 = (
        filtrado_p20.groupby("anio")
        .agg(
            colegios=("codigo_colegio", "nunique"),
            graduados=("graduados_total", "sum"),
            leads=("leads", "sum"),
            afluentes=("afluentes", "sum"),
            documentados=("documentados", "sum"),
        )
        .reset_index()
        .sort_values("anio")
    )
    tabla_anual_p20 = por_anio_p20[
        ["anio", "colegios", "graduados", "leads", "afluentes", "documentados"]
    ].copy()
    for col in ["graduados", "leads", "afluentes", "documentados"]:
        tabla_anual_p20[f"var_{col}_pct"] = (
            tabla_anual_p20[col].pct_change().mul(100).round(1)
        )
    tabla_anual_p20 = tabla_anual_p20.sort_values("anio", ascending=False).rename(columns={
        "anio": "Año", "colegios": "Colegios", "graduados": "Graduados", "leads": "Leads",
        "afluentes": "Afluentes", "documentados": "Documentados",
        "var_graduados_pct": "% var. Graduados", "var_leads_pct": "% var. Leads",
        "var_afluentes_pct": "% var. Afluentes", "var_documentados_pct": "% var. Documentados",
    })[[
        "Año", "Colegios", "Graduados", "% var. Graduados", "Leads", "% var. Leads",
        "Afluentes", "% var. Afluentes", "Documentados", "% var. Documentados",
    ]]
    st.dataframe(
        tabla_anual_p20.style.map(_fondo_variacion, subset=COLUMNAS_VARIACION).format({
            "Colegios": "{:,.0f}", "Graduados": "{:,.0f}", "Leads": "{:,.0f}",
            "Afluentes": "{:,.0f}", "Documentados": "{:,.0f}",
            "% var. Graduados": "{:+.1f}%", "% var. Leads": "{:+.1f}%",
            "% var. Afluentes": "{:+.1f}%", "% var. Documentados": "{:+.1f}%",
        }, na_rep="—"),
        width="stretch", hide_index=True,
    )

##############################################################################
## SECCIÓN: PROMEDIO PONDERADO DE CAPTACIÓN
## ─────────────────────────────────────────────────────────────────────────
## Objetivo: mostrar, año a año, cuántos graduados hubo en los colegios
## filtrados, cuántos se documentaron, qué % representa la captación y
## calcular un PROMEDIO PONDERADO de esa tasa según los pesos que el
## usuario asigne libremente a cada año (sliders interactivos), normalizados
## automáticamente para que siempre sumen 100%.
##
## Fuente de datos: usa el DataFrame "filtrado" (resumen por PeriodoBanner_Sales
## x colegio) heredado de los filtros superiores de esta página. Para obtener
## un dato anual limpio se colapsa sumando TODOS los periodos del año (10 + 20)
## para reflejar el ciclo académico completo.
##
## Lógica del promedio ponderado
## ─────────────────────────────
##  captacion_pct_i  = documentados_i / graduados_i × 100  (por cada año i)
##  peso_crudo_i      = valor del slider del año i  (rango 0–100, default 1)
##  peso_i (%)        = peso_crudo_i / Σ(peso_crudo) × 100   → normalizado a 100%
##  promedio_pond     = Σ(captacion_pct_i × peso_i) / Σ(peso_i)
##
## Si todos los pesos son iguales, el resultado coincide con el promedio
## aritmético simple de las tasas anuales.
## Un peso 0 excluye el año del cómputo (equivale a ignorarlo).
##############################################################################

st.divider()   # separador visual respecto a la sección anterior

st.subheader("📊 Promedio ponderado de captación por año")
st.caption(
    "Incluye **todos** los periodos de admisión de cada año (10 + 20) con los filtros activos. "
    "Ajusta el **peso** de cada año para ponderar su influencia en el promedio "
    "(se normaliza automáticamente para sumar 100%); peso **0** = excluir el año del cálculo."
)

# ── 1. Construir tabla base anual (todos los periodos) ──────────────────────
filtrado_pond = filtrado.copy()
filtrado_pond["anio"] = filtrado_pond["PeriodoBanner_Sales"].str[:4]

tabla_pond_base = (
    filtrado_pond
    .groupby(["anio", "codigo_colegio"])
    .agg(
        graduados=   ("graduados_total", "first"),  # un único valor anual por colegio
        documentados=("documentados",    "sum"),    # suma periodo 10 + periodo 20
    )
    .reset_index()
    .groupby("anio")
    .agg(
        graduados=   ("graduados",    "sum"),
        documentados=("documentados", "sum"),
    )
    .reset_index()
    .sort_values("anio")
)

# Calcular % captación (evitar división por 0 con replace)
_grad_seguro = tabla_pond_base["graduados"].replace(0, np.nan)
tabla_pond_base["captacion_pct"] = (
    tabla_pond_base["documentados"] / _grad_seguro * 100
).round(2)

anios_disponibles_pond = tabla_pond_base["anio"].tolist()

if tabla_pond_base.empty or tabla_pond_base["captacion_pct"].isna().all():
    st.info("No hay datos suficientes para calcular el promedio ponderado con estos filtros.")
else:
    # ── 2. Sliders de ponderación (uno por año) ──────────────────────────────
    st.markdown("**Ajusta el peso de cada año** *(0 = excluir del promedio)*")

    n_anios = len(anios_disponibles_pond)
    MAX_COLS = min(n_anios, 6)   # máximo 6 sliders por fila
    filas_sliders = [
        anios_disponibles_pond[i : i + MAX_COLS]
        for i in range(0, n_anios, MAX_COLS)
    ]

    pesos: dict[str, float] = {}
    for fila_anios in filas_sliders:
        cols_slider = st.columns(len(fila_anios))
        for col_widget, anio in zip(cols_slider, fila_anios):
            with col_widget:
                pesos[anio] = st.slider(
                    label=str(anio),
                    min_value=0.0,
                    max_value=10.0,
                    value=1.0,        # peso neutral: todos los años cuentan igual
                    step=0.5,
                    key=f"slider_peso_pond_{anio}",
                    help=(
                        f"Peso del año {anio} en el promedio ponderado. "
                        "Aumentar le da más influencia; 0 lo excluye."
                    ),
                )

    # ── 3. Calcular promedio ponderado ──────────────────────────────────────
    tabla_pond_base["peso_crudo"] = tabla_pond_base["anio"].map(pesos).fillna(0.0)

    # ✅ CORREGIDO: mask_validos usa "peso_crudo" (la columna que sí existe
    # en este punto), no "peso" (que todavía no se ha creado).
    mask_validos = (tabla_pond_base["peso_crudo"] > 0) & tabla_pond_base["captacion_pct"].notna()
    suma_pesos_crudos = tabla_pond_base.loc[mask_validos, "peso_crudo"].sum()

    # Normalizamos los pesos crudos del slider a porcentajes que suman 100%.
    # Ej.: sliders en 3, 7, 1, 5 (suma=16) → 18.75%, 43.75%, 6.25%, 31.25% (suma=100%)
    if suma_pesos_crudos > 0:
        tabla_pond_base["peso"] = np.where(
            mask_validos,
            tabla_pond_base["peso_crudo"] / suma_pesos_crudos * 100,
            0.0,
        )
    else:
        tabla_pond_base["peso"] = 0.0

    suma_pesos = tabla_pond_base.loc[mask_validos, "peso"].sum()  # será 100.0 (o 0 si nada válido)
    suma_pond  = (
        tabla_pond_base.loc[mask_validos, "captacion_pct"]
        * tabla_pond_base.loc[mask_validos, "peso"]
    ).sum()

    promedio_ponderado = (suma_pond / suma_pesos) if suma_pesos > 0 else np.nan

    # ── 4. Columna auxiliar: contribución individual de cada año ────────────
    tabla_pond_base["contribucion"] = (
        tabla_pond_base["captacion_pct"] * tabla_pond_base["peso"] / 100
    ).round(3)

    # ── 5. Renombrar para visualización ─────────────────────────────────────
    # ✅ CORREGIDO: se elimina "peso_crudo" antes de renombrar, para que no
    # aparezca en la tabla final con valores sin normalizar (0–100 crudos).
    tabla_mostrar = (
        tabla_pond_base
        .drop(columns=["peso_crudo"])
        .rename(columns={
            "anio":          "Año",
            "graduados":     "Graduados",
            "documentados":  "Documentados",
            "captacion_pct": "% Captación",
            "peso":          "Peso (%)",
            "contribucion":  "Contribución ponderada",
        })
    )

    # Fila de totales / promedio al pie de la tabla
    fila_total = pd.DataFrame([{
        "Año":                    "TOTAL / PROMEDIO POND.",
        "Graduados":              tabla_mostrar["Graduados"].sum(),
        "Documentados":           tabla_mostrar["Documentados"].sum(),
        "% Captación":            promedio_ponderado,
        "Peso (%)":               suma_pesos,
        "Contribución ponderada": suma_pond / 100 if suma_pesos > 0 else np.nan,
    }])
    tabla_final = pd.concat([tabla_mostrar, fila_total], ignore_index=True)

    # ── 6. Función de color: compara cada año contra el promedio ponderado ──
    def _color_captacion_pond(val):
        if pd.isna(val) or not isinstance(val, (int, float)):
            return ""
        if np.isnan(promedio_ponderado):
            return ""
        if val > promedio_ponderado:
            return "background-color: rgba(76, 140, 107, 0.20)"   # verde tenue
        if val < promedio_ponderado:
            return "background-color: rgba(176, 116, 90, 0.20)"   # rojo tenue
        return ""

    # ── 7. KPIs resumen ─────────────────────────────────────────────────────
    kpi_pond = st.columns([1, 1, 1, 2])
    kpi_pond[0].metric(
        "Promedio ponderado de captación",
        f"{promedio_ponderado:.2f}%" if not np.isnan(promedio_ponderado) else "—",
        help="Σ(% captación × peso%) / 100",
    )
    kpi_pond[1].metric(
        "Años incluidos en el cálculo",
        f"{int(mask_validos.sum())} de {n_anios}",
        help="Años con peso > 0 y con datos de graduados",
    )
    kpi_pond[2].metric(
        "Suma de pesos",
        f"{suma_pesos:.1f}%",
        help="Los pesos crudos de los sliders se normalizan automáticamente para sumar 100%",
    )

    # ── 8. Tabla final ───────────────────────────────────────────────────────
    altura_tabla = min(500, (len(tabla_final) + 1) * 36 + 40)  # altura adaptativa
    st.dataframe(
        tabla_final.style
        .map(_color_captacion_pond, subset=["% Captación"])
        .format(
            {
                "Graduados":               "{:,.0f}",
                "Documentados":            "{:,.0f}",
                "% Captación":             "{:.2f}%",
                "Peso (%)":                "{:.1f}%",
                "Contribución ponderada":  "{:.2f}",
            },
            na_rep="—",
        ),
        width="stretch",
        hide_index=True,
        height=altura_tabla,
    )

    st.caption(
        "📌 **Contribución ponderada** = % Captación × Peso del año (%) / 100. "
        "La fila *TOTAL / PROMEDIO POND.* muestra la suma de Graduados y Documentados de todos "
        "los años, y el **promedio ponderado** de la tasa (no la suma). "
        "Verde = año con captación por encima del promedio · Rojo = por debajo."
    )
