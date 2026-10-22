"""Tablas del plan para mostrar y descargar (Excel / CSV)."""

import io

import numpy as np
import pandas as pd

from .datos import COLUMNAS_ZONAS, ETIQUETAS
from .modelo import detallar
from .solver import tabla_resultados


def tabla_plan(p, sol):
    """Plan por zona de una solución, en términos de campo (por m² y totales)."""
    d = detallar(p, sol)
    y = np.asarray(sol["y"]) == 1
    df = pd.DataFrame(index=pd.Index(p.nombres, name="Zona"))
    df["¿Intervenir?"] = np.where(y, "Sí", "No")
    df["Área (m²)"] = p.A
    for j, c in enumerate(p.consorcios):
        df[f"Consorcio {c.lower()} (L/m²)"] = sol["x"][:, j].round(2)
        df[f"Consorcio {c.lower()} total (L)"] = (sol["x"][:, j] * p.A).round(0)
    df["Nitrógeno (kg/m²)"] = sol["N"].round(3)
    df["Nitrógeno total (kg)"] = (sol["N"] * p.A).round(1)
    df["Fósforo (kg/m²)"] = (sol["N"] / 10).round(4)
    df["Fósforo total (kg)"] = (sol["N"] / 10 * p.A).round(1)
    df["Cal (kg/m²)"] = sol["L"].round(2)
    df["Cal total (kg)"] = (sol["L"] * p.A).round(0)
    df["k (1/día)"] = d["k"].round(4)
    df["TPH inicial (mg/kg)"] = p.C0.round(0)
    df["TPH final (mg/kg)"] = d["C_final"].round(0)
    df["Límite (mg/kg)"] = p.Clim.round(0)
    df["¿Cumple?"] = np.where(d["C_final"] <= p.Clim + 1, "Sí", "No")
    return df


def tabla_parametros(esc):
    filas = [{"Parámetro": nombre, "Valor": getattr(esc, campo), "Unidad": unidad, "Fuente": fuente or "—"}
             for campo, (nombre, unidad, fuente) in ETIQUETAS.items()]
    return pd.DataFrame(filas)


def excel_plan(p, frente, i_sel):
    """Libro de Excel con el plan elegido, el frente, los costos y los datos usados."""
    sol = frente["soluciones"][i_sel]
    d = detallar(p, sol)
    resumen = pd.DataFrame({
        "Concepto": ["Punto del frente", "Contaminante eliminado (%)", "Costo total (M COP)"] +
                    [f"Costo {k} (M COP)" for k in d["costos"]] +
                    ["Tiempo de tratamiento (días)", "Temperatura (°C)"],
        "Valor": [i_sel, round(100 * sol["f1"], 2), round(sol["f2"], 2)] +
                 [round(v, 2) for v in d["costos"].values()] + [p.esc.t_trat, p.esc.temp]})
    zonas = p.esc.zonas.rename(columns=COLUMNAS_ZONAS)
    zonas.index.name = "Zona"
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        resumen.to_excel(w, sheet_name="Resumen", index=False)
        tabla_plan(p, sol).to_excel(w, sheet_name="Plan por zona")
        tabla_resultados(p, frente["soluciones"]).to_excel(w, sheet_name="Frente de Pareto", index=False)
        zonas.to_excel(w, sheet_name="Zonas")
        tabla_parametros(p.esc).to_excel(w, sheet_name="Parámetros", index=False)
        p.esc.consorcios.to_excel(w, sheet_name="Consorcios")
        for hoja in w.sheets.values():
            for col in hoja.columns:
                hoja.column_dimensions[col[0].column_letter].width = max(
                    12, min(45, max(len(str(c.value or "")) for c in col) + 2))
    return buf.getvalue()


def csv_frente(p, frente):
    return tabla_resultados(p, frente["soluciones"]).to_csv(index=False).encode("utf-8-sig")
