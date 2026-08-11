"""Extrae las series de nacimientos necesarias para el análisis de cohortes."""

from pathlib import Path

import pandas as pd


ORIGEN = Path.home() / "Downloads" / "Tabulados_series_historicas_ENV_EDF_2024_vf.xlsx"
SALIDA = Path(__file__).resolve().parent.parent / "data" / "nacimientos_cohortes.parquet"


def main() -> None:
    nacional = pd.read_excel(
        ORIGEN,
        sheet_name="1.2.5",
        header=None,
        skiprows=4,
        usecols="B,C,E,H",
        names=["anio_nacimiento", "nacimientos_total", "iess", "privados"],
    )
    nacional["ambito"] = "Nacional"

    pichincha = pd.read_excel(
        ORIGEN,
        sheet_name="1.1.2",
        header=None,
        skiprows=3,
        usecols="B,C,T",
        names=["anio_nacimiento", "nacimientos_total", "pichincha"],
    )
    pichincha["nacimientos_total"] = pichincha["pichincha"]
    pichincha["iess"] = pd.NA
    pichincha["privados"] = pd.NA
    pichincha["ambito"] = "Pichincha"

    columnas = ["ambito", "anio_nacimiento", "nacimientos_total", "iess", "privados"]
    cohortes = pd.concat([nacional[columnas], pichincha[columnas]], ignore_index=True)
    cohortes["anio_nacimiento"] = pd.to_numeric(
        cohortes["anio_nacimiento"].astype(str).str.extract(r"(\d{4})", expand=False),
        errors="coerce",
    )
    cohortes = cohortes[
        cohortes["anio_nacimiento"].between(1990, 2024)
        & cohortes["nacimientos_total"].notna()
    ].copy()
    cohortes["anio_nacimiento"] = cohortes["anio_nacimiento"].astype("int64")
    for columna in ["nacimientos_total", "iess", "privados"]:
        cohortes[columna] = pd.to_numeric(cohortes[columna], errors="coerce")

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    cohortes.to_parquet(SALIDA, index=False)
    print(cohortes.groupby("ambito")["anio_nacimiento"].agg(["min", "max", "count"]))
    print(f"Guardado: {SALIDA}")


if __name__ == "__main__":
    main()
