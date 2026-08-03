from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# =============================================================================
# CONFIGURACIÓN GENERAL
# =============================================================================

st.set_page_config(
    page_title="Dashboard Financiero del Hogar",
    page_icon="📊",
    layout="wide",
)

RUTA_BASE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "hogar_financiero_estudiante.parquet"
)
RUTA_CAPTACION = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "documentados_colegios_resumen.parquet"
)
RUTA_UNIVERSO = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "universo_colegios_bachillerato.parquet"
)

PLOTLY_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
        "autoScale2d",
    ],
}

COLOR_FONDO = "#ffffff"
COLOR_TARJETA = "#ffffff"
COLOR_TEXTO = "#1f2a37"
COLOR_AZUL = "#234e70"
COLOR_NARANJA = "#f4a261"
COLOR_VERDE = "#7fb069"
COLOR_ROJO = "#d95d39"
COLOR_GRIS = "#6b7280"
COLOR_CELESTE = "#7aa6c2"


# =============================================================================
# ESTILOS
# =============================================================================

st.markdown(
    f"""
    <style>
        .stApp {{
            background-color: {COLOR_FONDO};
            color: {COLOR_TEXTO};
        }}

        .main-title {{
            font-size: 2rem;
            font-weight: 700;
            color: {COLOR_AZUL};
            margin-bottom: 0.25rem;
        }}

        .sub-title {{
            font-size: 0.95rem;
            color: {COLOR_GRIS};
            margin-bottom: 1.2rem;
        }}

        .metric-card {{
            background: {COLOR_TARJETA};
            border-radius: 18px;
            padding: 16px 18px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.05);
            min-height: 110px;
            border: 1px solid rgba(0,0,0,0.04);
            margin-bottom: 0.75rem;
            overflow-wrap: anywhere;
        }}

        /* Las tarjetas son botones completos, no solo bloques informativos. */
        [class*="st-key-metric_card_"] button {{
            width: 100%;
            min-height: 86px;
            height: 100%;
            display: block;
            text-align: left;
            white-space: pre-wrap;
            background: {COLOR_TARJETA};
            color: {COLOR_TEXTO};
            border: 1px solid rgba(0,0,0,0.04);
            border-radius: 18px;
            padding: 10px 13px;
            box-shadow: 0 1px 7px rgba(0,0,0,0.045);
            transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;
        }}

        [class*="st-key-metric_card_"] button p {{
            margin: 0;
            color: {COLOR_GRIS};
            font-size: 0.78rem;
            line-height: 1.2;
        }}

        [class*="st-key-metric_card_"] button p strong {{
            display: block;
            margin-top: 0.35rem;
            color: {COLOR_AZUL};
            font-size: 1.22rem;
            line-height: 1.1;
        }}

        [class*="st-key-metric_card_"] button:hover {{
            color: {COLOR_TEXTO};
            border-color: {COLOR_CELESTE};
            box-shadow: 0 4px 12px rgba(35,78,112,0.12);
            transform: translateY(-1px);
        }}

        [class*="st-key-metric_card_"] button:focus {{
            color: {COLOR_TEXTO};
            border-color: {COLOR_AZUL};
            box-shadow: 0 0 0 2px rgba(35,78,112,0.18);
        }}

        .metric-label {{
            font-size: 0.88rem;
            color: {COLOR_GRIS};
            margin-bottom: 0.4rem;
        }}

        .metric-value {{
            font-size: 1.6rem;
            font-weight: 700;
            color: {COLOR_AZUL};
            line-height: 1.15;
        }}

        .metric-help {{
            font-size: 0.78rem;
            color: {COLOR_GRIS};
            margin-top: 0.35rem;
        }}

        .section-title {{
            font-size: 1.15rem;
            font-weight: 700;
            color: {COLOR_AZUL};
            margin-top: 1rem;
            margin-bottom: 1rem;
        }}

        div[data-testid="stMetric"] {{
            background: white;
            border-radius: 16px;
            padding: 12px;
        }}

        /* Separación horizontal y vertical entre filas de tarjetas y gráficos. */
        div[data-testid="stHorizontalBlock"] {{
            flex-wrap: nowrap;
            column-gap: 1rem;
            row-gap: 1.25rem;
            margin-bottom: 1.25rem;
        }}

        div[data-testid="stPlotlyChart"] {{
            background: {COLOR_TARJETA};
            border: 1px solid rgba(0,0,0,0.04);
            border-radius: 16px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.04);
            padding: 0.5rem;
            margin-top: 0.35rem;
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}

        div[data-testid="stTabContent"] {{
            padding-top: 1rem;
            padding-bottom: 2rem;
        }}

        /* Los filtros generales permanecen compactos en una sola fila. */
        .st-key-general_filters div[data-testid="stHorizontalBlock"] {{
            flex-wrap: nowrap;
            column-gap: 0.75rem;
            margin-bottom: 1rem;
        }}

        .st-key-general_filters div[data-testid="stSelectbox"] label p {{
            white-space: nowrap;
        }}

        @media (max-width: 768px) {{
            div[data-testid="stHorizontalBlock"] {{
                column-gap: 0.75rem;
                margin-bottom: 1rem;
            }}

            div[data-testid="stPlotlyChart"] {{
                margin-bottom: 1rem;
            }}
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# UTILIDADES
# =============================================================================

def porcentaje(valor: float | int | None) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    return f"{valor:.1%}"


def moneda(valor: float | int | None) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    return f"USD {valor:,.0f}"


def numero(valor: float | int | None, decimales: int = 1) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    return f"{valor:,.{decimales}f}"


def safe_div(numerador, denominador):
    numerador = pd.to_numeric(numerador, errors="coerce")
    denominador = pd.to_numeric(denominador, errors="coerce")
    resultado = numerador / denominador.where(denominador != 0, np.nan)
    return resultado.replace([np.inf, -np.inf], np.nan)


def mostrar_tarjeta(
    titulo: str,
    valor: str,
    ayuda: str = "",
    detalle_id: str | None = None,
) -> None:
    """Dibuja una tarjeta clicable y conserva la selección entre reruns."""
    detalle_id = detalle_id or titulo.lower().replace(" ", "_")
    contenedor = st.container(key=f"metric_card_{detalle_id}")
    etiqueta = f"{titulo}\n\n**{valor}**"
    tooltip = f"{ayuda} Haz clic para ver el detalle por colegio.".strip()
    if contenedor.button(
        etiqueta,
        key=f"btn_{detalle_id}",
        help=tooltip,
        width="stretch",
    ):
        st.session_state["tarjeta_detalle_activa"] = detalle_id


DETALLES_TARJETAS = {
    "segmento_predominante": ("SegmentoFinancieroHogar", "composicion", "Composición financiera dentro de cada colegio", "porcentaje"),
    "estable": ("FlagSegmentoEstable", "media", "% hogares estables por colegio", "porcentaje"),
    "justo": ("FlagSegmentoJusto", "media", "% viviendo con lo justo por colegio", "porcentaje"),
    "presion_alta": ("FlagSegmentoPresion", "media", "% con presión financiera alta por colegio", "porcentaje"),
    "ahogado": ("FlagSegmentoAhogado", "media", "% ahogados en deuda por colegio", "porcentaje"),
    "severo": ("FlagSegmentoSevero", "media", "% con deterioro severo por colegio", "porcentaje"),
    "sin_ingresos_deuda": ("FlagSinIngresosNiDeuda", "media", "% sin ingresos ni deuda por colegio", "porcentaje"),
    "caida_ingreso": ("FlagCaidaIngresoCalc", "media", "% con caída de ingresos por colegio", "porcentaje"),
    "baja_quintil": ("FlagBajaQuintilCalc", "media", "% que bajaron de quintil por colegio", "porcentaje"),
    "sube_quintil": ("FlagSubeQuintilCalc", "media", "% que subieron de quintil por colegio", "porcentaje"),
    "ingreso_mediano": ("IngresoMensualHogarActual", "mediana", "Ingreso mensual mediano por colegio", "moneda"),
    "ambos_padres": ("FlagAmbosPadresTrabajan", "media", "% con ambos padres trabajando por colegio", "porcentaje"),
    "solo_padre": ("FlagSoloPadreTrabaja", "media", "% donde solo trabaja el padre por colegio", "porcentaje"),
    "solo_madre": ("FlagSoloMadreTrabaja", "media", "% donde solo trabaja la madre por colegio", "porcentaje"),
    "ninguno_trabaja": ("FlagNingunPadreTrabaja", "media", "% donde ningún padre trabaja por colegio", "porcentaje"),
    "con_deuda": ("FlagTieneDeuda", "media", "% de hogares con deuda por colegio", "porcentaje"),
    "meses_deuda": ("MesesIngresoEquivalentesDeuda", "mediana", "Meses de ingreso equivalentes por colegio", "numero"),
    "deuda_mayor_ingreso": ("FlagDeudaMayorIngresoAnual", "media", "% con deuda mayor al ingreso anual por colegio", "porcentaje"),
    "indice_presion": ("IndicePresionDeudaIngresoAnual", "mediana", "Índice mediano de presión por colegio", "numero"),
    "mora": ("FlagTieneMora", "media", "% de hogares con mora por colegio", "porcentaje"),
    "demanda": ("FlagDemandaJudicial", "media", "% con demanda judicial por colegio", "porcentaje"),
    "castigada": ("FlagCarteraCastigada", "media", "% con cartera castigada por colegio", "porcentaje"),
    "mala_calif": ("MontoDeudaCalificacionCritica", "ratio_deuda", "% de deuda mal calificada por colegio", "porcentaje"),
    "deterioro": ("MontoExposicionCritica", "ratio_deuda", "Índice de deterioro crediticio por colegio", "porcentaje"),
    "ingreso_colegio": ("PctIngresoAnualEnColegioCalc", "mediana", "% del ingreso anual gastado en colegio", "porcentaje"),
    "ingreso_udla": ("PctIngresoAnualEnUDLACalc", "mediana", "% del ingreso anual requerido por UDLA", "porcentaje"),
    "brecha_esfuerzo": ("BrechaEsfuerzo", "mediana", "Brecha de esfuerzo por colegio", "porcentaje"),
    "gap_udla": ("GapPctUDLAvsColegioCalc", "mediana", "% en que UDLA es más cara por colegio", "porcentaje"),
}

# Las tarjetas repetidas del resumen mantienen claves de widget independientes.
for _alias, _origen in {
    "resumen_ingreso": "ingreso_mediano",
    "resumen_presion": "indice_presion",
    "resumen_mala_calif": "mala_calif",
    "resumen_caida": "caida_ingreso",
    "resumen_mora": "mora",
    "resumen_udla": "ingreso_udla",
    "resumen_sin_ingresos": "sin_ingresos_deuda",
    "sin_ingresos_deuda_deuda": "sin_ingresos_deuda",
}.items():
    DETALLES_TARJETAS[_alias] = DETALLES_TARJETAS[_origen]


def fig_detalle_tarjeta(df: pd.DataFrame, detalle_id: str) -> go.Figure:
    """Construye el desglose por colegio de la tarjeta seleccionada."""
    hogares = base_hogar(df).copy()
    if hogares.empty or detalle_id not in DETALLES_TARJETAS:
        return go.Figure()

    columna, agregacion, titulo, formato = DETALLES_TARJETAS[detalle_id]
    total_hogares = len(hogares)
    segmentos = {
        "FlagSegmentoEstable": "Hogar estable",
        "FlagSegmentoJusto": "Viviendo con lo justo",
        "FlagSegmentoPresion": "Presión financiera alta",
        "FlagSegmentoAhogado": "Ahogado en deuda",
        "FlagSegmentoSevero": "Deterioro severo",
    }
    if columna in segmentos:
        hogares[columna] = (hogares["SegmentoFinancieroHogar"] == segmentos[columna]).astype(float)
    elif columna == "BrechaEsfuerzo":
        hogares[columna] = (
            pd.to_numeric(hogares["PctIngresoAnualEnUDLACalc"], errors="coerce")
            - pd.to_numeric(hogares["PctIngresoAnualEnColegioCalc"], errors="coerce")
        )

    hogares["Colegio"] = hogares["Colegio"].fillna("Sin colegio informado").astype(str)
    top = hogares["Colegio"].value_counts().head(15).index
    work = hogares[hogares["Colegio"].isin(top)].copy()
    if agregacion == "composicion":
        composicion = (
            work.groupby(["Colegio", columna], dropna=False)
            .size().rename("Hogares").reset_index()
        )
        composicion["TotalColegio"] = composicion.groupby("Colegio")["Hogares"].transform("sum")
        composicion["Porcentaje"] = composicion["Hogares"] / composicion["TotalColegio"]
        orden_colegios = (
            work["Colegio"].value_counts().sort_values(ascending=True).index.tolist()
        )
        fig = px.bar(
            composicion,
            x="Porcentaje",
            y="Colegio",
            color=columna,
            orientation="h",
            custom_data=["Hogares", "TotalColegio"],
        )
        fig.update_xaxes(tickformat=".0%", title=None)
        fig.update_yaxes(
            title=None,
            categoryorder="array",
            categoryarray=orden_colegios,
        )
        fig.update_traces(
            hovertemplate=(
                f"<b>%{{y}}</b><br>Participación: %{{x:.1%}}<br>"
                "Hogares del segmento: %{customdata[0]:,.0f} de %{customdata[1]:,.0f}<br>"
                f"Total general filtrado: {total_hogares:,.0f}<extra></extra>"
            )
        )
        fig.update_layout(
            title=dict(text=titulo, x=0.02), barmode="stack",
            height=max(400, 32 * composicion["Colegio"].nunique() + 100),
            margin=dict(l=10, r=20, t=60, b=35), paper_bgcolor="white", plot_bgcolor="white",
            legend_title_text="Segmento financiero",
        )
        return agregar_total_hogares(fig, df)
    filas = []
    for colegio, grupo in work.groupby("Colegio", dropna=False):
        valores = pd.to_numeric(grupo[columna], errors="coerce")
        if agregacion == "ratio_deuda":
            valor = valores.fillna(0).sum() / pd.to_numeric(
                grupo["DeudaTotalHogar"], errors="coerce"
            ).fillna(0).sum() if pd.to_numeric(grupo["DeudaTotalHogar"], errors="coerce").fillna(0).sum() else np.nan
        elif agregacion == "media":
            valor = valores.mean()
        else:
            valor = valores.median()
        filas.append({
            "Colegio": colegio,
            "Valor": valor,
            "Hogares": len(grupo),
            "Casos": valores.fillna(0).sum() if agregacion == "media" else np.nan,
            "BaseIndicador": valores.notna().sum() if agregacion == "media" else np.nan,
            "Cluster": grupo["Cluster"].dropna().astype(str).mode().iat[0] if not grupo["Cluster"].dropna().empty else "Sin cluster",
        })
    detalle = pd.DataFrame(filas).dropna(subset=["Valor"]).sort_values("Valor")
    fig = px.bar(
        detalle,
        x="Valor",
        y="Colegio",
        orientation="h",
        color="Cluster",
        custom_data=["Hogares", "Cluster", "Casos", "BaseIndicador"],
        text="Valor",
    )
    if formato == "porcentaje":
        fig.update_xaxes(tickformat=".0%")
        fig.update_traces(texttemplate="%{text:.1%}")
    elif formato == "moneda":
        fig.update_xaxes(tickprefix="USD ", tickformat=",")
        fig.update_traces(texttemplate="USD %{text:,.0f}")
    else:
        fig.update_traces(texttemplate="%{text:.2f}")
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=detalle["Colegio"].tolist(),
    )
    if agregacion == "media":
        hover = (
            f"<b>%{{y}}</b><br>Valor: %{{x:.1%}}<br>"
            "Hogares con la condición: %{customdata[2]:,.0f} de %{customdata[3]:,.0f}<br>"
            f"Hogares del colegio: %{{customdata[0]:,.0f}} de {total_hogares:,.0f} del total general<br>"
            "Cluster: %{customdata[1]}<extra></extra>"
        )
    else:
        hover = (
            f"<b>%{{y}}</b><br>Valor: %{{x}}<br>"
            f"Hogares del colegio: %{{customdata[0]:,.0f}} de {total_hogares:,.0f} del total general<br>"
            "Cluster: %{customdata[1]}<extra></extra>"
        )
    fig.update_traces(hovertemplate=hover)
    fig.update_layout(
        title=dict(text=titulo, x=0.02),
        xaxis_title=None,
        yaxis_title=None,
        height=max(400, 32 * len(detalle) + 100),
        margin=dict(l=10, r=20, t=60, b=35),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend_title_text="Cluster",
    )
    return agregar_total_hogares(fig, df)


def mostrar_detalle_tarjetas(df: pd.DataFrame, ids: list[str], key: str) -> None:
    detalle_id = st.session_state.get("tarjeta_detalle_activa")
    if detalle_id not in ids:
        return
    st.caption("Detalle de la tarjeta seleccionada · 15 colegios con más hogares")
    st.plotly_chart(
        fig_detalle_tarjeta(df, detalle_id),
        width="stretch",
        config=PLOTLY_CONFIG,
        key=f"detalle_{key}_{detalle_id}",
    )


def preparar_grafico(fig: go.Figure, df: pd.DataFrame) -> go.Figure:
    """Añade el total solo si la figura todavía no lo incluye."""
    anotaciones = list(fig.layout.annotations or [])
    if not any(str(anotacion.text).startswith("Total:") for anotacion in anotaciones):
        agregar_total_hogares(fig, df)
    return fig


def weighted_ratio(df: pd.DataFrame, numerador: str, denominador: str) -> float:
    n = pd.to_numeric(df[numerador], errors="coerce").fillna(0).sum()
    d = pd.to_numeric(df[denominador], errors="coerce").fillna(0).sum()
    if d == 0:
        return np.nan
    return n / d


def agg_median(series: pd.Series) -> float:
    serie = pd.to_numeric(series, errors="coerce").dropna()
    if serie.empty:
        return np.nan
    return float(serie.median())


def agregar_total_hogares(fig: go.Figure, df: pd.DataFrame) -> go.Figure:
    """Muestra el denominador vigente después de aplicar los filtros."""
    total = len(base_hogar(df))
    fig.add_annotation(
        text=f"Total: {total:,.0f} hogares",
        x=1,
        y=1.08,
        xref="paper",
        yref="paper",
        xanchor="right",
        yanchor="bottom",
        showarrow=False,
        font=dict(size=11, color=COLOR_GRIS),
        bgcolor="rgba(255,255,255,0.82)",
    )
    return fig


# =============================================================================
# CARGA DE DATOS
# =============================================================================

@st.cache_data(show_spinner=False)
def cargar_base() -> pd.DataFrame:
    if not RUTA_BASE.exists():
        raise FileNotFoundError(
            f"No se encontró la base final en: {RUTA_BASE}"
        )

    df = pd.read_parquet(RUTA_BASE)

    # -------------------------------------------------------------------------
    # Estandarización básica
    # -------------------------------------------------------------------------
    for col in [
        "AnioAnalisis",
        "Periodo",
        "Cluster",
        "Colegio",
        "Tipo",
        "Carrera",
        "CodAMIE",
        "Cedula",
        "QuintilActual",
        "PeorCalificacionHogar",
        "EstadoEmpleoHogarActual",
    ]:
        if col in df.columns:
            df[col] = df[col].astype("string")

    def moda_primera(serie: pd.Series):
        valores = serie.dropna()
        if valores.empty:
            return pd.NA
        moda = valores.mode()
        return moda.iloc[0] if not moda.empty else valores.iloc[0]

    # Atributos territoriales y comerciales compartidos con Captación/Mercado.
    if RUTA_CAPTACION.exists():
        captacion = pd.read_parquet(RUTA_CAPTACION)
        captacion["codigo_colegio"] = captacion["codigo_colegio"].astype("string").str.strip()

        atributos_colegio = (
            captacion.groupby("codigo_colegio", as_index=False)
            .agg(
                Provincia=("provincia", moda_primera),
                Canton=("canton", moda_primera),
                Sostenimiento=("sostenimiento", moda_primera),
                ClusterCaptacion=("cluster", moda_primera),
                RangoPension=("rango_pension", moda_primera),
            )
        )
        df["CodAMIE"] = df["CodAMIE"].astype("string").str.strip()
        df = df.merge(
            atributos_colegio,
            left_on="CodAMIE",
            right_on="codigo_colegio",
            how="left",
        ).drop(columns=["codigo_colegio"])
        df["Cluster"] = df["Cluster"].fillna(df["ClusterCaptacion"])
        df = df.drop(columns=["ClusterCaptacion"])
    else:
        for columna in ["Provincia", "Canton", "Sostenimiento", "RangoPension"]:
            df[columna] = pd.NA

    if RUTA_UNIVERSO.exists():
        universo = pd.read_parquet(RUTA_UNIVERSO)
        universo["AMIE"] = universo["AMIE"].astype("string").str.strip()
        atributos_universo = (
            universo.groupby("AMIE", as_index=False)
            .agg(
                TipoEducacion=("tipo_educacion", moda_primera),
                ZonaPlanificacion=("zona", moda_primera),
                Parroquia=("parroquia", moda_primera),
                Area=("area", moda_primera),
                Jurisdiccion=("jurisdiccion", moda_primera),
                RegimenEscolar=("regimen_escolar", moda_primera),
            )
        )
        df = df.merge(
            atributos_universo,
            left_on="CodAMIE",
            right_on="AMIE",
            how="left",
        ).drop(columns=["AMIE"])
    else:
        for columna in [
            "TipoEducacion", "ZonaPlanificacion", "Parroquia", "Area",
            "Jurisdiccion", "RegimenEscolar",
        ]:
            df[columna] = pd.NA

    # -------------------------------------------------------------------------
    # Flags y variables derivadas
    # -------------------------------------------------------------------------
    df["FlagCaidaIngresoCalc"] = pd.to_numeric(
        df.get("VariacionIngresoMensualUSD", 0),
        errors="coerce",
    ).fillna(0).lt(0).astype(int)

    df["FlagSubioIngresoCalc"] = pd.to_numeric(
        df.get("VariacionIngresoMensualUSD", 0),
        errors="coerce",
    ).fillna(0).gt(0).astype(int)

    df["FlagBajaQuintilCalc"] = pd.to_numeric(
        df.get("CambioQuintil", 0),
        errors="coerce",
    ).fillna(0).lt(0).astype(int)

    df["FlagSubeQuintilCalc"] = pd.to_numeric(
        df.get("CambioQuintil", 0),
        errors="coerce",
    ).fillna(0).gt(0).astype(int)

    df["FlagAmbosPadresTrabajan"] = pd.to_numeric(
        df.get("NumeroPadresConEmpleoFormalActual", 0),
        errors="coerce",
    ).fillna(0).eq(2).astype(int)

    df["FlagNingunPadreTrabaja"] = pd.to_numeric(
        df.get("NumeroPadresConEmpleoFormalActual", 0),
        errors="coerce",
    ).fillna(0).eq(0).astype(int)

    estado_empleo = df.get("EstadoEmpleoHogarActual", pd.Series(index=df.index, dtype="string")).astype("string").fillna("")

    df["FlagSoloPadreTrabaja"] = estado_empleo.str.contains("SOLO PADRE", case=False, na=False).astype(int)
    df["FlagSoloMadreTrabaja"] = estado_empleo.str.contains("SOLO MADRE", case=False, na=False).astype(int)

    df["FlagTieneDeuda"] = pd.to_numeric(
        df.get("DeudaTotalHogar", 0),
        errors="coerce",
    ).fillna(0).gt(0).astype(int)

    df["FlagTieneMora"] = pd.to_numeric(
        df.get("SaldoVencido", 0),
        errors="coerce",
    ).fillna(0).gt(0).astype(int)

    df["FlagSinIngresosNiDeuda"] = (
        pd.to_numeric(df.get("IngresoMensualHogarActual", 0), errors="coerce").fillna(0).eq(0)
        & pd.to_numeric(df.get("DeudaTotalHogar", 0), errors="coerce").fillna(0).eq(0)
    ).astype(int)

    df["GapPctUDLAvsColegioCalc"] = safe_div(
        pd.to_numeric(df.get("CostoUDLAAnual", np.nan), errors="coerce")
        - pd.to_numeric(df.get("CostoColegioAnual", np.nan), errors="coerce"),
        pd.to_numeric(df.get("CostoColegioAnual", np.nan), errors="coerce"),
    )

    df["PctIngresoAnualEnColegioCalc"] = safe_div(
        pd.to_numeric(df.get("CostoColegioAnual", np.nan), errors="coerce"),
        pd.to_numeric(df.get("IngresoAnualHogarActual", np.nan), errors="coerce"),
    )

    df["PctIngresoAnualEnUDLACalc"] = safe_div(
        pd.to_numeric(df.get("CostoUDLAAnual", np.nan), errors="coerce"),
        pd.to_numeric(df.get("IngresoAnualHogarActual", np.nan), errors="coerce"),
    )

    df["BrechaEsfuerzoCalc"] = (
        pd.to_numeric(df["PctIngresoAnualEnUDLACalc"], errors="coerce")
        - pd.to_numeric(df["PctIngresoAnualEnColegioCalc"], errors="coerce")
    )

    df["PeorCalificacionHogar"] = df["PeorCalificacionHogar"].fillna("Sin deuda reportada")

    # -------------------------------------------------------------------------
    # Segmentación financiera del hogar
    # -------------------------------------------------------------------------
    # Versión consolidada: deuda E+, judicial y castigada forman deuda crítica.
    df["SegmentoFinancieroHogar"] = construir_segmento_hogar(df)

    return df


def construir_segmento_hogar(df: pd.DataFrame) -> pd.Series:
    ingreso = pd.to_numeric(df.get("IngresoMensualHogarActual", 0), errors="coerce").fillna(0)
    deuda = pd.to_numeric(df.get("DeudaTotalHogar", 0), errors="coerce").fillna(0)
    presion = pd.to_numeric(df.get("IndicePresionDeudaIngresoAnual", np.nan), errors="coerce")
    pct_mora = pd.to_numeric(df.get("PorcentajeMoraAmpliada", np.nan), errors="coerce")
    deuda_critica = pd.to_numeric(
        df.get("IndiceDeterioroCrediticio", np.nan),
        errors="coerce",
    )
    flag_demanda = pd.to_numeric(df.get("FlagDemandaJudicial", 0), errors="coerce").fillna(0).eq(1)
    flag_castigada = pd.to_numeric(df.get("FlagCarteraCastigada", 0), errors="coerce").fillna(0).eq(1)
    flag_deuda_sin_ingreso = pd.to_numeric(df.get("FlagDeudaSinIngresoFormal", 0), errors="coerce").fillna(0).eq(1)
    flag_caida = pd.to_numeric(df.get("FlagCaidaIngresoCalc", 0), errors="coerce").fillna(0).eq(1)
    cambio_quintil = pd.to_numeric(df.get("CambioQuintil", 0), errors="coerce").fillna(0)
    peor_calif = df.get("PeorCalificacionHogar", pd.Series(index=df.index, dtype="string")).astype("string").fillna("Sin deuda reportada")
    estado_cambio = df.get("EstadoCambioIngreso", pd.Series(index=df.index, dtype="string")).astype("string").fillna("")
    ningun_padre = pd.to_numeric(df.get("FlagNingunPadreTrabaja", 0), errors="coerce").fillna(0).eq(1)

    segmento = pd.Series("Situación financiera intermedia", index=df.index, dtype="string")

    cond_sin_ingresos_ni_deuda = ingreso.eq(0) & deuda.eq(0)
    segmento.loc[cond_sin_ingresos_ni_deuda] = "Sin ingresos ni deuda"

    cond_deterioro_severo = (flag_demanda | flag_castigada)
    segmento.loc[cond_deterioro_severo] = "Deterioro severo"

    cond_ahogado = (
        ~cond_deterioro_severo
        & (
            presion.ge(2)
            | deuda_critica.ge(0.60)
            | pct_mora.ge(0.50)
        )
    )
    segmento.loc[cond_ahogado] = "Ahogado en deuda"

    cond_presion = (
        ~(cond_deterioro_severo | cond_ahogado)
        & (
            flag_deuda_sin_ingreso
            | (ningun_padre & deuda.gt(0))
            | presion.ge(1)
            | deuda_critica.ge(0.30)
            | pct_mora.ge(0.20)
        )
    )
    segmento.loc[cond_presion] = "Presión financiera alta"

    cond_justo = (
        ~(cond_deterioro_severo | cond_ahogado | cond_presion | cond_sin_ingresos_ni_deuda)
        & ingreso.gt(0)
        & (flag_caida | cambio_quintil.lt(0))
        & presion.ge(0.50)
        & presion.lt(1)
        & deuda_critica.lt(0.30)
        & ~flag_demanda
        & ~flag_castigada
        & ~peor_calif.isin(["E"])
    )
    segmento.loc[cond_justo] = "Viviendo con lo justo"

    cond_estable = (
        ~(cond_deterioro_severo | cond_ahogado | cond_presion | cond_justo | cond_sin_ingresos_ni_deuda)
        & ingreso.gt(0)
        & estado_cambio.str.contains("AUMENT", case=False, na=False)
        & peor_calif.isin(["A1", "Sin deuda reportada"])
        & presion.lt(0.50)
        & deuda_critica.fillna(0).eq(0)
        & pct_mora.fillna(0).eq(0)
    )
    segmento.loc[cond_estable] = "Hogar estable"

    return segmento


# =============================================================================
# FILTROS
# =============================================================================

CUADRANTES_MERCADO = [
    "Mercado crece + UDLA crece",
    "Mercado cae + UDLA crece",
    "Mercado crece + UDLA cae",
    "Mercado cae + UDLA cae",
]


@st.cache_data(show_spinner=False)
def calcular_cuadrantes_mercado(
    anios_base: tuple[str, ...],
    anios_comparados: tuple[str, ...],
) -> pd.DataFrame:
    if not anios_base or not anios_comparados or not RUTA_CAPTACION.exists():
        return pd.DataFrame(columns=["CodAMIE", "CuadranteMercado"])

    mercado = pd.read_parquet(RUTA_CAPTACION)
    mercado["anio"] = mercado["PeriodoBanner_Sales"].astype(str).str[:4]
    mercado["codigo_colegio"] = mercado["codigo_colegio"].astype("string").str.strip()
    anual = (
        mercado.groupby(["anio", "codigo_colegio"], as_index=False)
        .agg(
            graduados=("graduados_total", "first"),
            documentados=("documentados", "sum"),
        )
    )
    base = (
        anual[anual["anio"].isin(anios_base)]
        .groupby("codigo_colegio")[["graduados", "documentados"]]
        .sum()
    )
    comparado = (
        anual[anual["anio"].isin(anios_comparados)]
        .groupby("codigo_colegio")[["graduados", "documentados"]]
        .sum()
    )
    comunes = base.index.intersection(comparado.index)
    if comunes.empty:
        return pd.DataFrame(columns=["CodAMIE", "CuadranteMercado"])

    resultado = pd.DataFrame({
        "CodAMIE": comunes,
        "graduados_base": base.loc[comunes, "graduados"],
        "graduados_comparado": comparado.loc[comunes, "graduados"],
        "documentados_base": base.loc[comunes, "documentados"],
        "documentados_comparado": comparado.loc[comunes, "documentados"],
    }).reset_index(drop=True)
    resultado["cambio_graduados"] = safe_div(
        resultado["graduados_comparado"] - resultado["graduados_base"],
        resultado["graduados_base"],
    )
    resultado["cambio_documentados"] = safe_div(
        resultado["documentados_comparado"] - resultado["documentados_base"],
        resultado["documentados_base"],
    )
    resultado = resultado.dropna(subset=["cambio_graduados", "cambio_documentados"])
    resultado["CuadranteMercado"] = np.select(
        [
            (resultado["cambio_graduados"] >= 0) & (resultado["cambio_documentados"] >= 0),
            (resultado["cambio_graduados"] < 0) & (resultado["cambio_documentados"] >= 0),
            (resultado["cambio_graduados"] >= 0) & (resultado["cambio_documentados"] < 0),
        ],
        CUADRANTES_MERCADO[:3],
        default=CUADRANTES_MERCADO[3],
    )
    return resultado[["CodAMIE", "CuadranteMercado"]]


def aplicar_filtros(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    filtros_container = st.container(key="general_filters")
    filtros_container.markdown("**Filtros generales**")
    fila_comparacion = filtros_container.columns(5, gap="small")
    fila_filtros_1 = filtros_container.columns(4, gap="small")
    fila_filtros_2 = filtros_container.columns(4, gap="small")
    fila_filtros_3 = filtros_container.columns(5, gap="small")
    columnas_filtros = [*fila_filtros_1, *fila_filtros_2, *fila_filtros_3]
    df_filtrado = df.copy()

    anios_financieros = sorted(
        df["AnioAnalisis"].dropna().astype(str).unique().tolist(), key=str
    )
    with fila_comparacion[0]:
        anios_financieros_sel = st.multiselect("Año", anios_financieros)
    if anios_financieros_sel:
        df_filtrado = df_filtrado[
            df_filtrado["AnioAnalisis"].astype(str).isin(anios_financieros_sel)
        ]

    tipos_disponibles = sorted(
        df_filtrado["Tipo"].dropna().astype(str).unique().tolist(), key=str
    )
    with fila_comparacion[1]:
        tipos_sel = st.multiselect("Tipo", tipos_disponibles)
    if tipos_sel:
        df_filtrado = df_filtrado[df_filtrado["Tipo"].astype(str).isin(tipos_sel)]

    mercado_anios = pd.read_parquet(
        RUTA_CAPTACION, columns=["PeriodoBanner_Sales"]
    )["PeriodoBanner_Sales"].astype(str).str[:4]
    mercado_anios = sorted(mercado_anios.dropna().unique().tolist())
    anio_comparado_default = mercado_anios[-2] if len(mercado_anios) > 1 else mercado_anios[-1]
    anio_base_default = mercado_anios[-3] if len(mercado_anios) > 2 else mercado_anios[0]

    with fila_comparacion[2]:
        anios_base_sel = st.multiselect(
            "Año(s) base", mercado_anios, default=[anio_base_default]
        )
    anios_comparables = [anio for anio in mercado_anios if anio not in anios_base_sel]
    default_comparado = (
        [anio_comparado_default]
        if anio_comparado_default in anios_comparables
        else anios_comparables[-1:]
    )
    with fila_comparacion[3]:
        anios_comparados_sel = st.multiselect(
            "Año(s) comparado(s)", anios_comparables, default=default_comparado
        )
    with fila_comparacion[4]:
        cuadrantes_sel = st.multiselect(
            "Cuadrante", CUADRANTES_MERCADO, default=CUADRANTES_MERCADO
        )

    if (
        anios_base_sel
        and anios_comparados_sel
        and cuadrantes_sel
        and set(cuadrantes_sel) != set(CUADRANTES_MERCADO)
    ):
        cuadrantes_colegio = calcular_cuadrantes_mercado(
            tuple(anios_base_sel), tuple(anios_comparados_sel)
        )
        codigos_cuadrante = set(
            cuadrantes_colegio.loc[
                cuadrantes_colegio["CuadranteMercado"].isin(cuadrantes_sel), "CodAMIE"
            ].astype(str)
        )
        df_filtrado = df_filtrado[
            df_filtrado["CodAMIE"].astype(str).isin(codigos_cuadrante)
        ]

    configuracion_filtros = [
        ("Colegio", "Colegio"),
        ("Periodo", "Periodo"),
        ("Tipo de educación", "TipoEducacion"),
        ("Zona de planificación", "ZonaPlanificacion"),
        ("Provincia", "Provincia"),
        ("Cantón", "Canton"),
        ("Parroquia", "Parroquia"),
        ("Urbano/Rural", "Area"),
        ("Sostenimiento", "Sostenimiento"),
        ("Intercultural/Intercultural bilingüe", "Jurisdiccion"),
        ("Régimen escolar", "RegimenEscolar"),
        ("Cluster", "Cluster"),
        ("Rango pensión", "RangoPension"),
    ]
    selecciones = {}
    for columna_ui, (etiqueta, columna_df) in zip(columnas_filtros, configuracion_filtros):
        opciones = sorted(
            df_filtrado[columna_df].dropna().astype(str).unique().tolist(),
            key=str,
        )
        with columna_ui:
            seleccion = st.multiselect(etiqueta, opciones)
        selecciones[columna_df] = seleccion
        if seleccion:
            df_filtrado = df_filtrado[df_filtrado[columna_df].astype(str).isin(seleccion)]

    periodo_sel = selecciones["Periodo"]
    colegio_sel = selecciones["Colegio"]
    cluster_sel = selecciones["Cluster"]
    anios_periodos = {str(periodo)[:4] for periodo in periodo_sel}
    if len(anios_financieros_sel) == 1:
        anio_filtro_compatibilidad = anios_financieros_sel[0]
    elif len(anios_periodos) == 1:
        anio_filtro_compatibilidad = next(iter(anios_periodos))
    else:
        anio_filtro_compatibilidad = "Todos"

    filtros = {
        "anio": anio_filtro_compatibilidad,
        "periodo": periodo_sel[0] if len(periodo_sel) == 1 else "Todos",
        "tipo": tipos_sel[0] if len(tipos_sel) == 1 else "Todos",
        "cluster": cluster_sel[0] if len(cluster_sel) == 1 else "Todos",
        "colegio": colegio_sel[0] if len(colegio_sel) == 1 else "Todos",
    }

    return df_filtrado, filtros


# =============================================================================
# RESÚMENES
# =============================================================================

def base_hogar(df: pd.DataFrame) -> pd.DataFrame:
    if "IdHogarAnio" not in df.columns:
        return df.copy()
    return (
        df.sort_values(by=["IdHogarAnio"])
        .drop_duplicates(subset=["IdHogarAnio"], keep="first")
        .copy()
    )


def resumen_general_hogares(df: pd.DataFrame) -> dict:
    hogares = base_hogar(df)

    resumen = {
        "hogares": len(hogares),
        "pct_caida_ingreso": hogares["FlagCaidaIngresoCalc"].mean(),
        "pct_baja_quintil": hogares["FlagBajaQuintilCalc"].mean(),
        "pct_sube_quintil": hogares["FlagSubeQuintilCalc"].mean(),
        "pct_ambos_padres": hogares["FlagAmbosPadresTrabajan"].mean(),
        "pct_solo_padre": hogares["FlagSoloPadreTrabaja"].mean(),
        "pct_solo_madre": hogares["FlagSoloMadreTrabaja"].mean(),
        "pct_ninguno": hogares["FlagNingunPadreTrabaja"].mean(),
        "ingreso_mediano": agg_median(hogares["IngresoMensualHogarActual"]),
        "pct_con_deuda": hogares["FlagTieneDeuda"].mean(),
        "pct_mora": hogares["FlagTieneMora"].mean(),
        "pct_demanda": pd.to_numeric(hogares.get("FlagDemandaJudicial", 0), errors="coerce").fillna(0).mean(),
        "pct_castigada": pd.to_numeric(hogares.get("FlagCarteraCastigada", 0), errors="coerce").fillna(0).mean(),
        "pct_deuda_mayor_ingreso": pd.to_numeric(hogares.get("FlagDeudaMayorIngresoAnual", 0), errors="coerce").fillna(0).mean(),
        "meses_equiv_mediana": agg_median(hogares["MesesIngresoEquivalentesDeuda"]),
        "idx_deterioro_ponderado": weighted_ratio(hogares, "MontoExposicionCritica", "DeudaTotalHogar"),
        "pct_deuda_mala_calif_ponderado": weighted_ratio(hogares, "MontoDeudaCalificacionCritica", "DeudaTotalHogar"),
        "idx_presion_mediano": agg_median(hogares["IndicePresionDeudaIngresoAnual"]),
        "pct_sin_ingresos_ni_deuda": hogares["FlagSinIngresosNiDeuda"].mean(),
        "pct_ingreso_colegio": agg_median(hogares["PctIngresoAnualEnColegioCalc"]),
        "pct_ingreso_udla": agg_median(hogares["PctIngresoAnualEnUDLACalc"]),
        "gap_pct_udla": agg_median(hogares["GapPctUDLAvsColegioCalc"]),
    }

    return resumen


def resumen_por_colegio(df: pd.DataFrame) -> pd.DataFrame:
    hogares = base_hogar(df)

    group_cols = ["Colegio", "Cluster"]
    if hogares.empty:
        return pd.DataFrame(columns=group_cols)

    rows = []
    for (colegio, cluster), g in hogares.groupby(group_cols, dropna=False):
        rows.append({
            "Colegio": colegio,
            "Cluster": cluster,
            "Hogares": len(g),
            "PctCaidaIngreso": g["FlagCaidaIngresoCalc"].mean(),
            "PctSubeIngreso": g["FlagSubioIngresoCalc"].mean(),
            "PctBajaQuintil": g["FlagBajaQuintilCalc"].mean(),
            "PctSubeQuintil": g["FlagSubeQuintilCalc"].mean(),
            "PctAmbosPadres": g["FlagAmbosPadresTrabajan"].mean(),
            "PctSoloPadre": g["FlagSoloPadreTrabaja"].mean(),
            "PctSoloMadre": g["FlagSoloMadreTrabaja"].mean(),
            "PctNinguno": g["FlagNingunPadreTrabaja"].mean(),
            "IngresoMediano": agg_median(g["IngresoMensualHogarActual"]),
            "PctConDeuda": g["FlagTieneDeuda"].mean(),
            "PctMora": g["FlagTieneMora"].mean(),
            "PctDemandaJudicial": pd.to_numeric(g.get("FlagDemandaJudicial", 0), errors="coerce").fillna(0).mean(),
            "PctCarteraCastigada": pd.to_numeric(g.get("FlagCarteraCastigada", 0), errors="coerce").fillna(0).mean(),
            "PctDeudaMayorIngreso": pd.to_numeric(g.get("FlagDeudaMayorIngresoAnual", 0), errors="coerce").fillna(0).mean(),
            "MesesIngresoEquivMediana": agg_median(g["MesesIngresoEquivalentesDeuda"]),
            "IndicePresionMediano": agg_median(g["IndicePresionDeudaIngresoAnual"]),
            "IndiceDeterioroPonderado": weighted_ratio(g, "MontoExposicionCritica", "DeudaTotalHogar"),
            "PctDeudaMalaCalifPonderado": weighted_ratio(g, "MontoDeudaCalificacionCritica", "DeudaTotalHogar"),
            "PctSinIngresosNiDeuda": g["FlagSinIngresosNiDeuda"].mean(),
            "PctIngresoColegioMediano": agg_median(g["PctIngresoAnualEnColegioCalc"]),
            "PctIngresoUDLAMediano": agg_median(g["PctIngresoAnualEnUDLACalc"]),
            "GapPctUDLAMediano": agg_median(g["GapPctUDLAvsColegioCalc"]),
            "CostoColegioMediano": agg_median(g["CostoColegioAnual"]),
            "CostoUDLAMediano": agg_median(g["CostoUDLAAnual"]),
        })
    return pd.DataFrame(rows)


def comparativos_scope(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    """
    Si se elige colegio:
        devuelve colegio seleccionado vs cluster vs total filtrado.
    Si no:
        devuelve top colegios por hogares.
    """
    hogares = base_hogar(df)
    if hogares.empty:
        return pd.DataFrame()

    colegio_sel = filtros["colegio"]
    cluster_sel = filtros["cluster"]

    if colegio_sel != "Todos":
        total = hogares.copy()
        cluster_df = hogares.copy()
        if cluster_sel != "Todos":
            cluster_df = cluster_df[cluster_df["Cluster"] == cluster_sel]
        colegio_df = hogares[hogares["Colegio"] == colegio_sel]

        grupos = [
            ("Colegio seleccionado", colegio_df),
            ("Cluster", cluster_df),
            ("Total filtrado", total),
        ]

        rows = []
        for nombre, g in grupos:
            if g.empty:
                continue
            rows.append({
                "Grupo": nombre,
                "Hogares": len(g),
                "PctCaidaIngreso": g["FlagCaidaIngresoCalc"].mean(),
                "PctSubeIngreso": g["FlagSubioIngresoCalc"].mean(),
                "PctBajaQuintil": g["FlagBajaQuintilCalc"].mean(),
                "PctSubeQuintil": g["FlagSubeQuintilCalc"].mean(),
                "PctAmbosPadres": g["FlagAmbosPadresTrabajan"].mean(),
                "PctSoloPadre": g["FlagSoloPadreTrabaja"].mean(),
                "PctSoloMadre": g["FlagSoloMadreTrabaja"].mean(),
                "PctNinguno": g["FlagNingunPadreTrabaja"].mean(),
            })
        return pd.DataFrame(rows)

    resumen = resumen_por_colegio(hogares)
    if resumen.empty:
        return resumen

    resumen = resumen.sort_values("Hogares", ascending=False).head(12).copy()
    resumen = resumen.rename(columns={"Colegio": "Grupo"})

    return resumen


# =============================================================================
# GRÁFICOS
# =============================================================================

def fig_radar_segmentos(df: pd.DataFrame) -> go.Figure:
    hogares = base_hogar(df)
    data = (
        hogares.assign(
            SegmentoFinancieroHogar=hogares["SegmentoFinancieroHogar"].fillna("Sin clasificar")
        )
        .groupby("SegmentoFinancieroHogar", dropna=False)
        .size()
        .rename("Hogares")
        .reset_index()
    )

    total = data["Hogares"].sum()
    data["Porcentaje"] = data["Hogares"] / total if total else 0
    data = data[
        data["SegmentoFinancieroHogar"].ne("Situación financiera intermedia")
    ].copy()
    data = data.sort_values("Porcentaje", ascending=False)

    fig = go.Figure()
    if not data.empty and total:
        fig.add_trace(
            go.Scatterpolar(
                r=data["Porcentaje"],
                theta=data["SegmentoFinancieroHogar"],
                customdata=data["Hogares"],
                fill="toself",
                fillcolor="rgba(35, 78, 112, 0.25)",
                line=dict(color=COLOR_AZUL, width=3),
                marker=dict(color=COLOR_AZUL, size=8),
                name="Hogares",
                hovertemplate=(
                    "<b>%{theta}</b><br>"
                    "Participación: %{r:.1%}<br>"
                    "Hogares: %{customdata:,.0f}<extra></extra>"
                ),
            )
        )

    max_pct = float(data["Porcentaje"].max()) if not data.empty else 0
    radial_max = max(0.1, math.ceil(max_pct * 10) / 10)
    fig.update_layout(
        title=dict(text="Distribución porcentual por segmento", x=0.02),
        polar=dict(
            bgcolor="white",
            radialaxis=dict(
                visible=True,
                range=[0, radial_max],
                tickformat=".0%",
                gridcolor="rgba(35, 78, 112, 0.18)",
            ),
            angularaxis=dict(
                gridcolor="rgba(35, 78, 112, 0.18)",
                tickfont=dict(size=11, color=COLOR_TEXTO),
            ),
        ),
        showlegend=False,
        margin=dict(l=85, r=85, t=65, b=55),
        height=440,
        paper_bgcolor="white",
    )
    return fig


def fig_heatmap_segmento_quintil(df: pd.DataFrame) -> go.Figure:
    hogares = base_hogar(df).copy()
    tabla = (
        hogares.groupby(["SegmentoFinancieroHogar", "QuintilActual"], dropna=False)
        .size()
        .rename("Hogares")
        .reset_index()
    )
    pivot = tabla.pivot(
        index="SegmentoFinancieroHogar",
        columns="QuintilActual",
        values="Hogares",
    ).fillna(0)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]

    pivot_pct = pivot.div(pivot.sum(axis=1).replace(0, np.nan), axis=0)

    fig = px.imshow(
        pivot_pct,
        text_auto=".0%",
        aspect="auto",
        color_continuous_scale="Blues",
    )
    fig.update_layout(
        xaxis_title="Quintil actual",
        yaxis_title="Segmento del hogar",
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig


def fig_matriz_composicion(df: pd.DataFrame) -> go.Figure:
    resumen = resumen_por_colegio(df)
    if resumen.empty:
        return go.Figure()

    columnas_numericas = [
        "IndicePresionMediano",
        "PctDeudaMalaCalifPonderado",
        "PctCaidaIngreso",
        "Hogares",
    ]
    for columna in columnas_numericas:
        resumen[columna] = pd.to_numeric(resumen[columna], errors="coerce")

    resumen["PctCaidaIngreso"] = resumen["PctCaidaIngreso"].fillna(0).clip(0, 1)
    resumen = resumen.dropna(
        subset=["IndicePresionMediano", "PctDeudaMalaCalifPonderado", "Hogares"]
    ).copy()
    resumen = resumen[
        resumen["IndicePresionMediano"].ge(0)
        & resumen["PctDeudaMalaCalifPonderado"].between(0, 1)
        & resumen["Hogares"].gt(0)
    ]

    if resumen.empty:
        return go.Figure()

    # Los puntos grandes se dibujan al final para que no queden ocultos.
    resumen = resumen.sort_values("Hogares", ascending=True)

    # log(1 + x) conserva los valores cero y evita que pocos extremos oculten
    # la distribución de la mayoría de colegios cerca del origen.
    resumen["IndicePresionVisual"] = np.log1p(resumen["IndicePresionMediano"])

    fig = px.scatter(
        resumen,
        x="IndicePresionVisual",
        y="PctDeudaMalaCalifPonderado",
        size="Hogares",
        color="PctCaidaIngreso",
        color_continuous_scale=[
            [0.0, "#9ecae1"],
            [0.35, "#6baed6"],
            [0.7, "#3182bd"],
            [1.0, "#08519c"],
        ],
        range_color=[0, 1],
        size_max=34,
        hover_name="Colegio",
        hover_data={
            "Cluster": True,
            "Hogares": ":,.0f",
            "IngresoMediano": ":,.0f",
            "IndicePresionMediano": ":.2f",
            "IndicePresionVisual": False,
            "PctDeudaMalaCalifPonderado": ":.1%",
            "PctCaidaIngreso": ":.1%",
        },
    )
    valores_eje = np.array([0, 0.25, 0.5, 1, 2, 5, 10, 25, 50, 100, 300])
    valores_eje = valores_eje[valores_eje <= max(1, resumen["IndicePresionMediano"].max())]
    fig.update_layout(
        xaxis_title="Índice mediano de presión deuda / ingreso anual (escala logarítmica)",
        yaxis_title="Participación ponderada de deuda con mala calificación",
        coloraxis_colorbar=dict(title="% caída<br>de ingreso", tickformat=".0%"),
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_xaxes(
        tickmode="array",
        tickvals=np.log1p(valores_eje),
        ticktext=[f"{valor:g}" for valor in valores_eje],
    )
    fig.update_yaxes(tickformat=".0%", range=[0, 1.02])
    fig.update_traces(
        marker=dict(
            sizemin=7,
            opacity=0.78,
            line=dict(color="rgba(8, 81, 156, 0.65)", width=0.7),
        )
    )
    fig.add_hline(y=0.30, line_dash="dash", line_color=COLOR_ROJO)
    fig.add_vline(x=np.log1p(1.00), line_dash="dash", line_color=COLOR_ROJO)
    return fig


def fig_lollipop_divergente(df_comp: pd.DataFrame, col_neg: str, col_pos: str, titulo: str) -> go.Figure:
    if df_comp.empty:
        return go.Figure()

    work = df_comp.copy()
    work["Grupo"] = work["Grupo"].fillna("Sin colegio informado").astype(str)
    work["Negativo"] = -pd.to_numeric(work[col_neg], errors="coerce").fillna(0)
    work["Positivo"] = pd.to_numeric(work[col_pos], errors="coerce").fillna(0)
    work = work.drop_duplicates(subset="Grupo", keep="first")
    work["EtiquetaGrupo"] = work["Grupo"].map(
        lambda valor: valor if len(valor) <= 42 else f"{valor[:39]}..."
    )
    work = work.sort_values("Hogares", ascending=True)
    orden_grupos = work["EtiquetaGrupo"].tolist()

    fig = go.Figure()

    for _, row in work.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[row["Negativo"], row["Positivo"]],
                y=[row["EtiquetaGrupo"], row["EtiquetaGrupo"]],
                mode="lines",
                line=dict(color="#d9d9d9", width=3),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=work["Negativo"],
            y=work["EtiquetaGrupo"],
            mode="markers+text",
            marker=dict(size=12, color=COLOR_ROJO),
            text=[f"{abs(v):.0%}" for v in work["Negativo"]],
            textposition="middle left",
            name="Caída / baja",
            customdata=work["Grupo"],
            hovertemplate="<b>%{customdata}</b><br>Caída / baja: %{x:.1%}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=work["Positivo"],
            y=work["EtiquetaGrupo"],
            mode="markers+text",
            marker=dict(size=12, color=COLOR_VERDE),
            text=[f"{v:.0%}" for v in work["Positivo"]],
            textposition="middle right",
            name="Sube / aumenta",
            customdata=work["Grupo"],
            hovertemplate="<b>%{customdata}</b><br>Sube / aumenta: %{x:.1%}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text=titulo, x=0.01, y=0.98),
        xaxis=dict(
            tickformat=".0%",
            zeroline=True,
            zerolinewidth=1.5,
            zerolinecolor="#999999",
        ),
        yaxis=dict(
            title="", type="category", automargin=True,
            categoryorder="array", categoryarray=orden_grupos,
        ),
        margin=dict(l=10, r=25, t=55, b=75),
        height=max(430, 34 * len(work) + 120),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(
            orientation="h",
            x=0,
            xanchor="left",
            y=-0.16,
            yanchor="top",
        ),
    )
    return fig


def fig_transicion_quintiles(df: pd.DataFrame, altura: int = 430) -> go.Figure:
    """Compara el quintil anterior y actual de los mismos hogares."""
    hogares = base_hogar(df).copy()
    orden = [f"Quintil {numero}" for numero in range(1, 6)] + [
        "Sin información de empleo"
    ]

    if not {"QuintilAnterior", "QuintilActual"}.issubset(hogares.columns):
        hogares = hogares.iloc[0:0]
    else:
        hogares = hogares[
            hogares["QuintilAnterior"].isin(orden)
            & hogares["QuintilActual"].isin(orden)
        ].copy()

    anios = sorted(
        pd.to_numeric(hogares.get("AnioAnalisis"), errors="coerce")
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )
    if len(anios) == 1:
        etiqueta_actual = str(anios[0])
        etiqueta_anterior = str(anios[0] - 1)
    else:
        etiqueta_anterior = "Año anterior"
        etiqueta_actual = "Año filtrado"

    fig = go.Figure()
    if hogares.empty:
        fig.add_annotation(
            text="No hay hogares con quintil comparable entre ambos años",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=13, color=COLOR_GRIS),
        )
        fig.update_layout(
            title=dict(text="Transición entre quintiles", x=0.01, y=0.98),
            height=altura,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )
        return fig

    flujos = (
        hogares.groupby(["QuintilAnterior", "QuintilActual"], observed=True)
        .size()
        .rename("Hogares")
        .reset_index()
    )
    total = int(flujos["Hogares"].sum())
    conteo_anterior = hogares["QuintilAnterior"].value_counts()
    conteo_actual = hogares["QuintilActual"].value_counts()
    matriz = (
        flujos.pivot(
            index="QuintilAnterior",
            columns="QuintilActual",
            values="Hogares",
        )
        .reindex(index=orden, columns=orden, fill_value=0)
        .fillna(0)
        .astype(int)
    )

    colores = [
        "#d95d39", "#f4a261", "#e9c46a", "#7fb069", "#234e70", "#9ca3af"
    ]
    colores_flujo = [
        "rgba(217,93,57,0.22)",
        "rgba(244,162,97,0.22)",
        "rgba(233,196,106,0.22)",
        "rgba(127,176,105,0.22)",
        "rgba(35,78,112,0.22)",
        "rgba(156,163,175,0.22)",
    ]
    etiqueta_visible = {
        quintil: quintil for quintil in orden
    }
    etiqueta_visible["Sin información de empleo"] = "Sin información<br>de empleo"
    etiquetas = [
        f"<b>{etiqueta_visible[quintil]}</b><br>"
        f"{conteo_anterior.get(quintil, 0):,.0f} hogares"
        for quintil in orden
    ] + [
        f"<b>{etiqueta_visible[quintil]}</b><br>"
        f"{conteo_actual.get(quintil, 0):,.0f} hogares"
        for quintil in orden
    ]
    detalle_nodos = []
    for quintil_origen in orden:
        movimientos = "<br>".join(
            f"{quintil_destino}: {matriz.loc[quintil_origen, quintil_destino]:,.0f}"
            for quintil_destino in orden
        )
        detalle_nodos.append(
            f"<b>{quintil_origen} · {etiqueta_anterior}</b><br>"
            f"Destino en {etiqueta_actual}:<br>{movimientos}<br>"
            f"<b>Total: {conteo_anterior.get(quintil_origen, 0):,.0f} hogares</b>"
        )
    for quintil_destino in orden:
        movimientos = "<br>".join(
            f"{quintil_origen}: {matriz.loc[quintil_origen, quintil_destino]:,.0f}"
            for quintil_origen in orden
        )
        detalle_nodos.append(
            f"<b>{quintil_destino} · {etiqueta_actual}</b><br>"
            f"Origen en {etiqueta_anterior}:<br>{movimientos}<br>"
            f"<b>Total: {conteo_actual.get(quintil_destino, 0):,.0f} hogares</b>"
        )
    indice = {quintil: posicion for posicion, quintil in enumerate(orden)}

    sources = [indice[valor] for valor in flujos["QuintilAnterior"]]
    numero_categorias = len(orden)
    targets = [numero_categorias + indice[valor] for valor in flujos["QuintilActual"]]
    values = flujos["Hogares"].astype(int).tolist()
    customdata = [
        [
            fila.QuintilAnterior,
            fila.QuintilActual,
            fila.Hogares / total,
        ]
        for fila in flujos.itertuples(index=False)
    ]

    fig.add_trace(
        go.Sankey(
            arrangement="fixed",
            orientation="h",
            valueformat=",.0f",
            # Reserva una franja superior amplia para los encabezados de año.
            domain=dict(x=[0, 1], y=[0, 0.72]),
            textfont=dict(
                size=14,
                color="#ffffff",
                family="Arial, sans-serif",
                shadow=(
                    "-1px -1px 0 #111827, 1px -1px 0 #111827, "
                    "-1px 1px 0 #111827, 1px 1px 0 #111827"
                ),
            ),
            node=dict(
                pad=30,
                thickness=18,
                line=dict(color="rgba(0,0,0,0)", width=0),
                label=etiquetas,
                color=colores + colores,
                customdata=detalle_nodos,
                x=[0.07] * numero_categorias + [0.93] * numero_categorias,
                y=[0.01, 0.17, 0.33, 0.49, 0.65, 0.81] * 2,
                hovertemplate="%{customdata}<extra></extra>",
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=[colores_flujo[source] for source in sources],
                customdata=customdata,
                hovertemplate=(
                    "<b>%{customdata[0]} → %{customdata[1]}</b><br>"
                    "Hogares: %{value:,.0f}<br>"
                    "Participación: %{customdata[2]:.1%}<extra></extra>"
                ),
            ),
        )
    )
    fig.update_layout(
        title=dict(text="Transición entre quintiles", x=0.01, y=0.98),
        font=dict(size=14, color=COLOR_TEXTO, family="Arial, sans-serif"),
        margin=dict(l=85, r=85, t=100, b=45),
        height=altura,
        paper_bgcolor="white",
        plot_bgcolor="white",
        annotations=[
            dict(
                text=f"<b>{etiqueta_anterior}</b><br><span style='font-size:11px'>Quintil de origen</span>",
                x=0.07, y=0.91,
                xref="paper", yref="paper", showarrow=False, xanchor="center",
                yanchor="middle", align="center",
                font=dict(size=15, color=COLOR_AZUL),
            ),
            dict(
                text=f"<b>{etiqueta_actual}</b><br><span style='font-size:11px'>Quintil de destino</span>",
                x=0.93, y=0.91,
                xref="paper", yref="paper", showarrow=False, xanchor="center",
                yanchor="middle", align="center",
                font=dict(size=15, color=COLOR_AZUL),
            ),
            dict(
                text=f"Total: {total:,.0f} hogares comparables", x=1, y=1.12,
                xref="paper", yref="paper", showarrow=False, xanchor="right",
                font=dict(size=11, color=COLOR_GRIS),
            ),
        ],
    )
    return fig


def fig_empleo_quintil(df: pd.DataFrame) -> go.Figure:
    hogares = base_hogar(df).copy()

    def etiqueta_estado(row):
        if row["FlagAmbosPadresTrabajan"] == 1:
            return "Ambos trabajan"
        if row["FlagSoloPadreTrabaja"] == 1:
            return "Solo padre"
        if row["FlagSoloMadreTrabaja"] == 1:
            return "Solo madre"
        return "Ninguno"

    hogares["EstadoLaboralSimple"] = hogares.apply(etiqueta_estado, axis=1)
    hogares = hogares[
        hogares["EstadoLaboralSimple"].ne("Ninguno")
        & hogares["QuintilActual"].ne("Sin información de empleo")
    ].copy()

    tabla = (
        hogares.groupby(["QuintilActual", "EstadoLaboralSimple"], dropna=False)
        .size()
        .rename("Hogares")
        .reset_index()
    )

    pivot = tabla.pivot(
        index="QuintilActual",
        columns="EstadoLaboralSimple",
        values="Hogares",
    ).fillna(0)
    pivot = pivot.reindex(
        columns=["Ambos trabajan", "Solo padre", "Solo madre"],
        fill_value=0,
    )

    pivot_pct = pivot.div(pivot.sum(axis=1).replace(0, np.nan), axis=0)

    fig = px.imshow(
        pivot_pct,
        text_auto=".0%",
        aspect="auto",
        color_continuous_scale="Blues",
    )
    fig.update_layout(
        xaxis_title="Estado laboral del hogar",
        yaxis_title="Quintil actual",
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig


def fig_stack_empleo(df: pd.DataFrame) -> go.Figure:
    hogares = base_hogar(df).copy()

    categorias = {
        "Ambos trabajan": hogares["FlagAmbosPadresTrabajan"].mean(),
        "Solo padre": hogares["FlagSoloPadreTrabaja"].mean(),
        "Solo madre": hogares["FlagSoloMadreTrabaja"].mean(),
        "Ninguno": hogares["FlagNingunPadreTrabaja"].mean(),
    }
    categorias = dict(
        sorted(categorias.items(), key=lambda item: item[1], reverse=True)
    )

    fig = go.Figure()
    base_x = ["Composición laboral"]

    colores = {
        "Ambos trabajan": COLOR_AZUL,
        "Solo padre": COLOR_VERDE,
        "Solo madre": COLOR_NARANJA,
        "Ninguno": COLOR_ROJO,
    }

    for nombre, valor in categorias.items():
        fig.add_trace(
            go.Bar(
                x=base_x,
                y=[valor],
                name=nombre,
                marker_color=colores[nombre],
                text=[f"{valor:.0%}"],
                textposition="inside",
            )
        )

    fig.update_layout(
        barmode="stack",
        yaxis_tickformat=".0%",
        margin=dict(l=10, r=10, t=25, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend_orientation="h",
        legend_y=1.15,
    )
    return fig


def fig_violin_deuda(df: pd.DataFrame, variable: str, titulo: str) -> go.Figure:
    hogares = base_hogar(df).copy()
    fig = go.Figure()
    titulos_eje_y = {
        "IndicePresionDeudaIngresoAnual": "Índice de presión deuda / ingreso anual",
        "PorcentajeDeudaCalificacionCritica": "Deuda con mala calificación (%)",
        "PorcentajeMoraAmpliada": "Mora ampliada (%)",
    }
    es_porcentaje = variable in {
        "PorcentajeDeudaCalificacionCritica",
        "PorcentajeMoraAmpliada",
    }

    segmentos_colores = [
        ("Hogar estable", COLOR_VERDE),
        ("Viviendo con lo justo", COLOR_NARANJA),
        ("Presión financiera alta", COLOR_CELESTE),
        ("Ahogado en deuda", COLOR_ROJO),
        ("Deterioro severo", "#7c3aed"),
    ]
    segmentos_colores.sort(
        key=lambda item: pd.to_numeric(
            hogares.loc[hogares["SegmentoFinancieroHogar"] == item[0], variable],
            errors="coerce",
        ).median(),
        reverse=True,
    )

    for segmento, color in segmentos_colores:
        datos = pd.to_numeric(
            hogares.loc[hogares["SegmentoFinancieroHogar"] == segmento, variable],
            errors="coerce",
        ).dropna()

        if datos.empty:
            continue

        violin_config = dict(
            y=datos.clip(0, 1) if es_porcentaje else datos,
            name=segmento,
            box_visible=True,
            meanline_visible=True,
            line_color=color,
            fillcolor=color,
            opacity=0.45,
        )
        if es_porcentaje:
            violin_config.update(span=[0, 1], spanmode="manual")

        fig.add_trace(go.Violin(**violin_config))

    fig.update_layout(
        title=titulo,
        xaxis_title="Segmento financiero del hogar",
        yaxis_title=titulos_eje_y.get(variable, variable),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    if es_porcentaje:
        fig.update_yaxes(range=[0, 1], tickformat=".0%")
    return fig


def fig_lineas_calificacion_por_colegio(
    df: pd.DataFrame,
    variable: str,
    titulo: str,
) -> go.Figure:
    """Una línea por calificación y un punto por colegio."""
    hogares = base_hogar(df).copy()
    hogares["Colegio"] = hogares["Colegio"].fillna(
        "Sin colegio informado"
    ).astype(str)
    hogares["PeorCalificacionHogar"] = hogares[
        "PeorCalificacionHogar"
    ].fillna("Sin deuda reportada").astype(str)
    hogares[variable] = pd.to_numeric(
        hogares[variable], errors="coerce"
    ).clip(0, 1)

    orden_colegios = hogares["Colegio"].value_counts().head(15).index.tolist()
    orden_calificaciones = [
        "A1", "A2", "A3", "B1", "B2", "C1", "C2", "D", "E", "AL"
    ]
    work = hogares[
        hogares["Colegio"].isin(orden_colegios)
        & hogares["PeorCalificacionHogar"].isin(orden_calificaciones)
    ].copy()
    totales_colegio = hogares["Colegio"].value_counts()
    resumen = (
        work.groupby(["Colegio", "PeorCalificacionHogar"], dropna=False)
        .agg(
            Valor=(variable, "median"),
            HogaresCalificacion=(variable, "count"),
        )
        .reset_index()
    )
    resumen["TotalColegio"] = resumen["Colegio"].map(totales_colegio)

    fig = go.Figure()
    colores = px.colors.qualitative.Safe + px.colors.qualitative.Set2
    mapa_orden = {
        colegio: posicion for posicion, colegio in enumerate(orden_colegios)
    }
    for indice, calificacion in enumerate(orden_calificaciones):
        datos = resumen[
            resumen["PeorCalificacionHogar"].eq(calificacion)
        ].copy()
        if datos.empty:
            continue
        datos["Orden"] = datos["Colegio"].map(mapa_orden)
        datos = datos.sort_values("Orden")
        color = colores[indice % len(colores)]
        fig.add_trace(
            go.Scatter(
                x=datos["Colegio"],
                y=datos["Valor"],
                mode="lines+markers",
                name=calificacion,
                connectgaps=False,
                line=dict(
                    color=color, width=2.2, shape="spline", smoothing=0.65
                ),
                marker=dict(
                    size=7,
                    color="white",
                    line=dict(color=color, width=2),
                ),
                customdata=np.column_stack([
                    datos["HogaresCalificacion"],
                    datos["TotalColegio"],
                ]),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    f"Calificación: {calificacion}<br>"
                    "Valor mediano: %{y:.1%}<br>"
                    "Hogares con esta calificación: %{customdata[0]:,.0f} "
                    "de %{customdata[1]:,.0f} hogares del colegio"
                    "<extra></extra>"
                ),
            )
        )

    etiqueta_y = {
        "PorcentajeDeudaCalificacionCritica": (
            "% de deuda con mala calificación"
        ),
        "PorcentajeMoraAmpliada": "% de mora ampliada",
    }
    fig.update_layout(
        title=dict(text=titulo, x=0.02),
        xaxis_title="Colegio (15 con más hogares)",
        yaxis_title=etiqueta_y.get(variable, variable),
        margin=dict(l=10, r=10, t=55, b=145),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(
            title="Calificación",
            orientation="h",
            y=-0.38,
        ),
    )
    fig.update_xaxes(
        categoryorder="array",
        categoryarray=orden_colegios,
        tickangle=-40,
        showgrid=False,
    )
    fig.update_yaxes(range=[0, 1], tickformat=".0%")
    return fig


def fig_box_deuda_por_quintil(
    df: pd.DataFrame,
    mostrar_outliers: bool = True,
) -> go.Figure:
    """Distribución de deuda y resumen de presión financiera por quintil."""
    hogares = base_hogar(df).copy()
    orden = [f"Quintil {numero}" for numero in range(1, 6)] + [
        "Sin información de empleo"
    ]

    hogares["DeudaTotalVisual"] = pd.to_numeric(
        hogares.get("DeudaTotalHogar", 0), errors="coerce"
    ).fillna(0).clip(lower=0)
    hogares["PresionVisual"] = pd.to_numeric(
        hogares.get("IndicePresionDeudaIngresoAnual", np.nan), errors="coerce"
    )
    hogares["IngresoAnualVisual"] = pd.to_numeric(
        hogares.get("IngresoAnualHogarActual", 0), errors="coerce"
    ).fillna(0)

    condiciones_presion = [
        hogares["DeudaTotalVisual"].le(0),
        hogares["DeudaTotalVisual"].gt(0) & hogares["IngresoAnualVisual"].le(0),
        hogares["PresionVisual"].le(0.5),
        hogares["PresionVisual"].le(1),
        hogares["PresionVisual"].le(2),
        hogares["PresionVisual"].gt(2),
    ]
    etiquetas_presion = [
        "Sin deuda",
        "Crítica: deuda sin ingreso formal",
        "Baja: hasta 0,5 años",
        "Media: 0,5 a 1 año",
        "Alta: 1 a 2 años",
        "Crítica: más de 2 años",
    ]
    hogares["CategoriaPresionVisual"] = np.select(
        [
            condicion.fillna(False).to_numpy(dtype=bool)
            for condicion in condiciones_presion
        ],
        etiquetas_presion,
        default="Sin dato de ingreso",
    )

    colores = ["#d95d39", "#f4a261", "#e9c46a", "#7fb069", "#234e70", "#9ca3af"]
    fig = go.Figure()

    for quintil, color in zip(orden, colores):
        grupo = hogares[hogares["QuintilActual"].eq(quintil)].copy()
        deuda_positiva = grupo[grupo["DeudaTotalVisual"].gt(0)].copy()
        if grupo.empty or deuda_positiva.empty:
            continue

        total_hogares = len(grupo)
        total_deuda = float(grupo["DeudaTotalVisual"].sum())
        exposicion_critica = pd.to_numeric(
            grupo.get("MontoExposicionCritica", 0), errors="coerce"
        ).fillna(0).sum()
        pct_deuda_critica = exposicion_critica / total_deuda if total_deuda else 0
        pct_morosos = pd.to_numeric(
            grupo.get("FlagTieneMora", 0), errors="coerce"
        ).fillna(0).eq(1).mean()
        categorias = grupo["CategoriaPresionVisual"].value_counts()
        detalle_categorias = "<br>".join(
            f"{categoria}: {int(categorias.get(categoria, 0)):,}"
            for categoria in etiquetas_presion
        )
        resumen_tooltip = (
            f"<b>{quintil}</b><br>"
            f"Hogares: {total_hogares:,}<br>"
            f"Hogares con deuda: {len(deuda_positiva):,}<br>"
            f"<b>Categorías de presión:</b><br>{detalle_categorias}<br>"
            f"Morosos: {pct_morosos:.1%}<br>"
            f"Deuda crítica / deuda total: {pct_deuda_critica:.1%}"
        )

        fig.add_trace(
            go.Box(
                name=quintil,
                y=deuda_positiva["DeudaTotalVisual"],
                marker=dict(color=color, opacity=0.55),
                line=dict(color=color, width=2),
                fillcolor=color,
                opacity=0.60,
                boxpoints="outliers" if mostrar_outliers else False,
                customdata=[resumen_tooltip] * len(deuda_positiva),
                hoveron="boxes+points",
                hovertemplate=(
                    "%{customdata}<br>"
                    "Deuda del hogar: $%{y:,.2f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(
            text="Distribución de la deuda total por quintil socioeconómico",
            x=0.01,
        ),
        xaxis_title="Quintil socioeconómico actual",
        yaxis_title="Deuda total del hogar (USD, escala logarítmica)",
        yaxis_type="log",
        showlegend=False,
        height=520,
        margin=dict(l=65, r=30, t=65, b=65),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hoverlabel=dict(bgcolor="white", font=dict(color=COLOR_TEXTO, size=12)),
    )
    fig.update_yaxes(gridcolor="rgba(107,114,128,0.16)", tickprefix="$")
    return fig


def fig_composicion_presion_por_quintil(df: pd.DataFrame) -> go.Figure:
    """Composición porcentual de hogares según presión de deuda."""
    hogares = base_hogar(df).copy()
    orden_quintiles = [f"Quintil {numero}" for numero in range(1, 6)] + [
        "Sin información de empleo"
    ]
    deuda = pd.to_numeric(hogares.get("DeudaTotalHogar", 0), errors="coerce").fillna(0)
    ingreso = pd.to_numeric(
        hogares.get("IngresoAnualHogarActual", 0), errors="coerce"
    ).fillna(0)
    presion = pd.to_numeric(
        hogares.get("IndicePresionDeudaIngresoAnual", np.nan), errors="coerce"
    )
    condiciones = [
        deuda.le(0),
        deuda.gt(0) & ingreso.gt(0) & presion.le(0.5),
        deuda.gt(0) & ingreso.gt(0) & presion.gt(0.5) & presion.le(1),
        deuda.gt(0) & (ingreso.le(0) | presion.gt(1)),
    ]
    categorias = ["Sin deuda", "Presión baja", "Presión media", "Presión de deuda"]
    hogares["NivelPresionDeuda"] = np.select(
        [condicion.fillna(False).to_numpy(dtype=bool) for condicion in condiciones],
        categorias,
        default="Sin dato",
    )
    tabla = (
        hogares[hogares["QuintilActual"].isin(orden_quintiles)]
        .groupby(["QuintilActual", "NivelPresionDeuda"], observed=True)
        .size()
        .rename("Hogares")
        .reset_index()
    )
    totales = tabla.groupby("QuintilActual")["Hogares"].transform("sum")
    tabla["Porcentaje"] = tabla["Hogares"] / totales

    colores = {
        "Sin deuda": "#d1d5db",
        "Presión baja": COLOR_VERDE,
        "Presión media": COLOR_NARANJA,
        "Presión de deuda": COLOR_ROJO,
        "Sin dato": COLOR_GRIS,
    }
    fig = px.bar(
        tabla,
        x="QuintilActual",
        y="Porcentaje",
        color="NivelPresionDeuda",
        category_orders={
            "QuintilActual": orden_quintiles,
            "NivelPresionDeuda": categorias + ["Sin dato"],
        },
        color_discrete_map=colores,
        custom_data=["Hogares"],
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>%{fullData.name}<br>"
            "Hogares: %{customdata[0]:,.0f}<br>"
            "Participación: %{y:.1%}<extra></extra>"
        )
    )
    fig.update_layout(
        title=dict(text="Composición de la presión de deuda por quintil", x=0.01),
        xaxis_title="Quintil socioeconómico actual",
        yaxis_title="Porcentaje de hogares",
        yaxis_tickformat=".0%",
        barmode="stack",
        height=460,
        margin=dict(l=55, r=20, t=65, b=70),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.23, x=0),
    )
    return fig


def fig_riesgo_deuda_por_quintil(df: pd.DataFrame) -> go.Figure:
    """Morosidad, deuda crítica y presión de deuda por quintil."""
    hogares = base_hogar(df).copy()
    orden_quintiles = [f"Quintil {numero}" for numero in range(1, 6)] + [
        "Sin información de empleo"
    ]
    filas = []
    for quintil in orden_quintiles:
        grupo = hogares[hogares["QuintilActual"].eq(quintil)].copy()
        if grupo.empty:
            continue
        deuda = pd.to_numeric(grupo.get("DeudaTotalHogar", 0), errors="coerce").fillna(0)
        ingreso = pd.to_numeric(
            grupo.get("IngresoAnualHogarActual", 0), errors="coerce"
        ).fillna(0)
        presion = pd.to_numeric(
            grupo.get("IndicePresionDeudaIngresoAnual", np.nan), errors="coerce"
        )
        deuda_total = deuda.sum()
        exposicion_critica = pd.to_numeric(
            grupo.get("MontoExposicionCritica", 0), errors="coerce"
        ).fillna(0).sum()
        indicadores = {
            "Morosidad": pd.to_numeric(
                grupo.get("FlagTieneMora", 0), errors="coerce"
            ).fillna(0).eq(1).mean(),
            "Participación monetaria de deuda crítica": (
                exposicion_critica / deuda_total if deuda_total else 0
            ),
            "Presión de deuda": (deuda.gt(0) & (ingreso.le(0) | presion.gt(1))).mean(),
        }
        for indicador, valor in indicadores.items():
            filas.append({
                "Quintil": quintil,
                "Indicador": indicador,
                "Porcentaje": valor,
                "Hogares": len(grupo),
            })

    tabla = pd.DataFrame(filas)
    colores = {
        "Morosidad": COLOR_NARANJA,
        "Deuda crítica": "#7c3aed",
        "Presión de deuda": COLOR_ROJO,
    }
    fig = px.scatter(
        tabla,
        x="Quintil",
        y="Porcentaje",
        color="Indicador",
        category_orders={"Quintil": orden_quintiles},
        color_discrete_map=colores,
        custom_data=["Hogares"],
    )
    fig.update_traces(
        marker=dict(size=13, line=dict(color="white", width=1.5)),
        mode="markers+lines",
        hovertemplate=(
            "<b>%{x}</b><br>%{fullData.name}: %{y:.1%}<br>"
            "Hogares: %{customdata[0]:,.0f}<extra></extra>"
        ),
    )
    fig.update_layout(
        title=dict(text="Indicadores de riesgo de deuda por quintil", x=0.01),
        xaxis_title="Quintil socioeconómico actual",
        yaxis_title="Porcentaje",
        yaxis_tickformat=".0%",
        height=460,
        margin=dict(l=55, r=20, t=65, b=70),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.23, x=0),
    )
    return fig


def fig_indicadores_deuda_por_colegio(df: pd.DataFrame) -> go.Figure:
    """Compara los principales porcentajes de deuda entre colegios."""
    hogares = base_hogar(df).copy()
    hogares["ColegioVisual"] = (
        hogares["Colegio"].fillna("Sin colegio informado").astype(str)
    )
    filas = []
    for colegio, grupo in hogares.groupby("ColegioVisual", dropna=False):
        deuda = pd.to_numeric(
            grupo.get("DeudaTotalHogar", 0), errors="coerce"
        ).fillna(0)
        ingreso = pd.to_numeric(
            grupo.get("IngresoAnualHogarActual", 0), errors="coerce"
        ).fillna(0)
        presion = pd.to_numeric(
            grupo.get("IndicePresionDeudaIngresoAnual", np.nan), errors="coerce"
        )
        deuda_total = float(deuda.sum())
        exposicion_critica = pd.to_numeric(
            grupo.get("MontoExposicionCritica", 0), errors="coerce"
        ).fillna(0).sum()
        filas.append({
            "Colegio": colegio,
            "Hogares": len(grupo),
            "Sin deuda": deuda.le(0).mean(),
            "Morosidad": pd.to_numeric(
                grupo.get("FlagTieneMora", 0), errors="coerce"
            ).fillna(0).eq(1).mean(),
            "Participación monetaria de deuda crítica": (
                exposicion_critica / deuda_total if deuda_total else 0
            ),
            "Presión de deuda": (
                deuda.gt(0) & (ingreso.le(0) | presion.gt(1))
            ).fillna(False).mean(),
        })

    resumen = pd.DataFrame(filas)
    if resumen.empty:
        return go.Figure()

    # Prioriza los colegios con mayor cantidad de hogares documentados.
    resumen = (
        resumen.sort_values(
            ["Hogares", "Presión de deuda"],
            ascending=[False, False],
        )
        .head(20)
        .copy()
    )
    resumen["ColegioCorto"] = resumen["Colegio"].map(
        lambda valor: valor if len(valor) <= 24 else f"{valor[:21]}..."
    )
    # El valor completo identifica la categoría. La versión corta se usa solo
    # como etiqueta para evitar que colegios con prefijos iguales se superpongan.
    orden_colegios = resumen["Colegio"].tolist()
    colores = {
        "Sin deuda": COLOR_CELESTE,
        "Morosidad": COLOR_NARANJA,
        "Participación monetaria de deuda crítica": "#7c3aed",
        "Presión de deuda": COLOR_ROJO,
    }
    definiciones = {
        "Sin deuda": "Hogares sin deuda reportada",
        "Morosidad": "Hogares con al menos un saldo vencido",
        "Participación monetaria de deuda crítica": (
            "Exposición E+, judicial o castigada / deuda total"
        ),
        "Presión de deuda": "Deuda > ingreso anual o deuda sin ingreso formal",
    }

    fig = go.Figure()
    for indicador in [
        "Sin deuda",
        "Morosidad",
        "Participación monetaria de deuda crítica",
        "Presión de deuda",
    ]:
        fig.add_trace(
            go.Scatter(
                x=resumen["Colegio"],
                y=resumen[indicador],
                mode="lines+markers",
                name=indicador,
                line=dict(color=colores[indicador], width=2.5),
                marker=dict(
                    color="white",
                    size=8,
                    line=dict(color=colores[indicador], width=2.5),
                ),
                customdata=np.column_stack([
                    resumen["Colegio"],
                    resumen["Hogares"],
                    [definiciones[indicador]] * len(resumen),
                ]),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    f"{indicador}: %{{y:.1%}}<br>"
                    "Hogares: %{customdata[1]:,.0f}<br>"
                    "%{customdata[2]}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(
            text="Indicadores de deuda por colegio",
            x=0.01,
            y=0.98,
            yanchor="top",
        ),
        xaxis=dict(
            title="Colegio (20 con más hogares documentados)",
            categoryorder="array",
            categoryarray=orden_colegios,
            tickmode="array",
            tickvals=resumen["Colegio"].tolist(),
            ticktext=resumen["ColegioCorto"].tolist(),
            tickangle=-45,
        ),
        yaxis=dict(title="Porcentaje", tickformat=".0%", rangemode="tozero"),
        height=570,
        margin=dict(l=60, r=30, t=165, b=180),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        legend=dict(
            title_text="Indicador",
            orientation="h",
            x=0,
            xanchor="left",
            y=1.16,
            yanchor="bottom",
        ),
        annotations=[
            dict(
                text=f"Total: {len(hogares):,.0f} hogares",
                x=1,
                y=1.29,
                xref="paper",
                yref="paper",
                xanchor="right",
                yanchor="bottom",
                showarrow=False,
                font=dict(size=11, color=COLOR_GRIS),
            )
        ],
    )
    fig.update_yaxes(gridcolor="rgba(107,114,128,0.16)")
    return fig


def fig_radar_riesgo_deuda(
    df_base: pd.DataFrame,
    filtros: dict,
) -> go.Figure:
    """Perfil de riesgo del colegio frente a su clúster y al total comparable."""
    scope = df_base.copy()
    for columna, llave in [
        ("AnioAnalisis", "anio"),
        ("Periodo", "periodo"),
        ("Tipo", "tipo"),
        ("Cluster", "cluster"),
    ]:
        valor = filtros.get(llave, "Todos")
        if valor != "Todos":
            scope = scope[scope[columna].eq(valor)]

    hogares_scope = base_hogar(scope)
    colegio_seleccionado = filtros.get("colegio", "Todos")

    if colegio_seleccionado == "Todos":
        candidatos = []
        for colegio, grupo in hogares_scope.groupby("Colegio", dropna=False):
            deuda = pd.to_numeric(
                grupo.get("DeudaTotalHogar", 0), errors="coerce"
            ).fillna(0)
            ingreso = pd.to_numeric(
                grupo.get("IngresoAnualHogarActual", 0), errors="coerce"
            ).fillna(0)
            presion = pd.to_numeric(
                grupo.get("IndicePresionDeudaIngresoAnual", np.nan),
                errors="coerce",
            )
            candidatos.append({
                "Colegio": colegio,
                "Hogares": len(grupo),
                "Presion": (
                    deuda.gt(0) & (ingreso.le(0) | presion.gt(1))
                ).fillna(False).mean(),
            })
        tabla_candidatos = pd.DataFrame(candidatos)
        if tabla_candidatos.empty:
            return go.Figure()
        # Evita elegir automáticamente un colegio con una muestra mínima.
        elegibles = tabla_candidatos[tabla_candidatos["Hogares"].ge(20)]
        if elegibles.empty:
            elegibles = tabla_candidatos
        colegio_seleccionado = (
            elegibles.sort_values(
                ["Presion", "Hogares"],
                ascending=[False, False],
            )
            .iloc[0]["Colegio"]
        )

    colegio_df = hogares_scope[
        hogares_scope["Colegio"].fillna("Sin colegio informado").astype(str)
        .eq(str(colegio_seleccionado))
    ].copy()
    if colegio_df.empty:
        return go.Figure()

    cluster_colegio = (
        colegio_df["Cluster"].dropna().astype(str).mode().iloc[0]
        if colegio_df["Cluster"].notna().any()
        else "Sin cluster"
    )
    cluster_df = hogares_scope[
        hogares_scope["Cluster"].fillna("Sin cluster").astype(str).eq(cluster_colegio)
    ].copy()

    ejes = [
        "Hogares con deuda",
        "Morosidad",
        "Deuda crítica",
        "Presión de deuda",
    ]

    def calcular_perfil(grupo: pd.DataFrame) -> list[float]:
        if grupo.empty:
            return [0.0] * len(ejes)
        deuda = pd.to_numeric(
            grupo.get("DeudaTotalHogar", 0), errors="coerce"
        ).fillna(0)
        ingreso = pd.to_numeric(
            grupo.get("IngresoAnualHogarActual", 0), errors="coerce"
        ).fillna(0)
        presion = pd.to_numeric(
            grupo.get("IndicePresionDeudaIngresoAnual", np.nan), errors="coerce"
        )
        deuda_total = deuda.sum()
        critica = pd.to_numeric(
            grupo.get("MontoExposicionCritica", 0), errors="coerce"
        ).fillna(0).sum()
        return [
            deuda.gt(0).mean(),
            pd.to_numeric(
                grupo.get("FlagTieneMora", 0), errors="coerce"
            ).fillna(0).eq(1).mean(),
            critica / deuda_total if deuda_total else 0,
            (
                deuda.gt(0) & (ingreso.le(0) | presion.gt(1))
            ).fillna(False).mean(),
        ]

    perfiles = [
        (str(colegio_seleccionado), colegio_df, COLOR_ROJO),
        (f"Promedio del clúster: {cluster_colegio}", cluster_df, COLOR_AZUL),
    ]
    fig = go.Figure()
    for nombre, grupo, color in perfiles:
        valores = calcular_perfil(grupo)
        fig.add_trace(
            go.Scatterpolar(
                r=valores + [valores[0]],
                theta=ejes + [ejes[0]],
                mode="lines+markers",
                fill="toself",
                name=nombre,
                line=dict(color=color, width=2.5),
                marker=dict(size=7, color=color),
                opacity=0.62,
                customdata=[[len(grupo)]] * (len(ejes) + 1),
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "%{theta}: %{r:.1%}<br>"
                    "Hogares: %{customdata[0]:,.0f}<extra></extra>"
                ),
            )
        )

    nombre_corto = str(colegio_seleccionado)
    if len(nombre_corto) > 55:
        nombre_corto = f"{nombre_corto[:52]}..."
    fig.update_layout(
        title=dict(
            text=f"Perfil de riesgo de deuda — {nombre_corto}",
            x=0.01,
        ),
        polar=dict(
            bgcolor="white",
            radialaxis=dict(
                range=[0, 1],
                tickformat=".0%",
                tickvals=[0.2, 0.4, 0.6, 0.8, 1],
                gridcolor="rgba(107,114,128,0.22)",
            ),
            angularaxis=dict(
                gridcolor="rgba(107,114,128,0.20)",
                tickfont=dict(size=12, color=COLOR_TEXTO),
            ),
        ),
        height=530,
        margin=dict(l=100, r=100, t=90, b=80),
        paper_bgcolor="white",
        legend=dict(
            orientation="h",
            x=0,
            y=-0.12,
        ),
    )
    return fig


def fig_matriz_cambio_presion_deuda(
    df_base: pd.DataFrame,
    filtros: dict,
) -> go.Figure:
    """Cambio interanual de presión de deuda por clúster y quintil."""
    scope = df_base.copy()
    for columna, llave in [
        ("Tipo", "tipo"),
        ("Cluster", "cluster"),
        ("Colegio", "colegio"),
    ]:
        valor = filtros.get(llave, "Todos")
        if valor != "Todos":
            scope = scope[scope[columna].eq(valor)]

    anio_filtro = filtros.get("anio", "Todos")
    periodo_filtro = filtros.get("periodo", "Todos")
    if anio_filtro != "Todos":
        anio_actual = int(anio_filtro)
    elif periodo_filtro != "Todos":
        anios_periodo = pd.to_numeric(
            scope.loc[scope["Periodo"].eq(periodo_filtro), "AnioAnalisis"],
            errors="coerce",
        ).dropna()
        anio_actual = int(anios_periodo.max()) if not anios_periodo.empty else None
    else:
        anios_disponibles = pd.to_numeric(
            scope["AnioAnalisis"], errors="coerce"
        ).dropna()
        anio_actual = (
            int(anios_disponibles.max()) if not anios_disponibles.empty else None
        )

    fig = go.Figure()
    if anio_actual is None:
        return fig
    anio_anterior = anio_actual - 1

    anios_numericos = pd.to_numeric(scope["AnioAnalisis"], errors="coerce")
    actual = scope[anios_numericos.eq(anio_actual)].copy()
    anterior = scope[anios_numericos.eq(anio_anterior)].copy()

    if periodo_filtro != "Todos":
        periodo_actual = int(periodo_filtro)
        periodo_anterior = periodo_actual - 100
        actual = actual[
            pd.to_numeric(actual["Periodo"], errors="coerce").eq(periodo_actual)
        ]
        anterior = anterior[
            pd.to_numeric(anterior["Periodo"], errors="coerce").eq(periodo_anterior)
        ]

    actual = base_hogar(actual)
    anterior = base_hogar(anterior)
    orden_quintiles = [f"Quintil {numero}" for numero in range(1, 6)] + [
        "Sin información de empleo"
    ]
    orden_clusters_base = ["AAA", "AA", "A", "B", "Sin cluster"]

    def resumir(base: pd.DataFrame) -> pd.DataFrame:
        if base.empty:
            return pd.DataFrame(
                columns=["ClusterVisual", "QuintilActual", "Presion", "Hogares"]
            )
        work = base.copy()
        work["ClusterVisual"] = (
            work["Cluster"].fillna("Sin cluster").astype(str)
        )
        deuda = pd.to_numeric(
            work.get("DeudaTotalHogar", 0), errors="coerce"
        ).fillna(0)
        ingreso = pd.to_numeric(
            work.get("IngresoAnualHogarActual", 0), errors="coerce"
        ).fillna(0)
        indice = pd.to_numeric(
            work.get("IndicePresionDeudaIngresoAnual", np.nan), errors="coerce"
        )
        work["FlagPresionMatriz"] = (
            deuda.gt(0) & (ingreso.le(0) | indice.gt(1))
        ).fillna(False)
        return (
            work[work["QuintilActual"].isin(orden_quintiles)]
            .groupby(["ClusterVisual", "QuintilActual"], observed=True)
            .agg(
                Presion=("FlagPresionMatriz", "mean"),
                Hogares=("FlagPresionMatriz", "size"),
            )
            .reset_index()
        )

    resumen_actual = resumir(actual)
    resumen_anterior = resumir(anterior)
    clusters_presentes = set(resumen_actual["ClusterVisual"]).union(
        resumen_anterior["ClusterVisual"]
    )
    orden_clusters = [
        cluster for cluster in orden_clusters_base if cluster in clusters_presentes
    ] + sorted(clusters_presentes.difference(orden_clusters_base))

    if not orden_clusters:
        fig.add_annotation(
            text="No hay información comparable con el año anterior",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=13, color=COLOR_GRIS),
        )
        return fig

    def pivotar(tabla: pd.DataFrame, valor: str) -> pd.DataFrame:
        return (
            tabla.pivot(
                index="ClusterVisual",
                columns="QuintilActual",
                values=valor,
            )
            .reindex(index=orden_clusters, columns=orden_quintiles)
        )

    presion_actual = pivotar(resumen_actual, "Presion")
    presion_anterior = pivotar(resumen_anterior, "Presion")
    hogares_actual = pivotar(resumen_actual, "Hogares")
    hogares_anterior = pivotar(resumen_anterior, "Hogares")
    diferencia = presion_actual - presion_anterior
    valores_validos = diferencia.to_numpy(dtype=float)
    max_abs = np.nanmax(np.abs(valores_validos)) if np.isfinite(valores_validos).any() else 0.1
    max_abs = max(float(max_abs), 0.05)

    texto = np.empty(diferencia.shape, dtype=object)
    for fila in range(diferencia.shape[0]):
        for columna in range(diferencia.shape[1]):
            valor = diferencia.iloc[fila, columna]
            texto[fila, columna] = (
                f"{valor * 100:+.1f} pp" if pd.notna(valor) else "Sin dato"
            )
    customdata = np.stack(
        [
            presion_actual.to_numpy(dtype=float),
            presion_anterior.to_numpy(dtype=float),
            hogares_actual.to_numpy(dtype=float),
            hogares_anterior.to_numpy(dtype=float),
        ],
        axis=-1,
    )

    fig.add_trace(
        go.Heatmap(
            z=diferencia.to_numpy(dtype=float),
            x=[
                quintil.replace("Sin información de empleo", "Sin información")
                for quintil in orden_quintiles
            ],
            y=orden_clusters,
            zmin=-max_abs,
            zmax=max_abs,
            zmid=0,
            colorscale=[
                [0.0, "#2e7d32"],
                [0.45, "#c8e6c9"],
                [0.5, "#f7f7f7"],
                [0.55, "#ffcdd2"],
                [1.0, "#c62828"],
            ],
            showscale=False,
            text=texto,
            texttemplate="%{text}",
            customdata=customdata,
            hovertemplate=(
                "<b>Clúster %{y} · %{x}</b><br>"
                f"Presión {anio_actual}: %{{customdata[0]:.1%}} "
                "(%{customdata[2]:,.0f} hogares)<br>"
                f"Presión {anio_anterior}: %{{customdata[1]:.1%}} "
                "(%{customdata[3]:,.0f} hogares)<br>"
                "Variación: %{z:+.1%}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title=dict(
            text=(
                f"Cambio de presión de deuda por clúster y quintil "
                f"({anio_anterior} → {anio_actual})"
            ),
            x=0.01,
        ),
        xaxis_title="Quintil socioeconómico",
        yaxis_title="Clúster",
        height=max(390, 75 * len(orden_clusters) + 170),
        margin=dict(l=75, r=80, t=80, b=65),
        paper_bgcolor="white",
        plot_bgcolor="white",
        annotations=[
            dict(
                text=f"Total: {len(actual):,.0f} hogares en {anio_actual}",
                x=1,
                y=1.10,
                xref="paper",
                yref="paper",
                xanchor="right",
                showarrow=False,
                font=dict(size=11, color=COLOR_GRIS),
            )
        ],
    )
    return fig


def fig_donut_estado_deuda(df: pd.DataFrame) -> go.Figure:
    hogares = base_hogar(df).copy()

    condiciones = [
        hogares["FlagTieneDeuda"].eq(0),
        (hogares["FlagTieneDeuda"].eq(1) & hogares["FlagTieneMora"].eq(0)
         & pd.to_numeric(hogares.get("FlagDeterioroCrediticioCritico", 0), errors="coerce").fillna(0).eq(0)),
        hogares["FlagTieneMora"].eq(1),
        pd.to_numeric(hogares.get("FlagCalificacionCriticaHogar", 0), errors="coerce").fillna(0).eq(1),
        (pd.to_numeric(hogares.get("FlagDemandaJudicial", 0), errors="coerce").fillna(0).eq(1)
         | pd.to_numeric(hogares.get("FlagCarteraCastigada", 0), errors="coerce").fillna(0).eq(1)),
    ]

    opciones = [
        "Sin deuda",
        "Deuda sana",
        "Con mora",
        "Calificación crítica",
        "Judicial / castigada",
    ]

    hogares["EstadoDeudaVisual"] = np.select(condiciones, opciones, default="Otra")

    data = hogares["EstadoDeudaVisual"].value_counts(dropna=False).reset_index()
    data.columns = ["Estado", "Hogares"]
    data = data.sort_values("Hogares", ascending=False)

    fig = px.pie(
        data,
        names="Estado",
        values="Hogares",
        hole=0.58,
        color="Estado",
        color_discrete_map={
            "Sin deuda": "#dbeafe",
            "Deuda sana": COLOR_VERDE,
            "Con mora": COLOR_NARANJA,
            "Calificación crítica": "#ef4444",
            "Judicial / castigada": "#7c3aed",
            "Otra": "#9ca3af",
        },
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="white",
    )
    return fig


def fig_dumbbell_colegiatura(df: pd.DataFrame, filtros: dict) -> go.Figure:
    resumen = resumen_por_colegio(df)
    if resumen.empty:
        return go.Figure()

    if filtros["colegio"] != "Todos":
        colegios = [filtros["colegio"]]
    else:
        colegios = resumen.sort_values("Hogares", ascending=False).head(10)["Colegio"].tolist()

    work = resumen[resumen["Colegio"].isin(colegios)].copy()
    work = work.sort_values("PctIngresoUDLAMediano", ascending=True)
    orden_colegios = work["Colegio"].tolist()

    fig = go.Figure()

    for _, row in work.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[row["PctIngresoColegioMediano"], row["PctIngresoUDLAMediano"]],
                y=[row["Colegio"], row["Colegio"]],
                mode="lines",
                line=dict(color="#d1d5db", width=3),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=work["PctIngresoColegioMediano"],
            y=work["Colegio"],
            mode="markers",
            marker=dict(size=12, color=COLOR_VERDE),
            name="% ingreso en colegio",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=work["PctIngresoUDLAMediano"],
            y=work["Colegio"],
            mode="markers",
            marker=dict(size=12, color=COLOR_AZUL),
            name="% ingreso en UDLA",
        )
    )

    fig.update_layout(
        title="Esfuerzo económico: colegio vs UDLA",
        xaxis_tickformat=".0%",
        yaxis_title="",
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend_orientation="h",
        legend_y=1.12,
        yaxis=dict(
            title="", categoryorder="array", categoryarray=orden_colegios,
        ),
    )
    return fig


def fig_lollipop_gap_udla(df: pd.DataFrame, filtros: dict) -> tuple[go.Figure, float | None]:
    resumen = resumen_por_colegio(df)
    if resumen.empty:
        return go.Figure(), None

    columnas_numericas = [
        "GapPctUDLAMediano",
        "CostoColegioMediano",
        "CostoUDLAMediano",
        "Hogares",
    ]
    for columna in columnas_numericas:
        resumen[columna] = pd.to_numeric(resumen[columna], errors="coerce")

    resumen = resumen.dropna(
        subset=["Colegio", "GapPctUDLAMediano", "CostoColegioMediano", "CostoUDLAMediano"]
    ).copy()

    # Se excluyen valores atípicos mediante el criterio estándar de 1.5 × IQR.
    q1 = resumen["GapPctUDLAMediano"].quantile(0.25)
    q3 = resumen["GapPctUDLAMediano"].quantile(0.75)
    iqr = q3 - q1
    limite_inferior = q1 - 1.5 * iqr
    limite_superior = q3 + 1.5 * iqr
    resumen = resumen[resumen["GapPctUDLAMediano"].between(limite_inferior, limite_superior)]

    if filtros["colegio"] != "Todos":
        work = resumen[resumen["Colegio"] == filtros["colegio"]].copy()
    else:
        work = resumen.sort_values("Hogares", ascending=False).head(12).copy()

    work = work.sort_values("GapPctUDLAMediano", ascending=True)
    orden_colegios = work["Colegio"].tolist()

    if work.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay colegios dentro del rango sin valores atípicos para los filtros seleccionados.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        return fig, None

    fig = go.Figure()

    for _, row in work.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[0, row["GapPctUDLAMediano"]],
                y=[row["Colegio"], row["Colegio"]],
                mode="lines",
                line=dict(color="#d9d9d9", width=3),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=work["GapPctUDLAMediano"],
            y=work["Colegio"],
            mode="markers+text",
            marker=dict(
                size=13,
                color=np.where(work["GapPctUDLAMediano"].fillna(0) >= 0, COLOR_NARANJA, COLOR_VERDE),
            ),
            text=[f"{v:.0%}" if pd.notna(v) else "—" for v in work["GapPctUDLAMediano"]],
            textposition="middle right",
            name="Gap %",
            showlegend=False,
            customdata=np.column_stack([work["CostoColegioMediano"]]),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Gap UDLA vs. colegio: %{x:.1%}<br>"
                "Colegiatura anual del colegio: USD %{customdata[0]:,.0f}"
                "<extra></extra>"
            ),
        )
    )

    costo_udla_referencia = float(work["CostoUDLAMediano"].median())

    fig.update_layout(
        title="¿Qué % más cara o barata es la UDLA frente al colegio?",
        xaxis_tickformat=".0%",
        yaxis=dict(
            title="", categoryorder="array", categoryarray=orden_colegios,
        ),
        margin=dict(l=10, r=25, t=40, b=25),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.add_vline(x=0, line_dash="dash", line_color="#999999")
    return fig, costo_udla_referencia


def fig_resumen_matriz_1(df: pd.DataFrame) -> go.Figure:
    resumen = resumen_por_colegio(df)
    if resumen.empty:
        return go.Figure()
    resumen = resumen.sort_values("Hogares", ascending=True)

    fig = px.scatter(
        resumen,
        x="PctAmbosPadres",
        y="PctDeudaMayorIngreso",
        size="Hogares",
        color="PctCaidaIngreso",
        hover_name="Colegio",
        color_continuous_scale=[
            [0.0, "#b3d7ea"],
            [0.10, "#6baed6"],
            [0.35, "#3182bd"],
            [0.70, "#08519c"],
            [1.0, "#08306b"],
        ],
        range_color=[0, 1],
        size_max=34,
        hover_data={
            "Cluster": True,
            "PctAmbosPadres": ":.1%",
            "PctDeudaMayorIngreso": ":.1%",
            "PctCaidaIngreso": ":.1%",
        },
    )
    fig.update_layout(
        title="Capacidad económica vs. deuda superior al ingreso anual",
        xaxis_title="% hogares con ambos padres trabajando",
        yaxis_title="% hogares con deuda > ingreso anual",
        coloraxis_colorbar=dict(title="% caída<br>de ingreso", tickformat=".0%"),
        margin=dict(l=10, r=10, t=45, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_traces(
        marker=dict(
            sizemin=6,
            opacity=0.78,
            line=dict(color="rgba(8, 81, 156, 0.65)", width=0.7),
        )
    )
    return fig


def fig_resumen_matriz_2(df: pd.DataFrame) -> go.Figure:
    resumen = resumen_por_colegio(df)
    if resumen.empty:
        return go.Figure()
    resumen = resumen.sort_values("Hogares", ascending=True)

    fig = px.scatter(
        resumen,
        x="PctDeudaMalaCalifPonderado",
        y="PctIngresoUDLAMediano",
        size="Hogares",
        color="PctMora",
        hover_name="Colegio",
        color_continuous_scale="Blues",
        hover_data={
            "Cluster": True,
            "PctDeudaMalaCalifPonderado": ":.1%",
            "PctIngresoUDLAMediano": ":.1%",
            "PctMora": ":.1%",
        },
    )
    fig.update_layout(
        title="Calidad de deuda vs. esfuerzo económico UDLA",
        xaxis_title="Participación ponderada de deuda con mala calificación",
        yaxis_title="% del ingreso anual requerido por UDLA",
        margin=dict(l=10, r=10, t=45, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig


# =============================================================================
# TABLAS
# =============================================================================

def tabla_resumen_segmentos(df: pd.DataFrame) -> pd.DataFrame:
    hogares = base_hogar(df)
    data = (
        hogares.groupby("SegmentoFinancieroHogar", dropna=False)
        .size()
        .rename("Hogares")
        .reset_index()
        .sort_values("Hogares", ascending=False)
    )
    total = data["Hogares"].sum()
    data["%"] = data["Hogares"] / total if total > 0 else np.nan
    return data


def tabla_resumen_colegios(df: pd.DataFrame) -> pd.DataFrame:
    resumen = resumen_por_colegio(df)
    if resumen.empty:
        return resumen

    cols = [
        "Colegio",
        "Cluster",
        "Hogares",
        "IngresoMediano",
        "PctCaidaIngreso",
        "PctAmbosPadres",
        "PctDeudaMayorIngreso",
        "PctDeudaMalaCalifPonderado",
        "IndicePresionMediano",
        "PctIngresoUDLAMediano",
    ]
    return resumen[cols].sort_values("Hogares", ascending=False)


# =============================================================================
# APP
# =============================================================================

def main():
    df = cargar_base()

    st.markdown('<div class="main-title">Dashboard financiero del hogar</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Composición del hogar, ingresos, deuda, calidad crediticia y esfuerzo económico en colegiaturas.</div>',
        unsafe_allow_html=True,
    )

    df_filtrado, filtros = aplicar_filtros(df)
    resumen = resumen_general_hogares(df_filtrado)
    hogares = base_hogar(df_filtrado)

    # -------------------------------------------------------------------------
    # PESTAÑAS
    # -------------------------------------------------------------------------
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "1. Composición del hogar",
            "2. Ingresos y empleo",
            "3. Deuda y calidad",
            "4. Colegiatura",
        ]
    )

    # =========================================================================
    # TAB 1 - COMPOSICIÓN DEL HOGAR
    # =========================================================================
    with tab1:
        st.markdown('<div class="section-title">Segmentación financiera del hogar</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            pct_estable = (hogares["SegmentoFinancieroHogar"] == "Hogar estable").mean() if len(hogares) else np.nan
            mostrar_tarjeta("% hogares estables", porcentaje(pct_estable), "Ingreso formal, baja presión y sin deterioro.", "estable")
        with c2:
            pct_justo = (hogares["SegmentoFinancieroHogar"] == "Viviendo con lo justo").mean() if len(hogares) else np.nan
            mostrar_tarjeta("% viviendo con lo justo", porcentaje(pct_justo), "Caída de ingresos o baja de quintil con poca holgura.", "justo")
        with c3:
            pct_presion = (hogares["SegmentoFinancieroHogar"] == "Presión financiera alta").mean() if len(hogares) else np.nan
            mostrar_tarjeta("% con presión financiera alta", porcentaje(pct_presion), "Incluye deuda sin ingreso y un peso elevado de deuda crítica consolidada.", "presion_alta")

        c4, c5, c6 = st.columns(3)
        with c4:
            pct_ahogado = (hogares["SegmentoFinancieroHogar"] == "Ahogado en deuda").mean() if len(hogares) else np.nan
            mostrar_tarjeta("% ahogados en deuda", porcentaje(pct_ahogado), "Deuda extrema frente al ingreso, mora ampliada o deuda crítica muy concentrada.", "ahogado")
        with c5:
            pct_severo = (hogares["SegmentoFinancieroHogar"] == "Deterioro severo").mean() if len(hogares) else np.nan
            mostrar_tarjeta("% con deterioro severo", porcentaje(pct_severo), "Demanda judicial o cartera castigada.", "severo")
        with c6:
            mostrar_tarjeta("% sin ingresos ni deuda", porcentaje(resumen["pct_sin_ingresos_ni_deuda"]), "No se identifican ingresos formales ni deuda reportada.", "sin_ingresos_deuda")

        mostrar_detalle_tarjetas(df_filtrado, ["estable", "justo", "presion_alta", "ahogado", "severo", "sin_ingresos_deuda"], "composicion")

        col_g1, col_g2 = st.columns([1.1, 1])
        with col_g1:
            st.plotly_chart(
                preparar_grafico(fig_radar_segmentos(df_filtrado), df_filtrado),
                width="stretch",
                config=PLOTLY_CONFIG,
                key="radar_segmentos",
            )
        with col_g2:
            st.plotly_chart(
                preparar_grafico(fig_heatmap_segmento_quintil(df_filtrado), df_filtrado),
                width="stretch",
                config=PLOTLY_CONFIG,
                key="heatmap_segmento_quintil",
            )

        st.plotly_chart(
            preparar_grafico(fig_matriz_composicion(df_filtrado), df_filtrado),
            width="stretch",
            config=PLOTLY_CONFIG,
            key="matriz_composicion",
        )

        st.dataframe(
            tabla_resumen_segmentos(df_filtrado),
            width="stretch",
            hide_index=True,
        )

    # =========================================================================
    # TAB 2 - INGRESOS Y EMPLEO
    # =========================================================================
    with tab2:
        st.markdown('<div class="section-title">Ingresos, cambios recientes y estructura laboral del hogar</div>', unsafe_allow_html=True)

        tarjetas_ingresos = [
            ("% hogares con caída de ingresos", porcentaje(resumen["pct_caida_ingreso"]), "Cambio reciente negativo del ingreso formal del hogar.", "caida_ingreso"),
            ("% hogares que bajaron de quintil", porcentaje(resumen["pct_baja_quintil"]), "Cambio del quintil actual respecto al anterior.", "baja_quintil"),
            ("% hogares que subieron de quintil", porcentaje(resumen["pct_sube_quintil"]), "Mejora reciente de quintil.", "sube_quintil"),
            ("Ingreso mensual mediano", moneda(resumen["ingreso_mediano"]), "Mediana del ingreso mensual formal del hogar.", "ingreso_mediano"),
            ("% ambos padres trabajando", porcentaje(resumen["pct_ambos_padres"]), "Hogares con padre y madre con empleo formal.", "ambos_padres"),
            ("% solo padre", porcentaje(resumen["pct_solo_padre"]), "Solo el padre presenta empleo formal.", "solo_padre"),
            ("% solo madre", porcentaje(resumen["pct_solo_madre"]), "Solo la madre presenta empleo formal.", "solo_madre"),
            ("% ninguno trabaja", porcentaje(resumen["pct_ninguno"]), "No se identificó empleo formal en ninguno de los progenitores.", "ninguno_trabaja"),
        ]
        for inicio in range(0, len(tarjetas_ingresos), 4):
            columnas_tarjetas = st.columns(4)
            for columna, (titulo, valor, ayuda, detalle_id) in zip(
                columnas_tarjetas, tarjetas_ingresos[inicio:inicio + 4]
            ):
                with columna:
                    mostrar_tarjeta(titulo, valor, ayuda, detalle_id)

        mostrar_detalle_tarjetas(df_filtrado, [item[3] for item in tarjetas_ingresos], "ingresos")

        comparacion = comparativos_scope(df_filtrado, filtros)

        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(
                preparar_grafico(fig_lollipop_divergente(
                    comparacion,
                    "PctCaidaIngreso",
                    "PctSubeIngreso",
                    "Caída vs. aumento de ingresos",
                ), df_filtrado),
                width="stretch",
                config=PLOTLY_CONFIG,
                key="lollipop_ingresos",
            )
        with col_b:
            altura_comparacion = max(430, 34 * len(comparacion) + 120)
            st.plotly_chart(
                preparar_grafico(
                    fig_transicion_quintiles(df_filtrado, altura=altura_comparacion),
                    df_filtrado,
                ),
                width="stretch",
                config=PLOTLY_CONFIG,
                key="transicion_quintiles",
            )

        st.plotly_chart(
            preparar_grafico(fig_empleo_quintil(df_filtrado), df_filtrado),
            width="stretch",
            config=PLOTLY_CONFIG,
            key="heatmap_empleo_quintil",
        )

    # =========================================================================
    # TAB 3 - DEUDA Y CALIDAD
    # =========================================================================
    with tab3:
        st.markdown('<div class="section-title">Volumen, presión y calidad de la deuda del hogar</div>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            mostrar_tarjeta("% hogares con deuda", porcentaje(resumen["pct_con_deuda"]), "Participación de hogares con deuda reportada.", "con_deuda")
        with c2:
            mostrar_tarjeta("Meses de ingreso equivalentes", numero(resumen["meses_equiv_mediana"], 1), "Mediana de meses de ingreso bruto equivalentes a la deuda.", "meses_deuda")
        with c3:
            mostrar_tarjeta("% deuda > ingreso anual", porcentaje(resumen["pct_deuda_mayor_ingreso"]), "Hogares cuya deuda supera el ingreso anual.", "deuda_mayor_ingreso")
        with c4:
            mostrar_tarjeta("Índice mediano de presión deuda/ingreso", numero(resumen["idx_presion_mediano"], 2), "Deuda total sobre ingreso anual del hogar.", "indice_presion")

        c5, c6, c7, c8 = st.columns(4)
        with c5:
            mostrar_tarjeta("% hogares con mora", porcentaje(resumen["pct_mora"]), "Al menos una porción de la deuda está vencida.", "mora")
        with c6:
            mostrar_tarjeta("% con demanda judicial", porcentaje(resumen["pct_demanda"]), "Hogares con deuda judicializada.", "demanda")
        with c7:
            mostrar_tarjeta("% con cartera castigada", porcentaje(resumen["pct_castigada"]), "Hogares con cartera castigada.", "castigada")
        with c8:
            mostrar_tarjeta("% deuda mal calificada / deuda total", porcentaje(resumen["pct_deuda_mala_calif_ponderado"]), "Participación ponderada de deuda con mala calificación.", "mala_calif")

        c9, c10 = st.columns(2)
        with c9:
            mostrar_tarjeta("Índice ponderado de deterioro crediticio", porcentaje(resumen["idx_deterioro_ponderado"]), "Exposición crítica total sobre deuda total.", "deterioro")
        with c10:
            mostrar_tarjeta("% sin ingresos formales ni deuda", porcentaje(resumen["pct_sin_ingresos_ni_deuda"]), "Sirve para distinguir hogares sin exposición financiera observada.", "sin_ingresos_deuda_deuda")

        mostrar_detalle_tarjetas(df_filtrado, ["con_deuda", "meses_deuda", "deuda_mayor_ingreso", "indice_presion", "mora", "demanda", "castigada", "mala_calif", "deterioro", "sin_ingresos_deuda_deuda"], "deuda")

        mostrar_outliers_deuda = st.checkbox(
            "Mostrar valores atípicos (outliers)",
            value=True,
            key="mostrar_outliers_box_deuda",
        )
        st.plotly_chart(
            preparar_grafico(
                fig_box_deuda_por_quintil(
                    df_filtrado,
                    mostrar_outliers=mostrar_outliers_deuda,
                ),
                df_filtrado,
            ),
            width="stretch",
            config=PLOTLY_CONFIG,
            key="box_deuda_por_quintil",
        )

        st.plotly_chart(
            preparar_grafico(
                fig_indicadores_deuda_por_colegio(df_filtrado),
                df_filtrado,
            ),
            width="stretch",
            config=PLOTLY_CONFIG,
            key="indicadores_deuda_por_colegio",
        )

        st.plotly_chart(
            preparar_grafico(
                fig_radar_riesgo_deuda(df, filtros),
                df_filtrado,
            ),
            width="stretch",
            config=PLOTLY_CONFIG,
            key="radar_riesgo_deuda",
        )

        st.plotly_chart(
            preparar_grafico(
                fig_matriz_cambio_presion_deuda(df, filtros),
                df_filtrado,
            ),
            width="stretch",
            config=PLOTLY_CONFIG,
            key="matriz_cambio_presion_deuda",
        )

    # =========================================================================
    # TAB 4 - COLEGIATURA
    # =========================================================================
    with tab4:
        st.markdown('<div class="section-title">Esfuerzo económico en colegiaturas: colegio vs UDLA</div>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            mostrar_tarjeta("% del ingreso anual gastado en colegio", porcentaje(resumen["pct_ingreso_colegio"]), "Mediana del peso del colegio sobre el ingreso anual.", "ingreso_colegio")
        with c2:
            mostrar_tarjeta("% del ingreso anual requerido por UDLA", porcentaje(resumen["pct_ingreso_udla"]), "Mediana del esfuerzo económico requerido por UDLA.", "ingreso_udla")
        with c3:
            brecha_esfuerzo = None
            if pd.notna(resumen["pct_ingreso_udla"]) and pd.notna(resumen["pct_ingreso_colegio"]):
                brecha_esfuerzo = resumen["pct_ingreso_udla"] - resumen["pct_ingreso_colegio"]
            mostrar_tarjeta("Brecha de esfuerzo", porcentaje(brecha_esfuerzo), "Diferencia en puntos relativos del ingreso anual.", "brecha_esfuerzo")
        with c4:
            mostrar_tarjeta("% promedio en que UDLA es más cara", porcentaje(resumen["gap_pct_udla"]), "Gap porcentual mediano entre costo UDLA y colegio.", "gap_udla")

        mostrar_detalle_tarjetas(df_filtrado, ["ingreso_colegio", "ingreso_udla", "brecha_esfuerzo", "gap_udla"], "colegiatura")

        col_g1, col_g2 = st.columns([1.1, 1])
        with col_g1:
            st.plotly_chart(
                preparar_grafico(fig_dumbbell_colegiatura(df_filtrado, filtros), df_filtrado),
                width="stretch",
                config=PLOTLY_CONFIG,
                key="dumbbell_colegiatura",
            )
        with col_g2:
            fig_gap_udla, costo_udla_referencia = fig_lollipop_gap_udla(df_filtrado, filtros)
            st.plotly_chart(
                preparar_grafico(fig_gap_udla, df_filtrado),
                width="stretch",
                config=PLOTLY_CONFIG,
                key="lollipop_gap_udla",
            )
            if costo_udla_referencia is not None:
                st.caption(
                    f"Referencia: colegiatura anual mediana UDLA = USD {costo_udla_referencia:,.0f}"
                )

if __name__ == "__main__":
    main()
