"""
Optimización biobjetivo de la biorremediación de un suelo contaminado con
hidrocarburos — método ε-constraint y frente de Pareto.

Técnicas de Optimización · UPB · Entrega final
Santiago Fonseca, Matias Piedrahita

El modelo vive en el paquete `biorremediacion/` (datos, modelo, solver). Este
script resuelve el caso base y reproduce las salidas de la Entrega 2:
  1. Diagnóstico del sitio sin intervención.
  2. Frente de Pareto con el método ε-constraint (G = 15).
  3. Tabla de soluciones (resultados_pareto.csv) y gráficas
     (frente_pareto.png, dosis_por_zona.png).

Ejecutar:    python biorremediacion_econstraint.py

NOTA: el sitio es un caso de estudio ILUSTRATIVO; las fuentes de cada dato están
en biorremediacion/datos.py.
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

from biorremediacion import Parametros, escenario_base, frente_pareto, tabla_resultados  # noqa: E402
from biorremediacion.modelo import concentracion_final  # noqa: E402
from biorremediacion.solver import frente_a_json  # noqa: E402


# =============================================================================
# GRÁFICAS
# =============================================================================
def graficar_pareto(p, pareto, i_rod, archivo="frente_pareto.png"):
    f1 = np.array([100 * s["f1"] for s in pareto]); f2 = np.array([s["f2"] for s in pareto])
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.plot(f2, f1, "-o", color="#2E7D32", lw=2, ms=6, label="Soluciones de Pareto")
    ax.axvspan(0, f2[0], color="#C62828", alpha=0.08,
               label="Presupuesto insuficiente para cumplir la norma")
    marcas = {0: ("Costo mínimo", "#1565C0", (14, -6)),
              i_rod: ("Punto rodilla", "#EF6C00", (14, -30)),
              len(pareto) - 1: ("Máxima limpieza", "#6A1B9A", (-95, -38))}
    for i, (nombre, color, desfase) in marcas.items():
        ax.plot(f2[i], f1[i], "o", ms=12, mfc="none", mec=color, mew=2.5)
        ax.annotate(f"{nombre}\n{f1[i]:.1f} % · {f2[i]:.1f} M", (f2[i], f1[i]),
                    textcoords="offset points", xytext=desfase, color=color, fontsize=9)
    ax.set_xlim(0.9 * f2[0], 1.05 * f2[-1])
    ax.set_ylim(min(f1) - 3, max(f1) + 3)
    ax.set_xlabel("Costo total $f_2$ (millones de COP)")
    ax.set_ylabel("Contaminante eliminado $f_1$ (%)")
    ax.set_title(f"Frente de Pareto · método ε-constraint (T = {p.esc.t_trat} días, {p.esc.temp:.1f} °C)")
    ax.grid(alpha=0.3); ax.legend(loc="lower right")
    fig.tight_layout(); fig.savefig(archivo, dpi=200)
    return fig


def graficar_estrategias(p, pareto, i_rod, archivo="dosis_por_zona.png"):
    elegidas = {"Costo mínimo": pareto[0], "Punto rodilla": pareto[i_rod],
                "Máxima limpieza": pareto[-1]}
    fig, axs = plt.subplots(1, 4, figsize=(15, 4))
    ancho = 0.25
    datos = [("Consorcio autóctono (L/m²)", lambda s: s["x"][:, 0]),
             ("Consorcio comercial (L/m²)", lambda s: s["x"][:, 1]),
             ("Nitrógeno (kg/m²)", lambda s: s["N"]),
             ("Cal agrícola (kg/m²)", lambda s: s["L"])]
    colores = ["#1565C0", "#EF6C00", "#6A1B9A"]
    for ax, (titulo, f) in zip(axs, datos):
        for e, (nombre, s) in enumerate(elegidas.items()):
            ax.bar(np.arange(p.n) + (e - 1) * ancho, f(s), ancho, label=nombre, color=colores[e])
        ax.set_xticks(range(p.n)); ax.set_xticklabels(p.nombres); ax.set_title(titulo, fontsize=10)
        ax.grid(axis="y", alpha=0.3)
    axs[0].legend(fontsize=8)
    fig.suptitle("Dosis óptimas por zona en tres estrategias del frente de Pareto")
    fig.tight_layout(); fig.savefig(archivo, dpi=200)
    return fig


# =============================================================================
# PROGRAMA PRINCIPAL
# =============================================================================
if __name__ == "__main__":
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", None)
    esc = escenario_base()
    P = Parametros(esc)

    print("=" * 70)
    print("DIAGNÓSTICO DEL SITIO (sin intervención)")
    print("=" * 70)
    diag = pd.DataFrame({
        "suelo": esc.zonas["suelo"],
        "k_nat (1/día)": P.k_nat.round(5),
        "C_final nat. (mg/kg)": concentracion_final(P, P.k_nat).round(0),
        "C_lim (mg/kg)": P.Clim,
        "Fracción recalcitrante (mg/kg)": (P.phi * P.C0).round(0),
        "¿Debe intervenirse?": np.where(P.obligatorias, "Sí", "No")})
    print(diag, "\n")
    if np.any(P.phi * P.C0 > P.Clim):
        print("ADVERTENCIA: en alguna zona la fracción recalcitrante supera el límite;"
              " la biorremediación sola no alcanza a cumplir la norma.\n")

    print("=" * 70)
    print("MÉTODO ε-CONSTRAINT")
    print("=" * 70)
    frente = frente_pareto(P, G=15, progreso=lambda i, total, texto: print(f"  [{i:2d}/{total}] {texto}"))
    print(frente["mensaje"])
    if frente["estado"] != "ok":
        sys.exit(1)
    pareto, i_rod = frente["soluciones"], frente["i_rodilla"]

    print("\n" + "=" * 70)
    print("SOLUCIONES NO DOMINADAS (FRENTE DE PARETO)")
    print("=" * 70)
    df = tabla_resultados(P, pareto)
    print(df.to_string(index=False))
    df.to_csv("resultados_pareto.csv", index=False)

    print("\nDosis del punto rodilla (mejor relación limpieza/costo):")
    s = pareto[i_rod]
    print(pd.DataFrame({"Interviene": s["y"], "Autóctono (L/m²)": s["x"][:, 0].round(2),
                        "Comercial (L/m²)": s["x"][:, 1].round(2), "N (kg/m²)": s["N"].round(3),
                        "P (kg/m²)": (s["N"] / 10).round(4), "Cal (kg/m²)": s["L"].round(2)},
                       index=P.nombres))

    # Frente del caso base precalculado para que la app lo cargue al instante
    ruta_base = os.path.join(RAIZ, "datos", "frente_base.json")
    os.makedirs(os.path.dirname(ruta_base), exist_ok=True)
    with open(ruta_base, "w", encoding="utf-8") as fh:
        json.dump({"clave": esc.clave(), "G": 15, "frente": frente_a_json(frente)}, fh, ensure_ascii=False)

    graficar_pareto(P, pareto, i_rod)
    graficar_estrategias(P, pareto, i_rod)
    print("\nArchivos generados: frente_pareto.png, dosis_por_zona.png, resultados_pareto.csv,"
          " ../datos/frente_base.json")
    if os.environ.get("MPLBACKEND", "").lower() != "agg":
        plt.show()
