"""Consolida promovidos de tercero de Bachillerato de los históricos MINEDUC.

Genera una base compacta, a nivel institución y periodo, conservando los dos
campos de promovidos por sexo y añadiendo el total usado por el dashboard.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


DESCARGAS = Path.home() / "Downloads"
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ_PROYECTO / "data"

ARCHIVOS = [
    f"MINEDUC_RegistrosAdministrativos_{inicio}-{inicio + 1}-Fin.xlsx"
    for inicio in range(2013, 2023)
] + [
    "MINEDUC_RegistrosAdministrativos_2023-2024-Fin-1.xlsx",
    "1MINEDEC_RegistrosAdministrativos_2024-2025-Fin.xlsx",
]

COLUMNAS_SALIDA = [
    "Año_Lectivo",
    "Año_Egreso",
    "AMIE",
    "Nombre_Institucion",
    "Provincia",
    "Cod_Provincia",
    "Canton",
    "Cod_Canton",
    "Sostenimiento",
    "Regimen_Escolar",
    "EstudiantesFemeninoPromovidosTercerAñoBACH",
    "EstudiantesMasculinoPromovidosTercerAñoBACH",
    "TotalPromovidosTercerAñoBACH",
]


def cargar_periodo(path: Path) -> pd.DataFrame:
    es_ultimo_periodo = "2024-2025" in path.name
    fila_encabezado = 15 if es_ultimo_periodo else 16
    columnas_promovidos = [146, 147] if es_ultimo_periodo else [182, 183]
    posiciones = [0, 1, 2, 4, 5, 6, 7, 13, 15, *columnas_promovidos]

    df = pd.read_excel(
        path,
        sheet_name="Tabla n_01",
        header=fila_encabezado,
        usecols=posiciones,
        dtype=object,
        engine="openpyxl",
    )
    df.columns = [
        "Año_Lectivo",
        "AMIE",
        "Nombre_Institucion",
        "Provincia",
        "Cod_Provincia",
        "Canton",
        "Cod_Canton",
        "Sostenimiento",
        "Regimen_Escolar",
        "EstudiantesFemeninoPromovidosTercerAñoBACH",
        "EstudiantesMasculinoPromovidosTercerAñoBACH",
    ]

    df = df[df["Año_Lectivo"].notna() & df["AMIE"].notna()].copy()
    for columna in [
        "EstudiantesFemeninoPromovidosTercerAñoBACH",
        "EstudiantesMasculinoPromovidosTercerAñoBACH",
    ]:
        df[columna] = pd.to_numeric(df[columna], errors="coerce").fillna(0).astype("int64")

    df["Año_Egreso"] = (
        df["Año_Lectivo"].astype(str).str.extract(r"-(\d{4})", expand=False).astype("Int64")
    )
    df["TotalPromovidosTercerAñoBACH"] = (
        df["EstudiantesFemeninoPromovidosTercerAñoBACH"]
        + df["EstudiantesMasculinoPromovidosTercerAñoBACH"]
    )
    return df[COLUMNAS_SALIDA]


def main() -> None:
    faltantes = [nombre for nombre in ARCHIVOS if not (DESCARGAS / nombre).exists()]
    if faltantes:
        raise FileNotFoundError("Faltan históricos: " + ", ".join(faltantes))

    partes = []
    for nombre in ARCHIVOS:
        parte = cargar_periodo(DESCARGAS / nombre)
        partes.append(parte)
        print(f"{nombre}: {len(parte):,} instituciones")

    consolidado = pd.concat(partes, ignore_index=True)
    consolidado = consolidado.sort_values(
        ["Año_Egreso", "Cod_Provincia", "AMIE"], na_position="last"
    ).reset_index(drop=True)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = DATA_DIR / "graduados_tercero_bachillerato.parquet"
    excel_path = DATA_DIR / "coles_consolidado.xlsx"
    consolidado.to_parquet(parquet_path, index=False)
    consolidado.to_excel(excel_path, index=False, sheet_name="coles")

    resumen = consolidado.groupby("Año_Lectivo", as_index=False).agg(
        Instituciones=("AMIE", "size"),
        Graduados_Tercero=("TotalPromovidosTercerAñoBACH", "sum"),
    )
    print("\n", resumen.to_string(index=False))
    print(f"\nGuardado: {parquet_path}")
    print(f"Guardado: {excel_path}")


if __name__ == "__main__":
    main()
