"""ETL: construye el universo de colegios con oferta de Bachillerato a partir
de los Registros Administrativos del Ministerio de Educacion (MINEDUC/MINEDEC)
en data/external/, hasta el periodo 2024-2025 Fin.

Genera data/universo_colegios_bachillerato.parquet, grano AMIE x periodo.
"""
import re
import unicodedata
from pathlib import Path

import duckdb
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXT_DIR = DATA_DIR / "external"

PATRON_ANIO = re.compile(r"(\d{4})-\d{4}")
ULTIMO_ANIO_INCLUIDO = 2024  # Se excluye 2025-2026 Inicio a proposito

def _sin_tildes(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", t.strip())

###########################
## COLEGIOS CON BACHILLERATO
###########################

# normalizar_texto() (definida abajo) quita tildes del dato leido del Excel,
# asi que esta lista debe compararse ya sin tildes tambien -- si no, las 4
# categorias con tildes ("Educación", "Básica", etc.) nunca hacen match.
NIVELES_BACHILLERATO = {
    _sin_tildes(s)
    for s in [
        "Bachillerato",
        "Inicial, Educación Básica y Bachillerato",
        "EGB y Bachillerato",
        "Educación Básica y Bachillerato",  # sinonimo de "EGB y Bachillerato" -- unico usado en 2018-2019-Fin
        "Educación Básica, Bachillerato y Artesanal P.P.",
        "Educación Básica, Bachillarato y Alfabetizacion P.P.",
        "Educación Básica, Bachillerato,Alfabetización y Artesanal P.P.",
    ]
}

#################################
## COLUMNAS POR POSICIÓN
#################################

# Columnas de identidad/ubicacion por posicion (0-indexed) -- estable en los
# 16 archivos pese a que los nombres de columna varian levemente entre anios
# (tildes, espacios, orden de columnas extra). Ver notebooks/00_Información_Ministerio.ipynb
# para el analisis que valido estas posiciones.
COL_PERIODO_RAW = 0
COL_AMIE = 1
COL_NOMBRE = 2
COL_ZONA = 3
COL_PROVINCIA = 4
COL_CANTON = 6
COL_PARROQUIA = 8
COL_TIPO_EDUCACION = 11
COL_NIVEL_EDUCACION = 12
COL_SOSTENIMIENTO = 13
COL_AREA = 14
COL_REGIMEN = 15
COL_JURISDICCION = 16
COL_DOCENTES_F = 21
COL_DOCENTES_M = 22
COL_TOTAL_DOCENTES = 23
COL_TOTAL_ESTUDIANTES = 29

def normalizar_texto(texto):
    if not isinstance(texto, str) or not texto.strip():
        return None
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", t.strip())


def listar_archivos():
    archivos = [
        f for f in EXT_DIR.glob("*RegistrosAdministrativos*.xlsx")
        if not f.name.startswith("~$")
    ]
    con_anio = [(int(PATRON_ANIO.search(f.name).group(1)), f) for f in archivos]
    con_anio = [(anio, f) for anio, f in con_anio if anio <= ULTIMO_ANIO_INCLUIDO]
    return sorted(con_anio, key=lambda t: t[0])


def encontrar_fila_encabezado(path, max_filas=30):
    muestra = pd.read_excel(path, header=None, nrows=max_filas, engine="calamine")
    for i, fila in muestra.iterrows():
        valores = [str(v).strip() for v in fila.tolist() if v is not None]
        if "AMIE" in valores:
            return i
    raise ValueError(f"No se encontro fila de encabezado con 'AMIE' en {path.name}")

################################
## PROMOVIDOS, NO PROMOVIMOS, ABANDONO
################################

def clasificar_columnas_grado(encabezados):
    """Clasifica columnas de desglose por grado por patron de texto (no
    posicion, ya que el numero y orden de columnas de grado varia bastante
    entre anios). Sensible a mayusculas/minusculas a proposito: 'Promovido'
    (con P mayuscula) evita falsos positivos como 'FemeninoPromovido' que
    contiene 'noPromovido' en minusculas si se compara sin distinguir caso.
    """
    idx_promovido, idx_nopromovido, idx_abandono = [], [], []
    for i, nombre in enumerate(encabezados):
        if not isinstance(nombre, str):
            continue
        if "NoPromovido" in nombre:
            idx_nopromovido.append(i)
        elif "Promovido" in nombre:
            idx_promovido.append(i)
        elif "Abandono" in nombre:
            idx_abandono.append(i)
    return idx_promovido, idx_nopromovido, idx_abandono

##################################
## BUSQUEDA DE TERCERO DE BACHILLERATO
##################################
def clasificar_3er_bach(encabezados):
    """Encuentra las columnas de matricula BASE (sin desenlace) de 3er anio de
    Bachillerato, por sexo. El nombre de columna cambia de estilo entre anios:
    'EstudiantesFemeninoTercerAñoBACH' (anios viejos) vs
    'Estudiantes3erAñoBachilleratoMujeres' (MINEDEC 2024-2025) -- se busca por
    patron, no por posicion ni nombre exacto.
    """
    idx_mujeres, idx_hombres = None, None
    for i, nombre in enumerate(encabezados):
        if not isinstance(nombre, str):
            continue
        es_tercer_bach = ("TercerA" in nombre and "BACH" in nombre.upper()) or (
            "3erA" in nombre and "achillerato" in nombre
        )
        if not es_tercer_bach:
            continue
        es_desenlace = any(k in nombre for k in ["Promovido", "Abandono", "NoActualizad"])
        if es_desenlace:
            continue
        if "Femenino" in nombre or "Mujeres" in nombre:
            idx_mujeres = i
        elif "Masculino" in nombre or "Hombres" in nombre:
            idx_hombres = i
    return idx_mujeres, idx_hombres

##############################
## ME QUEDO CON LA INFORMACIÓN A ANALIZAR
##############################
def cargar_periodo(path, anio_inicio, etiqueta_periodo):
    fila_enc = encontrar_fila_encabezado(path)
    encabezados_df = pd.read_excel(path, header=None, skiprows=fila_enc, nrows=1, engine="calamine")
    encabezados = encabezados_df.iloc[0].tolist()

    idx_promovido, idx_nopromovido, idx_abandono = clasificar_columnas_grado(encabezados)
    idx_3bach_mujeres, idx_3bach_hombres = clasificar_3er_bach(encabezados)
    if idx_3bach_mujeres is None or idx_3bach_hombres is None:
        raise ValueError(f"No se encontraron columnas de 3er anio Bachillerato en {path.name}")

    columnas_identidad = [
        COL_AMIE, COL_NOMBRE, COL_ZONA, COL_PROVINCIA, COL_CANTON, COL_PARROQUIA,
        COL_TIPO_EDUCACION, COL_NIVEL_EDUCACION, COL_SOSTENIMIENTO, COL_AREA,
        COL_REGIMEN, COL_JURISDICCION, COL_DOCENTES_F, COL_DOCENTES_M,
        COL_TOTAL_DOCENTES, COL_TOTAL_ESTUDIANTES, idx_3bach_mujeres, idx_3bach_hombres,
    ]
    todas_las_columnas = sorted(set(columnas_identidad) | set(idx_promovido) | set(idx_nopromovido) | set(idx_abandono))

    df = pd.read_excel(
        path, header=None, skiprows=fila_enc + 1, usecols=todas_las_columnas, engine="calamine",
    )
    df.columns = todas_las_columnas

    def col(i):
        return pd.to_numeric(df[i], errors="coerce") if i in (
            COL_DOCENTES_F, COL_DOCENTES_M, COL_TOTAL_DOCENTES, COL_TOTAL_ESTUDIANTES
        ) else df[i]

    salida = pd.DataFrame({
        "AMIE": df[COL_AMIE].astype(str).str.strip(),
        "nombre_institucion": df[COL_NOMBRE],
        "zona": df[COL_ZONA],
        "provincia": df[COL_PROVINCIA],
        "canton": df[COL_CANTON],
        "parroquia": df[COL_PARROQUIA],
        "tipo_educacion": df[COL_TIPO_EDUCACION],
        "nivel_educacion": df[COL_NIVEL_EDUCACION],
        "sostenimiento": df[COL_SOSTENIMIENTO],
        "area": df[COL_AREA],
        "regimen_escolar": df[COL_REGIMEN],
        "jurisdiccion": df[COL_JURISDICCION],
        "docentes_femenino": col(COL_DOCENTES_F),
        "docentes_masculino": col(COL_DOCENTES_M),
        "total_docentes": col(COL_TOTAL_DOCENTES),
        "total_estudiantes_todos_grados": col(COL_TOTAL_ESTUDIANTES),
        "estudiantes_3bach_mujeres": pd.to_numeric(df[idx_3bach_mujeres], errors="coerce"),
        "estudiantes_3bach_hombres": pd.to_numeric(df[idx_3bach_hombres], errors="coerce"),
    })
    for c in ["provincia", "canton", "parroquia", "sostenimiento", "area", "regimen_escolar", "jurisdiccion", "tipo_educacion", "nivel_educacion"]:
        salida[c] = salida[c].map(normalizar_texto)

    salida["total_promovidos"] = df[idx_promovido].apply(pd.to_numeric, errors="coerce").sum(axis=1) if idx_promovido else 0
    salida["total_no_promovidos"] = df[idx_nopromovido].apply(pd.to_numeric, errors="coerce").sum(axis=1) if idx_nopromovido else 0
    salida["total_abandono"] = df[idx_abandono].apply(pd.to_numeric, errors="coerce").sum(axis=1) if idx_abandono else 0

    salida["anio_inicio"] = anio_inicio
    salida["periodo"] = etiqueta_periodo
    return salida

################################
## FILTRAR UNIVERSO DE BACHILLERATO
################################
def filtrar_universo_bachillerato(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["nivel_educacion"].isin(NIVELES_BACHILLERATO)].reset_index(drop=True)


def guardar_parquet(df: pd.DataFrame, path: Path) -> None:
    con = duckdb.connect()
    con.register("tmp_df", df)
    con.execute(f"COPY tmp_df TO '{path.as_posix()}' (FORMAT PARQUET)")
    con.close()


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    archivos = listar_archivos()
    print(f"Archivos a procesar (hasta {ULTIMO_ANIO_INCLUIDO}-{ULTIMO_ANIO_INCLUIDO + 1} Fin): {len(archivos)}")

    periodos = []
    for anio_inicio, path in archivos:
        etiqueta_periodo = PATRON_ANIO.search(path.name).group(0)
        df_periodo = cargar_periodo(path, anio_inicio, etiqueta_periodo)
        periodos.append(df_periodo)
        print(f"{path.name}: {len(df_periodo):,} filas totales")

    panel = pd.concat(periodos, ignore_index=True)
    universo = filtrar_universo_bachillerato(panel)

    print()
    print(f"Panel completo: {len(panel):,} filas")
    print(f"Universo Bachillerato (6 categorias de Nivel_Educacion): {len(universo):,} filas")
    print(universo["nivel_educacion"].value_counts())

    salida_path = DATA_DIR / "universo_colegios_bachillerato.parquet"
    guardar_parquet(universo, salida_path)
    print(f"Guardado: {salida_path}")


if __name__ == "__main__":
    main()
