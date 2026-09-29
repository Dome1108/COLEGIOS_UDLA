"""Carga las fuentes del dashboard, cacheadas en memoria.

Captacion UDLA y Mercado Alertas consultan SQL Server directamente con la
sesion de Windows que ejecuta Streamlit. Universo conserva su fuente Parquet,
porque proviene de los archivos historicos del Ministerio.
"""
import os
from pathlib import Path
from urllib.parse import quote_plus

import duckdb
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

ENV_PATH = BASE_DIR / ".env"


def _leer_parquet(nombre_archivo: str) -> pd.DataFrame:
    path = DATA_DIR / nombre_archivo
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró {path}. Corre etl/build_resumen.py primero."
        )
    return duckdb.sql(f"SELECT * FROM read_parquet('{path.as_posix()}')").df()


@st.cache_data
def cargar_universo_colegios() -> pd.DataFrame:
    """Universo de colegios con oferta de Bachillerato (MINEDUC/MINEDEC,
    hasta 2024-2025 Fin). Ver etl/build_universo_colegios.py."""
    return _leer_parquet("universo_colegios_bachillerato.parquet")


def _configuracion_documentados() -> tuple[str, str, str]:
    """Lee .env en cada ejecucion de pagina, incluso si se creo tras iniciar Streamlit."""
    # ``override=True`` es importante: Streamlit mantiene el mismo proceso al
    # recargar una pagina; asi se reemplazan valores vacios heredados de un
    # inicio anterior por los valores actuales del archivo .env.
    load_dotenv(ENV_PATH, override=True)
    db_server = os.getenv("DB_SERVER")
    db_name = os.getenv("DB_NAME")
    tabla = os.getenv(
        "DB_DOCUMENTADOS_TABLE", "DwhStage..DocumentadosColegiosMINEDU_Nuevo"
    )
    if not db_server or not db_name:
        raise RuntimeError(
            f"Faltan DB_SERVER o DB_NAME en {ENV_PATH} para consultar los datos de captacion."
        )
    return db_server, db_name, tabla


@st.cache_resource
def _motor_documentados(db_server: str, db_name: str):
    """Crea una conexion SQL Server con autenticacion integrada de Windows.

    ``odbc_connect`` evita que caracteres de una instancia SQL, como la barra
    invertida de ``SERVIDOR\\INSTANCIA``, se interpreten como parte de una URL.
    Los valores TLS son configurables desde .env y permiten conectar a un SQL
    Server interno con certificado no publico. No usa usuario ni contrasena de
    SQL: ``Trusted_Connection=yes`` toma la sesion Windows actual.
    """
    driver = os.getenv("DB_ODBC_DRIVER", "ODBC Driver 17 for SQL Server")
    encrypt = os.getenv("DB_ENCRYPT", "no")
    trust_certificate = os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes")
    odbc = ";".join([
        f"DRIVER={{{driver}}}",
        f"SERVER={db_server}",
        f"DATABASE={db_name}",
        "Trusted_Connection=yes",
        f"Encrypt={encrypt}",
        f"TrustServerCertificate={trust_certificate}",
    ])
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}")


def _agregar_codigo_colegio(df: pd.DataFrame) -> pd.DataFrame:
    """Prioriza el AMIE institucional de Banner y descarta el centinela ``ND``."""
    df = df.copy()
    banner = df["CodColegioBanner_Sales"].mask(
        df["CodColegioBanner_Sales"].isin(["ND"])
    )
    amie = df["CodColegioAMIED"].mask(df["CodColegioAMIED"].isin(["ND"]))
    df["codigo_colegio"] = banner.fillna(amie)
    return df


def _sumar_por_codbanner(df: pd.DataFrame, llaves: list[str]) -> pd.DataFrame:
    """Evita sumar varias veces los totales L/A repetidos por estudiante.
    No duplica CodBanner en el groupby si ya viene incluido en `llaves`."""
    grupos = llaves if "HomologadoCodBannerColegio" in llaves else llaves + ["HomologadoCodBannerColegio"]
    totales = df.groupby(grupos, dropna=False)[["L", "A"]].max()
    if grupos == llaves:
        return totales
    return totales.groupby(level=llaves).sum()


def _construir_resumen_documentados(df: pd.DataFrame) -> pd.DataFrame:
    """Replica la agregacion del ETL para que SQL sea la unica fuente activa.

    Grano (PeriodoBanner_Sales, codigo_colegio, HomologadoCodBannerColegio):
    HomologadoCodBannerColegio (cod_banner_colegio) es la cuenta Banner real y
    el identificador correcto para analisis por consultor -- un mismo
    codigo_colegio (AMIE) puede tener varias cuentas Banner con consultores
    distintos en el mismo periodo, y agrupar solo por codigo_colegio (o por
    nombre_institucion) las mezclaria. Consultor se toma con "first" porque es
    constante dentro de (periodo, CodBanner). Ver etl/build_documentados_colegios.py."""
    identificados = df.dropna(subset=["codigo_colegio"])
    llaves = ["PeriodoBanner_Sales", "codigo_colegio", "HomologadoCodBannerColegio"]
    atributos = [
        "EstudiantesFemeninoTercerAñoBACH",
        "EstudiantesMasculinoTercerAñoBACH",
        "GraduadosColegioAMIED",
        "NombreInstitucionAMIED",
        "ProvinciaAMIED",
        "CantonAMIED",
        "ZonaInecAMIED",
        "RegimenAMIED",
        "Sostenimiento",
        "Cluster",
        "BACHILLERATO PENSIÓN",
        "RangoPension",
        "AñoGraduacionAMIED",
        "Consultor",
    ]
    resumen = (
        identificados.groupby(llaves, dropna=False)
        .agg(**{col: (col, "first") for col in atributos}, documentados=("IdBanner", "nunique"))
        .join(_sumar_por_codbanner(identificados, llaves))
        .reset_index()
        .rename(columns={
            "EstudiantesFemeninoTercerAñoBACH": "graduados_mujeres",
            "EstudiantesMasculinoTercerAñoBACH": "graduados_hombres",
            "GraduadosColegioAMIED": "graduados_total",
            "L": "leads", "A": "afluentes",
            "NombreInstitucionAMIED": "nombre_institucion",
            "ProvinciaAMIED": "provincia", "CantonAMIED": "canton",
            "ZonaInecAMIED": "zona", "RegimenAMIED": "regimen",
            "Sostenimiento": "sostenimiento",
            "Cluster": "cluster",
            "BACHILLERATO PENSIÓN": "pension",
            "RangoPension": "rango_pension",
            "AñoGraduacionAMIED": "anio_graduacion_mineduc",
            "HomologadoCodBannerColegio": "cod_banner_colegio",
            "Consultor": "consultor",
        })
    )

    sin_colegio = df[
        df["codigo_colegio"].isna()
        & df["PeriodoBanner_Sales"].isin(resumen["PeriodoBanner_Sales"].unique())
    ]
    bucket = (
        sin_colegio.groupby("PeriodoBanner_Sales")
        .agg(leads=("L", "sum"), afluentes=("A", "sum"), documentados=("IdBanner", "nunique"))
        .reset_index()
    )
    bucket["codigo_colegio"] = "ND"
    bucket["nombre_institucion"] = "SIN INFORMACION DE COLEGIO"
    return pd.concat([resumen, bucket], ignore_index=True)


@st.cache_data(ttl=900, show_spinner="Consultando captacion en SQL Server...")
def _cargar_documentados_desde_sql(
    db_server: str, db_name: str, tabla_documentados: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Consulta SQL Server y construye el resumen actual en memoria."""
    detalle = pd.read_sql(
        f"SELECT * FROM {tabla_documentados}", _motor_documentados(db_server, db_name)
    )
    detalle = _agregar_codigo_colegio(detalle)
    return detalle, _construir_resumen_documentados(detalle)


def cargar_documentados_resumen() -> pd.DataFrame:
    """Resumen actual de SQL Server, con grano periodo de admision x colegio."""
    return _cargar_documentados_desde_sql(*_configuracion_documentados())[1]


def cargar_documentados_detalle() -> pd.DataFrame:
    """Detalle actual de SQL Server, con grano de estudiante/IdBanner."""
    return _cargar_documentados_desde_sql(*_configuracion_documentados())[0]


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
