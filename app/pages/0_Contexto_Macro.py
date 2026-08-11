"""Contexto macro de nacimientos y graduados de tercero de Bachillerato."""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.theme import inject_css


st.set_page_config(page_title="Contexto macro", layout="wide")
inject_css()

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RUTA_NACIMIENTOS = DATA_DIR / "nacimientos_cohortes.parquet"
RUTA_GRADUADOS = DATA_DIR / "graduados_tercero_bachillerato.parquet"

COLORES = {
    "Fiscal": "#1F4E79",
    "Fiscomisional": "#D28C36",
    "Particular": "#6A994E",
    "Nacimientos": "#8C9BAB",
}


@st.cache_data
def cargar_datos() -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.read_parquet(RUTA_NACIMIENTOS), pd.read_parquet(RUTA_GRADUADOS)


def proyectar_por_cohorte(
    graduados: pd.DataFrame,
    nacimientos: pd.DataFrame,
    sostenimientos: list[str],
) -> pd.DataFrame:
    """Proyecta 2026-2035 según la tendencia suavizada de las cohortes conocidas.

    Cada sostenimiento parte de su último dato real y evoluciona con el índice
    lineal de nacimientos de 2008-2017. Esto evita saltos de nivel entre la
    observación de 2025 y el primer año proyectado.
    """
    futuro = nacimientos[nacimientos["anio_nacimiento"].between(2008, 2017)].copy()
    futuro["anio_egreso"] = futuro["anio_nacimiento"] + 18
    futuro = futuro.sort_values("anio_nacimiento")
    validos = futuro.dropna(subset=["nacimientos_total"])
    if len(validos) < 2:
        return pd.DataFrame()

    pendiente, intercepto = np.polyfit(
        validos["anio_nacimiento"], validos["nacimientos_total"], 1
    )
    nacimiento_base = intercepto + pendiente * 2007
    futuro["indice_cohorte"] = (
        intercepto + pendiente * futuro["anio_nacimiento"]
    ) / nacimiento_base

    partes = []
    for sostenimiento in sostenimientos:
        historico = graduados[graduados["Sostenimiento"] == sostenimiento].sort_values(
            "anio_egreso"
        )
        if historico.empty:
            continue
        ultimo_real_sostenimiento = historico.iloc[-1]
        parte = futuro[["anio_nacimiento", "anio_egreso", "nacimientos_total"]].copy()
        parte["Sostenimiento"] = sostenimiento
        parte["graduados"] = np.rint(
            ultimo_real_sostenimiento["graduados"] * futuro["indice_cohorte"]
        ).astype("int64")
        partes.append(parte)
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


st.title("Nacimientos y graduados de tercero de Bachillerato")
st.caption(
    "Lectura por cohortes: el eje inferior muestra el año de nacimiento y el superior "
    "el año aproximado de graduación (nacimiento + 18 años)."
)

ambito = st.radio("Ámbito", ["Nacional", "Pichincha"], horizontal=True)

nacimientos, detalle = cargar_datos()
nac = nacimientos[nacimientos["ambito"] == ambito].copy()
nac = nac[nac["anio_nacimiento"] >= 1996].copy()
if ambito == "Nacional":
    # La cohorte de referencia solicitada combina los nacimientos ocurridos en
    # establecimientos IESS y privados.
    nac["nacimientos_total"] = nac[["iess", "privados"]].sum(axis=1, min_count=1)
if ambito == "Pichincha":
    detalle = detalle[detalle["Provincia"].astype(str).str.upper() == "PICHINCHA"].copy()

detalle["Año_Egreso"] = pd.to_numeric(detalle["Año_Egreso"], errors="coerce")
graduados = (
    detalle[detalle["Sostenimiento"].isin(["Fiscal", "Fiscomisional", "Particular"])]
    .groupby(["Año_Egreso", "Sostenimiento"], as_index=False)["TotalPromovidosTercerAñoBACH"]
    .sum()
    .rename(columns={"Año_Egreso": "anio_egreso", "TotalPromovidosTercerAñoBACH": "graduados"})
)
graduados["anio_egreso"] = graduados["anio_egreso"].astype("int64")
graduados["anio_nacimiento"] = graduados["anio_egreso"] - 18
graduados = graduados[graduados["anio_nacimiento"] >= 1996].copy()

opciones = ["Fiscal", "Fiscomisional", "Particular"]
seleccion = st.multiselect("Sostenimiento de los graduados", opciones, default=opciones)
if not seleccion:
    st.warning("Selecciona al menos un sostenimiento para visualizar el gráfico.")
    st.stop()

graduados = graduados[graduados["Sostenimiento"].isin(seleccion)]
proyeccion = proyectar_por_cohorte(graduados, nac, seleccion)

ultimo_real = int(graduados["anio_egreso"].max())
total_ultimo = int(graduados.loc[graduados["anio_egreso"] == ultimo_real, "graduados"].sum())
total_proyectado = int(
    proyeccion.loc[proyeccion["anio_egreso"] == 2035, "graduados"].sum()
) if not proyeccion.empty else 0
variacion = (total_proyectado / total_ultimo - 1) * 100 if total_ultimo else np.nan

kpis = st.columns(4)
kpis[0].metric("Último dato real", str(ultimo_real))
kpis[1].metric("Graduados — último año", f"{total_ultimo:,.0f}")
kpis[2].metric("Horizonte proyectado", "2035")
kpis[3].metric(
    "Cambio esperado 2025–2035",
    f"{variacion:+.1f}%" if not np.isnan(variacion) else "N/D",
)

fig = go.Figure()

if ambito == "Nacional":
    fig.add_trace(
        go.Scatter(
            x=nac["anio_nacimiento"] + 18,
            y=nac["nacimientos_total"],
            mode="lines+markers",
            name="Nacimientos — IESS + privados",
            line=dict(color=COLORES["Nacimientos"], width=2),
            marker=dict(size=5),
            xaxis="x2",
            hovertemplate=(
                "Nacimiento: %{customdata}<br>Graduación aprox.: %{x}<br>"
                "IESS + privados: %{y:,.0f}<extra></extra>"
            ),
            customdata=nac["anio_nacimiento"],
        )
    )
else:
    fig.add_trace(
        go.Scatter(
            x=nac["anio_nacimiento"] + 18,
            y=nac["nacimientos_total"],
            mode="lines+markers",
            name="Nacimientos — Pichincha",
            line=dict(color=COLORES["Nacimientos"], width=2),
            marker=dict(size=5),
            xaxis="x2",
            hovertemplate=(
                "Nacimiento: %{customdata}<br>Graduación aprox.: %{x}<br>"
                "Nacimientos: %{y:,.0f}<extra></extra>"
            ),
            customdata=nac["anio_nacimiento"],
        )
    )

for sostenimiento in seleccion:
    real = graduados[graduados["Sostenimiento"] == sostenimiento]
    fig.add_trace(
        go.Scatter(
            x=real["anio_egreso"],
            y=real["graduados"],
            mode="lines+markers",
            name=f"Graduados — {sostenimiento}",
            line=dict(color=COLORES[sostenimiento], width=3),
            marker=dict(size=7),
            hovertemplate=(
                "Nacimiento aprox.: %{customdata}<br>Graduación: %{x}<br>"
                "Graduados: %{y:,.0f}<extra></extra>"
            ),
            customdata=real["anio_nacimiento"],
        )
    )
    estimado = proyeccion[proyeccion["Sostenimiento"] == sostenimiento]
    if not real.empty and not estimado.empty:
        puente = pd.concat(
            [
                real.tail(1)[["anio_egreso", "graduados"]],
                estimado[["anio_egreso", "graduados"]],
            ],
            ignore_index=True,
        )
        fig.add_trace(
            go.Scatter(
                x=puente["anio_egreso"],
                y=puente["graduados"],
                mode="lines+markers",
                name=f"Proyección — {sostenimiento}",
                showlegend=False,
                line=dict(color=COLORES[sostenimiento], width=2, dash="dash"),
                marker=dict(size=6, symbol="diamond-open"),
                hovertemplate="Graduación: %{x}<br>Proyección: %{y:,.0f}<extra></extra>",
            )
        )

inicio = 2014
fin = 2035
ticks = list(range(inicio, fin + 1))
fig.update_layout(
    height=680,
    margin=dict(l=40, r=30, t=85, b=85),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.12, xanchor="left", x=0),
    plot_bgcolor="white",
    paper_bgcolor="white",
    xaxis=dict(
        title="Año de graduación",
        side="top",
        tickmode="array",
        tickvals=ticks,
        ticktext=ticks,
        tickangle=-90,
        range=[inicio - 0.5, fin + 0.5],
        showgrid=False,
    ),
    xaxis2=dict(
        title="Año de nacimiento aproximado",
        overlaying="x",
        matches="x",
        side="bottom",
        tickmode="array",
        tickvals=ticks,
        ticktext=[a - 18 for a in ticks],
        tickangle=-90,
        range=[inicio - 0.5, fin + 0.5],
        showgrid=False,
    ),
    yaxis=dict(title="Personas", rangemode="tozero", gridcolor="#E3E7EC", tickformat=","),
    shapes=[
        dict(
            type="line",
            x0=ultimo_real + 0.5,
            x1=ultimo_real + 0.5,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            line=dict(color="#B0745A", dash="dot", width=2),
        )
    ],
    annotations=[
        dict(
            x=ultimo_real + 0.65,
            y=1.02,
            xref="x",
            yref="paper",
            text="Proyección 2026–2035",
            showarrow=False,
            font=dict(color="#B0745A"),
            xanchor="left",
        )
    ],
)
st.plotly_chart(fig, width="stretch")

st.info(
    "La proyección parte del valor real de graduados de 2025 y aplica la tendencia "
    "lineal de las cohortes nacidas entre 2008 y 2017. Para Nacional, la cohorte es la "
    "suma de nacimientos en IESS y establecimientos privados; para Pichincha, el total "
    "provincial. La suavización evita que variaciones puntuales oculten la tendencia."
)

with st.expander("Ver correspondencia entre años y valores proyectados"):
    tabla = proyeccion.pivot_table(
        index=["anio_nacimiento", "anio_egreso"],
        columns="Sostenimiento",
        values="graduados",
        aggfunc="sum",
    ).reset_index()
    tabla = tabla.rename(
        columns={"anio_nacimiento": "Año de nacimiento", "anio_egreso": "Año de graduación"}
    )
    st.dataframe(tabla, hide_index=True, width="stretch")
