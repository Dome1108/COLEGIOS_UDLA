"""DwhStage..DocumentadosColegiosMINEDU_Nuevo (autenticacion Windows) y

codigo_colegio = COALESCE(CodColegioBanner_Sales, CodColegioAMIED) -- en ese
orden de prioridad, CodColegioBanner_Sales primero, y si
no hay dato ahi, se usa CodColegioAMIED.


Leads (L) y Afluentes (A) vienen agregados a nivel
(periodo, codigo_colegio, CodBanner) -- no a nivel de colegio AMIE. Un mismo
codigo AMIE puede estar registrado bajo varios CodBanner en Banner, y cada uno
trae su propio total de L y A. Se toma un valor por CodBanner y recien ahi se
suman al nivel del colegio; nunca se suman a nivel fila de estudiante.

Graduados si es atributo del colegio AMIE (dato MINEDUC): se toma con "first"
y NO se suma por CodBanner, o se duplicarian los graduados del colegio.

Consultor es un atributo de (PeriodoBanner_Sales, CodBanner), no del colegio:
un mismo codigo_colegio puede tener consultores distintos en el mismo periodo
si tiene varios CodBanner. Por eso el resumen queda a nivel (periodo,
codigo_colegio, CodBanner/cod_banner_colegio) -- HomologadoCodBannerColegio es
el identificador real de cada "cuenta"; un colegio (codigo_colegio/AMIE) puede
aparecer en mas de una fila por periodo si tiene varias cuentas Banner.
Consultor se agrega con "first" dentro de ese grano (es constante ahi, no hace
falta sumarlo ni desambiguarlo). Cualquier consumidor que sume graduados_total
directamente sobre el resumen debe primero colapsar a (periodo, codigo_colegio)
con "first", o lo duplicara por cada cuenta Banner. Los datos de Consultor solo
existen desde el periodo 202420 en adelante; periodos anteriores quedan nulos.
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

COL_CODBANNER = "HomologadoCodBannerColegio"

# Un consultor por (PeriodoBanner_Sales, HomologadoCodBannerColegio) -- mismo
# nivel que L y A. Se agrega al grano del resumen (no con "first" como los
# atributos de colegio) porque dos CodBanner del mismo colegio en el mismo
# periodo pueden traer consultores distintos.
COL_CONSULTOR = "Consultor"

# Centinelas que la tabla usa en lugar de NULL para "no se identifico el
# colegio" (NombreInstitucionAMIED = "SIN INFORMACION DE COLEGIO").
CODIGOS_SIN_COLEGIO = ["ND"]

# Agregados a nivel (PeriodoBanner_Sales, codigo_colegio, CodBanner): se toma
# un valor por CodBanner y luego se suman al nivel del colegio.
CAMPOS_NIVEL_CODBANNER = ["L", "A"]

# Atributos del colegio AMIE, constantes dentro de (PeriodoBanner_Sales,
# codigo_colegio) -- se usa "first", nunca se suman.
CAMPOS_COLEGIO_CONSTANTES = [
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
    """codigo_colegio = CodColegioBanner_Sales y si no hay dato, CodColegioAMIED.
    Los centinelas de CODIGOS_SIN_COLEGIO se normalizan a nulo: si entraran como
    un codigo mas, "SIN INFORMACION DE COLEGIO" seria el colegio con mas leads
    de todos los periodos."""
    df = df.copy()
    banner, amie = (
        df[col].mask(df[col].isin(CODIGOS_SIN_COLEGIO))
        for col in ("CodColegioBanner_Sales", "CodColegioAMIED")
    )
    df["codigo_colegio"] = banner.fillna(amie)
    return df

############################
## TABLA RESUMEN
############################
def sumar_por_codbanner(df: pd.DataFrame, llaves: list) -> pd.DataFrame:
    """L y A totalizados por CodBanner: un valor por grupo (llaves + CodBanner,
    sin duplicar CodBanner si ya viene incluido en `llaves`) y despues la suma
    al nivel de `llaves`. Devuelve un DataFrame indexado por `llaves` con las
    columnas L y A.

    La tabla pone el total en una sola fila del grupo y 0 en las demas, por eso
    se toma el maximo. Solo hay conflicto real si dos filas del mismo grupo
    traen valores distintos de cero."""
    grupos = llaves if COL_CODBANNER in llaves else llaves + [COL_CODBANNER]

    no_cero = df[grupos + CAMPOS_NIVEL_CODBANNER].copy()
    no_cero[CAMPOS_NIVEL_CODBANNER] = no_cero[CAMPOS_NIVEL_CODBANNER].where(
        no_cero[CAMPOS_NIVEL_CODBANNER] > 0
    )
    ambiguos = (
        no_cero.groupby(grupos, dropna=False)[CAMPOS_NIVEL_CODBANNER]
        .nunique()
        .gt(1)
        .any(axis=1)
        .sum()
    )
    if ambiguos:
        print(
            f"ADVERTENCIA: {ambiguos:,} grupos (periodo, colegio, CodBanner) traen "
            "mas de un valor distinto de cero en L o A; se toma el maximo."
        )

    totales = df.groupby(grupos, dropna=False)[CAMPOS_NIVEL_CODBANNER].max()
    if grupos == llaves:
        return totales
    return totales.groupby(level=llaves).sum()


def construir_bucket_sin_colegio(df: pd.DataFrame, periodos) -> pd.DataFrame:
    """Una fila por periodo con los registros que no se pudieron atribuir a
    ningun colegio (centinela "ND" o sin ningun codigo), para que los totales
    del dashboard cuadren con el total de la tabla origen.

    Aqui L y A NO son totales repetidos: estas filas no tienen CodBanner y cada
    una trae su propio valor, asi que se suman directo. Se limita a `periodos`
    -- los que si tienen algun colegio identificado -- porque los demas son
    100% sin colegio y solo agregarian periodos vacios al dashboard."""
    sin_colegio = df[df["codigo_colegio"].isna() & df["PeriodoBanner_Sales"].isin(periodos)]

    bucket = (
        sin_colegio.groupby("PeriodoBanner_Sales")
        .agg(leads=("L", "sum"), afluentes=("A", "sum"), documentados=("IdBanner", "nunique"))
        .reset_index()
    )
    bucket["codigo_colegio"] = CODIGOS_SIN_COLEGIO[0]
    bucket["nombre_institucion"] = "SIN INFORMACION DE COLEGIO"
    return bucket


def construir_resumen(df: pd.DataFrame) -> pd.DataFrame:
    """Grano (PeriodoBanner_Sales, codigo_colegio, HomologadoCodBannerColegio):
    HomologadoCodBannerColegio (cod_banner_colegio) es la cuenta Banner real, y
    es el identificador correcto para analisis por consultor -- un mismo
    codigo_colegio (AMIE) puede tener varias cuentas Banner con consultores
    distintos en el mismo periodo, y agrupar solo por codigo_colegio (o peor,
    por nombre_institucion) las mezclaria. Consultor se toma con "first" porque
    es constante dentro de (periodo, CodBanner) -- ver docstring del modulo."""
    identificados = df.dropna(subset=["codigo_colegio"])
    llaves = ["PeriodoBanner_Sales", "codigo_colegio", COL_CODBANNER]

    resumen = (
        identificados.groupby(llaves, dropna=False)
        .agg({
            **{col: "first" for col in CAMPOS_COLEGIO_CONSTANTES + CAMPOS_METADATA_COLEGIO + [COL_CONSULTOR]},
            "IdBanner": "nunique",
        })
        .join(sumar_por_codbanner(identificados, llaves))
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
        COL_CODBANNER: "cod_banner_colegio",
        "Consultor": "consultor",
    })

    bucket = construir_bucket_sin_colegio(df, resumen["PeriodoBanner_Sales"].unique())
    return pd.concat([resumen, bucket], ignore_index=True)


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
