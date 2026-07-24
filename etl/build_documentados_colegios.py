"""DwhStage..DocumentadosColegiosMINEDU_Nuevo (autenticacion Windows) y

codigo_colegio = COALESCE(CodColegioBanner_Sales, CodColegioAMIED) -- en ese
orden de prioridad, CodColegioBanner_Sales primero, y si
no hay dato ahi, se usa CodColegioAMIED.


Leads (L) y Afluentes (A) si son agregados a nivel colegio (como Graduados):
se repiten iguales en todas las filas de un mismo periodo+colegio, así que se
toman con "first", nunca se suman a nivel fila de estudiante.
"""
import os
from pathlib import Path
from urllib.parse import quote_plus

import duckdb
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")

DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
TABLA = "DwhStage..DocumentadosColegiosMINEDU_Nuevo"

##############################
## CLASIFICACIÓN DE CAMPO
##############################

# Agregados a nivel (PeriodoBanner_Sales, codigo_colegio) -- se usa "first"
# para todos, nunca se suma nada a nivel de fila de estudiante.
CAMPOS_COLEGIO_CONSTANTES = [
    "L", "A",
    "EstudiantesFemeninoTercerAñoBACH",
    "EstudiantesMasculinoTercerAñoBACH",
    "GraduadosColegioAMIED",
]

CAMPOS_METADATA_COLEGIO = [
    "NombreInstitucionAMIED", "ProvinciaAMIED", "CantonAMIED", "ZonaInecAMIED",
    "RegimenAMIED", "Sostenimiento", "Cluster", "BACHILLERATO PENSIÓN",
    "RangoPension", "AñoGraduacionAMIED",
]

#############################
## AUTENTIFICACIÓN Y CONEXIÓN
#############################
def get_engine_windows_auth():
    if not DB_SERVER or not DB_NAME:
        raise RuntimeError(
            "Faltan DB_SERVER/DB_NAME en .env para conectar a DwhStage."
        )
    driver = quote_plus("ODBC Driver 17 for SQL Server")
    conn_str = f"mssql+pyodbc://@{DB_SERVER}/{DB_NAME}?driver={driver}&trusted_connection=yes"
    return create_engine(conn_str)

#############################
## EXTRACCIÓN DE LA TABLA
#############################
def extraer_detalle(engine) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {TABLA}", engine)

#############################
## CODAMIE, SI ES NULO TOMA EL SIGUIENTE
#############################
def agregar_codigo_colegio(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["codigo_colegio"] = df["CodColegioBanner_Sales"].fillna(df["CodColegioAMIED"])
    return df

############################
## TABLA RESUMEN
############################
def construir_resumen(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["codigo_colegio"])

    resumen = (
        df.groupby(["PeriodoBanner_Sales", "codigo_colegio"], dropna=False)
        .agg({
            **{col: "first" for col in CAMPOS_COLEGIO_CONSTANTES + CAMPOS_METADATA_COLEGIO},
            "IdBanner": "nunique",
        })
        .reset_index()
    )
    ## Renombro columnas--------------------------------------------
    resumen = resumen.rename(columns={
        "EstudiantesFemeninoTercerAñoBACH": "graduados_mujeres",
        "EstudiantesMasculinoTercerAñoBACH": "graduados_hombres",
        "GraduadosColegioAMIED": "graduados_total",
        "IdBanner": "documentados",
        "L": "leads",
        "A": "afluentes",
        "NombreInstitucionAMIED": "nombre_institucion",
        "ProvinciaAMIED": "provincia",
        "CantonAMIED": "canton",
        "ZonaInecAMIED": "zona",
        "RegimenAMIED": "regimen",
        "Sostenimiento": "sostenimiento",
        "Cluster": "cluster",
        "BACHILLERATO PENSIÓN": "pension",
        "RangoPension": "rango_pension",
        "AñoGraduacionAMIED": "anio_graduacion_mineduc",
    })
    return resumen


def guardar_parquet(df: pd.DataFrame, path: Path) -> None:
    con = duckdb.connect()
    con.register("tmp_df", df)
    con.execute(f"COPY tmp_df TO '{path.as_posix()}' (FORMAT PARQUET)")
    con.close()


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    engine = get_engine_windows_auth()
    print(f"Conectando a {DB_SERVER}/{DB_NAME} (autenticacion Windows) y extrayendo '{TABLA}'...")
    detalle = extraer_detalle(engine)
    print(f"Se extrajeron {len(detalle):,} filas (grano IdBanner).")

    detalle = agregar_codigo_colegio(detalle)
    sin_codigo = detalle["codigo_colegio"].isna().sum()
    if sin_codigo:
        print(f"ADVERTENCIA: {sin_codigo:,} filas sin CodColegioBanner_Sales ni CodColegioAMIED.")

    resumen = construir_resumen(detalle)
    print(f"Resumen (periodo x colegio): {len(resumen):,} filas.")
    print(
        f"Totales nacionales -> Leads: {resumen['leads'].sum():,.0f}  "
        f"Afluentes: {resumen['afluentes'].sum():,.0f}  "
        f"Documentados (conteo IdBanner, con colegio): {resumen['documentados'].sum():,.0f}"
    )

    detalle_path = DATA_DIR / "documentados_colegios_detalle.parquet"
    resumen_path = DATA_DIR / "documentados_colegios_resumen.parquet"

    guardar_parquet(detalle, detalle_path)
    guardar_parquet(resumen, resumen_path)

    print(f"Guardado: {detalle_path}")
    print(f"Guardado: {resumen_path}")


if __name__ == "__main__":
    main()
