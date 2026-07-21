"""ETL: extrae DwhStage..DocumentadosColegiosMINEDU (autenticacion Windows) y
construye:
- documentados_colegios_detalle.parquet: grano estudiante (IdBanner), tal cual.
- documentados_colegios_resumen.parquet: grano (PeriodoBanner_Sales, codigo_colegio).
  El funnel L/A/D se SUMA entre los distintos CodBanner de un mismo colegio+periodo
  (su granularidad real); las estadisticas del colegio (Graduados, etc.) se
  mantienen con "first" (constantes, sumarlas las inflaria). Nunca se suma
  nada a nivel de fila de estudiante (eso si esta repetido sin mas informacion).

codigo_colegio = COALESCE(CodColegioBanner_Sales, CodColegioAMIED) -- en ese
orden de prioridad, segun lo indicado: CodColegioBanner_Sales primero, y si
no hay dato ahi, se usa CodColegioAMIED.
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
TABLA = "DwhStage..DocumentadosColegiosMINEDU"

# La tabla origen trae dos tipos de campo pre-agregado, con granularidades
# DISTINTAS -- confirmado empiricamente (ver notebooks/investigacion CodBanner):
#
# 1) Funnel L/A/D: la granularidad real es (PeriodoBanner_Sales, codigo_colegio,
#    CodBanner) -- un mismo AMIE puede tener varios CodBanner (registros
#    distintos en Banner) en el mismo periodo, cada uno con su propio L/A/D.
#    Hay que sumar entre CodBanner para no perder informacion (antes de este
#    fix, tomar "first" a nivel (periodo,colegio) subestimaba D en ~7%
#    nacional -- 16,886 vs 18,066 en 2022-2024).
# 2) Estadisticas del colegio (Graduados, etc.): constantes por
#    (PeriodoBanner_Sales, codigo_colegio) sin importar el CodBanner -- se
#    usa "first", sumar las inflaria (es el mismo dato de MINEDUC repetido).
CAMPOS_FUNNEL = ["L", "A", "D"]
CAMPOS_COLEGIO_CONSTANTES = [
    "EstudiantesFemeninoTercerAñoBACH",
    "EstudiantesMasculinoTercerAñoBACH",
    "GraduadosColegioAMIED",
    "TotalDocumentadosPeriodo",  # comportamiento mixto -- ver aviso en consola
]

CAMPOS_METADATA_COLEGIO = [
    "NombreInstitucionAMIED", "ProvinciaAMIED", "CantonAMIED", "ZonaInecAMIED",
    "RegimenAMIED", "Sostenimiento", "Nuevo_cluster", "BACHILLERATO PENSIÓN",
    "RangoPension", "AñoGraduacionAMIED",
]


def get_engine_windows_auth():
    if not DB_SERVER or not DB_NAME:
        raise RuntimeError(
            "Faltan DB_SERVER/DB_NAME en .env para conectar a DwhStage."
        )
    driver = quote_plus("ODBC Driver 17 for SQL Server")
    conn_str = f"mssql+pyodbc://@{DB_SERVER}/{DB_NAME}?driver={driver}&trusted_connection=yes"
    return create_engine(conn_str)


def extraer_detalle(engine) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {TABLA}", engine)


def agregar_codigo_colegio(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["codigo_colegio"] = df["CodColegioBanner_Sales"].fillna(df["CodColegioAMIED"])
    return df


def construir_resumen(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["codigo_colegio"])

    # Paso 1: colapsar a la granularidad REAL (periodo, colegio, CodBanner).
    nivel_codbanner = (
        df.groupby(["PeriodoBanner_Sales", "codigo_colegio", "CodBanner"], dropna=False)
        .agg({col: "first" for col in CAMPOS_FUNNEL + CAMPOS_COLEGIO_CONSTANTES + CAMPOS_METADATA_COLEGIO})
        .reset_index()
    )

    # Paso 2: subir a (periodo, colegio) -- SUMAR el funnel entre CodBanner,
    # mantener "first" para las estadisticas constantes del colegio y su metadata.
    agg_map = {col: "sum" for col in CAMPOS_FUNNEL}
    agg_map.update({col: "first" for col in CAMPOS_COLEGIO_CONSTANTES + CAMPOS_METADATA_COLEGIO})
    resumen = (
        nivel_codbanner.groupby(["PeriodoBanner_Sales", "codigo_colegio"], dropna=False)
        .agg(agg_map)
        .reset_index()
    )
    resumen = resumen.rename(columns={
        "EstudiantesFemeninoTercerAñoBACH": "graduados_mujeres",
        "EstudiantesMasculinoTercerAñoBACH": "graduados_hombres",
        "GraduadosColegioAMIED": "graduados_total",
        "TotalDocumentadosPeriodo": "documentados",
        "L": "leads",
        "A": "afluentes",
        "D": "documentados_d",
        "NombreInstitucionAMIED": "nombre_institucion",
        "ProvinciaAMIED": "provincia",
        "CantonAMIED": "canton",
        "ZonaInecAMIED": "zona",
        "RegimenAMIED": "regimen",
        "Sostenimiento": "sostenimiento",
        "Nuevo_cluster": "cluster",
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
        f"Documentados (D, funnel): {resumen['documentados_d'].sum():,.0f}  "
        f"Documentados (TotalDocumentadosPeriodo): {resumen['documentados'].sum():,.0f}"
    )

    detalle_path = DATA_DIR / "documentados_colegios_detalle.parquet"
    resumen_path = DATA_DIR / "documentados_colegios_resumen.parquet"

    guardar_parquet(detalle, detalle_path)
    guardar_parquet(resumen, resumen_path)

    print(f"Guardado: {detalle_path}")
    print(f"Guardado: {resumen_path}")


if __name__ == "__main__":
    main()
