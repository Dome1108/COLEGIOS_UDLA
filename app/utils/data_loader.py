"""Carga los parquet generados por etl/build_resumen.py, cacheados en memoria."""
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _leer_parquet(nombre_archivo: str) -> pd.DataFrame:
    path = DATA_DIR / nombre_archivo
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró {path}. Corre etl/build_resumen.py primero."
        )
    return duckdb.sql(f"SELECT * FROM read_parquet('{path.as_posix()}')").df()


@st.cache_data
def cargar_resumen_colegio() -> pd.DataFrame:
    return _leer_parquet("resumen_captacion_colegio.parquet")


@st.cache_data
def cargar_detalle_estudiante() -> pd.DataFrame:
    return _leer_parquet("detalle_estudiante.parquet")


@st.cache_data
def cargar_universo_colegios() -> pd.DataFrame:
    """Universo de colegios con oferta de Bachillerato (MINEDUC/MINEDEC,
    hasta 2024-2025 Fin). Ver etl/build_universo_colegios.py."""
    return _leer_parquet("universo_colegios_bachillerato.parquet")


@st.cache_data
def cargar_documentados_resumen() -> pd.DataFrame:
    """Resumen (PeriodoBanner_Sales x colegio) de DwhStage..DocumentadosColegiosMINEDU.
    Ver etl/build_documentados_colegios.py."""
    return _leer_parquet("documentados_colegios_resumen.parquet")


@st.cache_data
def cargar_documentados_detalle() -> pd.DataFrame:
    """Detalle a nivel estudiante (IdBanner) de DwhStage..DocumentadosColegiosMINEDU.
    Ver etl/build_documentados_colegios.py."""
    return _leer_parquet("documentados_colegios_detalle.parquet")


# Fuente interina mientras se habilita `DB_TABLE` en SQL Server (ver etl/build_resumen.py,
# que mantiene la conexión SQL intacta). Los nombres de columna de este Excel son
# los mismos que tendrá la tabla en SQL Server, por eso no se renombran aquí.
PRELIMINAR_COLEGIOS_PATH = DATA_DIR / "processed" / "Preliminar colegios EC.xlsx"


@st.cache_data
def cargar_preliminar_colegios() -> pd.DataFrame:
    if not PRELIMINAR_COLEGIOS_PATH.exists():
        raise FileNotFoundError(f"No se encontró {PRELIMINAR_COLEGIOS_PATH}.")
    return pd.read_excel(PRELIMINAR_COLEGIOS_PATH)


PENSION_MINEDUC_PATH = DATA_DIR / "external" / "matricula-pension-mayo-2026.xlsx"


@st.cache_data
def cargar_pension_mineduc() -> pd.DataFrame:
    """Matrícula/pensión oficial del Ministerio por AMIE (snapshot mayo 2026).
    Se lee por posición de columna, no por nombre: el archivo trae caracteres
    acentuados corruptos (U+FFFD) en los encabezados al leerlo con calamine."""
    if not PENSION_MINEDUC_PATH.exists():
        raise FileNotFoundError(f"No se encontró {PENSION_MINEDUC_PATH}.")
    df = pd.read_excel(PENSION_MINEDUC_PATH, sheet_name="Table 1", engine="calamine")
    cols = df.columns.tolist()
    return pd.DataFrame({
        "AMIE": df[cols[2]].astype(str).str.strip(),
        "matricula_bachillerato": pd.to_numeric(df[cols[13]], errors="coerce"),
        "pension_bachillerato": pd.to_numeric(df[cols[14]], errors="coerce"),
    })
