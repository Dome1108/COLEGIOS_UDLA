"""ETL: extrae la tabla fuente de SQL Server y construye
resumen_captacion_colegio.parquet y detalle_estudiante.parquet en data/.
"""
import os
from pathlib import Path
from urllib.parse import quote_plus

import duckdb
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")

DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_TABLE = os.getenv("DB_TABLE")

REQUIRED_ENV_VARS = ["DB_SERVER", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_TABLE"]

GROUP_KEYS = ["CodColegioAMIED", "AñoGraduacionAMIED"]

COLUMNAS_COLEGIO = [
    "NombreInstitucionAMIED",
    "ProvinciaAMIED",
    "CantonAMIED",
    "ZonaInecAMIED",
    "RegimenAMIED",
    "Sostenimiento",
    "Cluster",
    "PENSIÓN",
    "RangoPension",
    "GraduadosColegioAMIED",
    "TotalDocumentadosPeriodo",
]


def get_engine():
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        raise RuntimeError(
            f"Faltan variables de entorno en .env: {', '.join(missing)}. "
            "Ver .env.example."
        )

    driver = quote_plus("ODBC Driver 17 for SQL Server")
    user = quote_plus(DB_USER)
    password = quote_plus(DB_PASSWORD)

    conn_str = f"mssql+pyodbc://{user}:{password}@{DB_SERVER}/{DB_NAME}?driver={driver}"
    return create_engine(conn_str)


def extraer_detalle(engine) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {DB_TABLE}", engine)


def calcular_documentado_neto(df: pd.DataFrame) -> pd.DataFrame:
    df["DocumentadoNeto"] = ((df["Documentado"] == 1) & (df["AdIndRetiro"] == 0)).astype(int)
    return df


def chequeo_integridad_colegio(df: pd.DataFrame) -> None:
    conteo = df.groupby("CodColegioAMIED")["NombreInstitucionAMIED"].nunique()
    inconsistentes = conteo[conteo > 1]

    if inconsistentes.empty:
        print("Chequeo de integridad OK: cada CodColegioAMIED tiene un único NombreInstitucionAMIED.")
        return

    print(f"ADVERTENCIA: {len(inconsistentes)} CodColegioAMIED con más de un NombreInstitucionAMIED:")
    for cod in inconsistentes.index:
        nombres = df.loc[df["CodColegioAMIED"] == cod, "NombreInstitucionAMIED"].unique()
        print(f"  - CodColegioAMIED={cod}: {list(nombres)}")


def _safe_div(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    return (numerador / denominador).replace([np.inf, -np.inf], np.nan)


def construir_resumen(df: pd.DataFrame) -> pd.DataFrame:
    agg_map = {col: "first" for col in COLUMNAS_COLEGIO}
    agg_map.update(
        {
            "Base": "sum",
            "Afluente": "sum",
            "Matriculado": "sum",
            "Documentado": "sum",
            "DocumentadoNeto": "sum",
        }
    )

    resumen = df.groupby(GROUP_KEYS, dropna=False).agg(agg_map).reset_index()
    resumen = resumen.rename(
        columns={
            "Base": "n_base",
            "Afluente": "n_afluente",
            "Matriculado": "n_matriculado",
            "Documentado": "n_documentado_bruto",
            "DocumentadoNeto": "n_documentado_neto",
        }
    )

    resumen["tasa_base_afluente"] = _safe_div(resumen["n_afluente"], resumen["n_base"])
    resumen["tasa_afluente_matriculado"] = _safe_div(resumen["n_matriculado"], resumen["n_afluente"])
    resumen["tasa_matriculado_documentado"] = _safe_div(resumen["n_documentado_bruto"], resumen["n_matriculado"])
    resumen["tasa_retencion"] = _safe_div(resumen["n_documentado_neto"], resumen["n_documentado_bruto"])
    resumen["tasa_penetracion_mercado"] = _safe_div(resumen["n_documentado_neto"], resumen["GraduadosColegioAMIED"])

    return resumen


def guardar_parquet(df: pd.DataFrame, path: Path) -> None:
    con = duckdb.connect()
    con.register("tmp_df", df)
    con.execute(f"COPY tmp_df TO '{path.as_posix()}' (FORMAT PARQUET)")
    con.close()


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    engine = get_engine()
    print(f"Conectando a SQL Server y extrayendo tabla '{DB_TABLE}'...")
    detalle = extraer_detalle(engine)
    print(f"Se extrajeron {len(detalle):,} filas (grano IdBanner).")

    detalle = calcular_documentado_neto(detalle)

    chequeo_integridad_colegio(detalle)

    resumen = construir_resumen(detalle)

    detalle_path = DATA_DIR / "detalle_estudiante.parquet"
    resumen_path = DATA_DIR / "resumen_captacion_colegio.parquet"

    guardar_parquet(detalle, detalle_path)
    guardar_parquet(resumen, resumen_path)

    print(f"Guardado: {detalle_path}")
    print(f"Guardado: {resumen_path}")


if __name__ == "__main__":
    main()
