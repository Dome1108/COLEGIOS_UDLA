"""Cuadrante de mercado: ¿el colegio (mercado de graduados) creció o decreció,
y cómo le fue a UDLA (documentados) en ese mismo colegio? Alertas para colegios
en caída en ambos frentes."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import cargar_documentados_resumen
from utils.theme import COLOR_PRIMARIO, COLOR_SECUNDARIO, inject_css

st.set_page_config(page_title="Mercado y Alertas", layout="wide")
inject_css()

COLOR_EXITO = "#4C8C6B"
COLOR_ALERTA = "#B0745A"

st.title("Mercado y Alertas — ¿Creció el colegio? ¿Le fue bien a UDLA ahí?")
st.caption(
    "Compara el último año académico completo contra el anterior, por colegio. "
    "Un 'año' agrupa los 2 periodos de admisión (ej. 2025 = 202510 + 202520)."
)

resumen = cargar_documentados_resumen()
resumen = resumen.copy()
resumen["anio"] = resumen["PeriodoBanner_Sales"].str[:4]

anios_disponibles = sorted(resumen["anio"].unique())
# El ultimo anio suele estar incompleto (admision en curso) -- se excluye del
# par de comparacion por defecto, pero se puede elegir manualmente.
anio_actual_default = anios_disponibles[-2] if len(anios_disponibles) > 1 else anios_disponibles[-1]
anio_anterior_default = anios_disponibles[-3] if len(anios_disponibles) > 2 else anios_disponibles[0]

cols_filtro = st.columns([2, 1.3, 1.3, 1, 1, 1, 1])
with cols_filtro[0]:
    colegios_nombres = sorted(resumen["nombre_institucion"].dropna().unique().tolist())
    colegio_sel = st.multiselect("Colegio", colegios_nombres)
with cols_filtro[1]:
    anios_base_sel = st.multiselect("Año(s) base", anios_disponibles, default=[anio_anterior_default])
with cols_filtro[2]:
    anios_actual_sel = st.multiselect("Año(s) comparado(s)", anios_disponibles, default=[anio_actual_default])
with cols_filtro[3]:
    provincias = sorted(resumen["provincia"].dropna().unique().tolist())
    provincia_sel = st.multiselect("Provincia", provincias)
with cols_filtro[4]:
    sostenimientos = sorted(resumen["sostenimiento"].dropna().unique().tolist())
    sostenimiento_sel = st.multiselect("Sostenimiento", sostenimientos)
with cols_filtro[5]:
    clusters = sorted(resumen["cluster"].dropna().unique().tolist())
    cluster_sel = st.multiselect("Cluster", clusters)
with cols_filtro[6]:
    rangos_pension = sorted(resumen["rango_pension"].dropna().unique().tolist())
    rango_pension_sel = st.multiselect("Rango pensión", rangos_pension)

CUADRANTES_TODOS = [
    "Mercado crece + UDLA crece",
    "Mercado cae + UDLA crece",
    "Mercado crece + UDLA cae",
    "Mercado cae + UDLA cae",
]
cuadrantes_sel = st.multiselect("Cuadrante (filtra tabla y alertas)", CUADRANTES_TODOS, default=CUADRANTES_TODOS)

if set(anios_base_sel) & set(anios_actual_sel):
    st.warning("Los años base y comparado no pueden superponerse — elige conjuntos distintos.")
    st.stop()

filtrado = resumen.copy()
for col, sel in [
    ("nombre_institucion", colegio_sel),
    ("provincia", provincia_sel), ("sostenimiento", sostenimiento_sel),
    ("cluster", cluster_sel), ("rango_pension", rango_pension_sel),
]:
    if sel:
        filtrado = filtrado[filtrado[col].isin(sel)]

# --- Tabla anual: valores + % de variación interanual (independiente del año base/comparado de abajo) ---
st.subheader("Tabla anual")
st.caption(
    "Usa TODOS los años disponibles para los colegios que queden en el filtro de Colegio/Provincia/Sostenimiento/"
    "Cluster/Rango pensión (no depende de Año base/comparado). Ordenable por cualquier columna (clic en el encabezado)."
)
por_anio_tabla = (
    filtrado.groupby("anio")
    .agg(
        colegios=("codigo_colegio", "nunique"),
        graduados=("graduados_total", "sum"),
        documentados=("documentados_d", "sum"),
    )
    .reset_index()
    .sort_values("anio")
)
por_anio_tabla["var_graduados_pct"] = por_anio_tabla["graduados"].pct_change().mul(100).round(1)
por_anio_tabla["var_documentados_pct"] = por_anio_tabla["documentados"].pct_change().mul(100).round(1)
tabla_anual = por_anio_tabla.sort_values("anio", ascending=False).rename(columns={
    "anio": "Año", "colegios": "Colegios", "graduados": "Graduados", "documentados": "Documentados",
    "var_graduados_pct": "% var. Graduados", "var_documentados_pct": "% var. Documentados",
})[["Año", "Colegios", "Graduados", "% var. Graduados", "Documentados", "% var. Documentados"]]


def _fondo_variacion(val):
    if pd.isna(val):
        return ""
    if val < 0:
        return "background-color: rgba(176, 116, 90, 0.20)"  # rojo tenue (tono COLOR_ALERTA)
    if val > 0:
        return "background-color: rgba(76, 140, 107, 0.20)"  # verde tenue (tono COLOR_EXITO)
    return ""


st.dataframe(
    tabla_anual.style.map(_fondo_variacion, subset=["% var. Graduados", "% var. Documentados"]).format({
        "Colegios": "{:,.0f}", "Graduados": "{:,.0f}", "Documentados": "{:,.0f}",
        "% var. Graduados": "{:+.1f}%", "% var. Documentados": "{:+.1f}%",
    }, na_rep="—"),
    width="stretch", hide_index=True,
)

# "documentados" toma el campo D (funnel L->A->D, corregido para sumar entre
# CodBanner -- ver etl/build_documentados_colegios.py), igual que en la pagina
# de Captacion UDLA, para que ambas paginas sean consistentes.
por_anio_colegio = (
    filtrado.groupby(["anio", "codigo_colegio"])
    .agg(
        nombre_institucion=("nombre_institucion", "first"),
        provincia=("provincia", "first"),
        canton=("canton", "first"),
        sostenimiento=("sostenimiento", "first"),
        cluster=("cluster", "first"),
        graduados=("graduados_total", "sum"),
        documentados=("documentados_d", "sum"),
    )
    .reset_index()
)

modo_trayectoria = not anios_base_sel and not anios_actual_sel
if not modo_trayectoria and (not anios_base_sel or not anios_actual_sel):
    st.warning("Elige al menos un año base y un año comparado (o deja ambos vacíos para ver la trayectoria completa).")
    st.stop()

if modo_trayectoria:
    # Sin año base/comparado elegido: se arma UNA fila por colegio y por CADA
    # transicion consecutiva (2022->2023, 2023->2024, ...), para poder trazar
    # el "camino" completo del colegio por el cuadrante en el tiempo.
    filas_transicion = []
    for anio_prev, anio_curr in zip(anios_disponibles[:-1], anios_disponibles[1:]):
        base_y = por_anio_colegio[por_anio_colegio["anio"] == anio_prev].set_index("codigo_colegio")
        actual_y = por_anio_colegio[por_anio_colegio["anio"] == anio_curr].set_index("codigo_colegio")
        comunes_y = base_y.index.intersection(actual_y.index)
        if len(comunes_y) == 0:
            continue
        filas_transicion.append(pd.DataFrame({
            "codigo_colegio": comunes_y,
            "anio_transicion": f"{anio_prev}→{anio_curr}",
            "nombre_institucion": actual_y.loc[comunes_y, "nombre_institucion"],
            "provincia": actual_y.loc[comunes_y, "provincia"],
            "canton": actual_y.loc[comunes_y, "canton"],
            "sostenimiento": actual_y.loc[comunes_y, "sostenimiento"],
            "cluster": actual_y.loc[comunes_y, "cluster"],
            "graduados_base": base_y.loc[comunes_y, "graduados"],
            "graduados_actual": actual_y.loc[comunes_y, "graduados"],
            "documentados_base": base_y.loc[comunes_y, "documentados"],
            "documentados_actual": actual_y.loc[comunes_y, "documentados"],
        }))
    cuadro = pd.concat(filas_transicion, ignore_index=True) if filas_transicion else pd.DataFrame(columns=[
        "codigo_colegio", "anio_transicion", "nombre_institucion", "provincia", "canton", "sostenimiento",
        "cluster", "graduados_base", "graduados_actual", "documentados_base", "documentados_actual",
    ])
else:
    etiqueta_base = "+".join(anios_base_sel)
    etiqueta_actual = "+".join(anios_actual_sel)

    # Si se eligen varios años en un grupo (base o actual), se SUMAN entre si antes
    # de comparar -- permite comparar bloques multi-anio (ej. 2022+2023 vs 2024+2025).
    actual = (
        por_anio_colegio[por_anio_colegio["anio"].isin(anios_actual_sel)]
        .groupby("codigo_colegio")
        .agg(
            nombre_institucion=("nombre_institucion", "first"),
            provincia=("provincia", "first"),
            canton=("canton", "first"),
            sostenimiento=("sostenimiento", "first"),
            cluster=("cluster", "first"),
            graduados=("graduados", "sum"),
            documentados=("documentados", "sum"),
        )
    )
    base = (
        por_anio_colegio[por_anio_colegio["anio"].isin(anios_base_sel)]
        .groupby("codigo_colegio")
        .agg(graduados=("graduados", "sum"), documentados=("documentados", "sum"))
    )
    comunes = base.index.intersection(actual.index)

    if len(comunes) == 0:
        st.warning("No hay colegios presentes en ambos grupos de años con estos filtros.")
        st.stop()

    cuadro = pd.DataFrame({
        "codigo_colegio": comunes,
        "anio_transicion": etiqueta_actual,
        "nombre_institucion": actual.loc[comunes, "nombre_institucion"],
        "provincia": actual.loc[comunes, "provincia"],
        "canton": actual.loc[comunes, "canton"],
        "sostenimiento": actual.loc[comunes, "sostenimiento"],
        "cluster": actual.loc[comunes, "cluster"],
        "graduados_base": base.loc[comunes, "graduados"],
        "graduados_actual": actual.loc[comunes, "graduados"],
        "documentados_base": base.loc[comunes, "documentados"],
        "documentados_actual": actual.loc[comunes, "documentados"],
    }).reset_index(drop=True)

if cuadro.empty:
    st.warning("No hay colegios comunes entre años consecutivos con estos filtros.")
    st.stop()

graduados_base_seguro = cuadro["graduados_base"].replace(0, np.nan)
documentados_base_seguro = cuadro["documentados_base"].replace(0, np.nan)

cuadro["cambio_graduados_pct"] = (
    (cuadro["graduados_actual"] - cuadro["graduados_base"]) / graduados_base_seguro * 100
).round(1)
cuadro["cambio_documentados_pct"] = (
    (cuadro["documentados_actual"] - cuadro["documentados_base"]) / documentados_base_seguro * 100
).round(1)
cuadro = cuadro.dropna(subset=["cambio_graduados_pct", "cambio_documentados_pct"])


def clasificar(row):
    mercado_crece = row["cambio_graduados_pct"] >= 0
    udla_crece = row["cambio_documentados_pct"] >= 0
    if mercado_crece and udla_crece:
        return "Mercado crece + UDLA crece"
    if mercado_crece and not udla_crece:
        return "Mercado crece + UDLA cae"
    if not mercado_crece and udla_crece:
        return "Mercado cae + UDLA crece"
    return "Mercado cae + UDLA cae"


cuadro["cuadrante"] = cuadro.apply(clasificar, axis=1)

COLOR_CUADRANTE = {
    "Mercado crece + UDLA crece": COLOR_EXITO,
    "Mercado cae + UDLA crece": COLOR_PRIMARIO,
    "Mercado crece + UDLA cae": COLOR_SECUNDARIO,
    "Mercado cae + UDLA cae": COLOR_ALERTA,
}

# --- KPIs nacionales (sobre este mismo filtro) ---
if modo_trayectoria:
    st.subheader("Mercado: trayectoria año a año")
    n_colegios_trayectoria = cuadro["codigo_colegio"].nunique()
    st.caption(
        f"{n_colegios_trayectoria:,} colegios · {cuadro['anio_transicion'].nunique()} transiciones año-a-año, "
        "con estos filtros. Sin Año base/comparado elegidos, se muestra el camino completo de cada colegio."
    )
    if n_colegios_trayectoria > 15:
        st.warning(
            f"Hay {n_colegios_trayectoria:,} colegios en esta vista — puede saturarse. "
            "Considera filtrar por Colegio/Provincia/Sostenimiento/Cluster para una trayectoria más legible."
        )
else:
    st.subheader(f"Mercado total: {etiqueta_base} → {etiqueta_actual}")
    total_grad_base, total_grad_actual = cuadro["graduados_base"].sum(), cuadro["graduados_actual"].sum()
    total_doc_base, total_doc_actual = cuadro["documentados_base"].sum(), cuadro["documentados_actual"].sum()
    kpi = st.columns(2)
    kpi[0].metric(
        f"Graduados (mercado) — colegios comunes",
        f"{total_grad_actual:,.0f}",
        f"{(total_grad_actual - total_grad_base) / total_grad_base * 100:+.1f}% vs {etiqueta_base}",
    )
    kpi[1].metric(
        "Documentados UDLA — mismos colegios",
        f"{total_doc_actual:,.0f}",
        f"{(total_doc_actual - total_doc_base) / total_doc_base * 100:+.1f}% vs {etiqueta_base}",
    )
    st.caption(
        f"{len(cuadro):,} colegios presentes en ambos grupos de años ({etiqueta_base} y {etiqueta_actual}) con estos filtros. "
        f"Graduados: {total_grad_base:,.0f} ({etiqueta_base}) → {total_grad_actual:,.0f} ({etiqueta_actual}). "
        f"Documentados: {total_doc_base:,.0f} ({etiqueta_base}) → {total_doc_actual:,.0f} ({etiqueta_actual})."
    )

# --- Vista 1: Cuadrante (scatter) ---
st.subheader("Vista de cuadrante")
doc_actual_max = cuadro["documentados_actual"].max() or 1
fig_cuadrante = go.Figure()

if modo_trayectoria:
    for _, grupo in cuadro.groupby("codigo_colegio"):
        grupo = grupo.sort_values("anio_transicion")
        tamanos = 8 + (grupo["documentados_actual"] / doc_actual_max) * 34
        colores_puntos = grupo["cuadrante"].map(COLOR_CUADRANTE)
        fig_cuadrante.add_trace(
            go.Scatter(
                x=grupo["cambio_graduados_pct"], y=grupo["cambio_documentados_pct"],
                mode="lines+markers", showlegend=False,
                line=dict(width=1, color="#B8B4AC"),
                marker=dict(size=tamanos, sizemode="diameter", color=colores_puntos, line=dict(width=1, color="white")),
                customdata=grupo[[
                    "nombre_institucion", "anio_transicion",
                    "documentados_base", "documentados_actual", "graduados_base", "graduados_actual",
                ]],
                hovertemplate=(
                    "%{customdata[0]} (%{customdata[1]})<br>"
                    "Documentados: %{customdata[2]:,.0f} → %{customdata[3]:,.0f} (%{y:+.1f}%)<br>"
                    "Graduados: %{customdata[4]:,.0f} → %{customdata[5]:,.0f} (%{x:+.1f}%)"
                    "<extra></extra>"
                ),
            )
        )
    # Leyenda manual de colores de cuadrante (las trazas por colegio van con showlegend=False).
    for cuadrante_nombre, color in COLOR_CUADRANTE.items():
        fig_cuadrante.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers", marker=dict(size=9, color=color), name=cuadrante_nombre,
        ))
    titulo_x = "% cambio en Graduados (vs año anterior)"
    titulo_y = "% cambio en Documentados UDLA (vs año anterior)"
else:
    for cuadrante_nombre, color in COLOR_CUADRANTE.items():
        sub = cuadro[cuadro["cuadrante"] == cuadrante_nombre]
        tamanos = 8 + (sub["documentados_actual"] / doc_actual_max) * 34
        fig_cuadrante.add_trace(
            go.Scatter(
                x=sub["cambio_graduados_pct"], y=sub["cambio_documentados_pct"],
                mode="markers", name=cuadrante_nombre,
                marker=dict(size=tamanos, sizemode="diameter", color=color, line=dict(width=1, color="white")),
                text=sub["nombre_institucion"],
                customdata=sub[["documentados_base", "documentados_actual", "graduados_base", "graduados_actual"]],
                hovertemplate=(
                    "%{text}<br>"
                    f"Documentados {etiqueta_base}→{etiqueta_actual}: " + "%{customdata[0]:,.0f} → %{customdata[1]:,.0f} (%{y:+.1f}%)<br>"
                    f"Graduados {etiqueta_base}→{etiqueta_actual}: " + "%{customdata[2]:,.0f} → %{customdata[3]:,.0f} (%{x:+.1f}%)"
                    "<extra></extra>"
                ),
            )
        )
    titulo_x = f"% cambio en Graduados ({etiqueta_base} → {etiqueta_actual})"
    titulo_y = f"% cambio en Documentados UDLA ({etiqueta_base} → {etiqueta_actual})"

fig_cuadrante.add_hline(y=0, line=dict(color=COLOR_SECUNDARIO, width=1, dash="dot"))
fig_cuadrante.add_vline(x=0, line=dict(color=COLOR_SECUNDARIO, width=1, dash="dot"))
fig_cuadrante.update_layout(
    template="plotly_white",
    xaxis_title=titulo_x,
    yaxis_title=titulo_y,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(l=10, r=10, t=40, b=10),
    height=520,
)
st.plotly_chart(fig_cuadrante, width="stretch")

# --- Vista 2: Tabla ---
st.subheader("Vista de tabla")
resumen_cuadrantes = cuadro["cuadrante"].value_counts().reindex(COLOR_CUADRANTE.keys()).fillna(0).astype(int)
st.write(" · ".join(f"**{k}**: {v}" for k, v in resumen_cuadrantes.items()))

cuadro_filtrado_cuadrante = cuadro[cuadro["cuadrante"].isin(cuadrantes_sel)]
tabla = cuadro_filtrado_cuadrante[[
    "nombre_institucion", "anio_transicion", "provincia", "canton", "sostenimiento", "cluster",
    "graduados_base", "graduados_actual", "cambio_graduados_pct",
    "documentados_base", "documentados_actual", "cambio_documentados_pct", "cuadrante",
]].sort_values("cambio_documentados_pct")
st.dataframe(tabla, width="stretch", height=400)

# --- Detalle por cuadrante (respeta el filtro de arriba) ---
st.subheader("Detalle por cuadrante")
ICONO_CUADRANTE = {
    "Mercado cae + UDLA cae": "🔴",
    "Mercado cae + UDLA crece": "🟡",
    "Mercado crece + UDLA cae": "🟠",
    "Mercado crece + UDLA crece": "🟢",
}
COLUMNAS_DETALLE = [
    "nombre_institucion", "anio_transicion", "provincia", "canton", "sostenimiento",
    "graduados_base", "graduados_actual", "cambio_graduados_pct",
    "documentados_base", "documentados_actual", "cambio_documentados_pct",
]
for cuadrante_nombre in CUADRANTES_TODOS:
    if cuadrante_nombre not in cuadrantes_sel:
        continue
    sub = cuadro[cuadro["cuadrante"] == cuadrante_nombre].sort_values("cambio_documentados_pct")
    icono = ICONO_CUADRANTE[cuadrante_nombre]
    with st.expander(f"{icono} {cuadrante_nombre} ({len(sub)} colegios)", expanded=(cuadrante_nombre == "Mercado cae + UDLA cae")):
        if sub.empty:
            st.success("Ningún colegio (con estos filtros) cae en este cuadrante.")
        else:
            st.dataframe(sub[COLUMNAS_DETALLE], width="stretch", height=300)
