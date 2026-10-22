"""Guarda el detalle de cada solución del frente base (dosis, k, C final y costos) en JSON."""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from biorremediacion import Parametros, detallar, escenario_base, frente_pareto  # noqa: E402
from biorremediacion.modelo import concentracion_final  # noqa: E402

P = Parametros(escenario_base())
frente = frente_pareto(P, G=15)
pareto, i_rod = frente["soluciones"], frente["i_rodilla"]
out = []
for s in pareto:
    d = detallar(P, s)
    out.append({"f1": float(s["f1"]), "f2": float(s["f2"]), "y": s["y"].tolist(), "x": s["x"].tolist(),
                "N": s["N"].tolist(), "L": s["L"].tolist(), "k": d["k"].tolist(),
                "C_final": d["C_final"].tolist(), "costos": d["costos"]})
json.dump({"i_rodilla": i_rod, "zonas": P.nombres, "C0": P.C0.tolist(), "Clim": P.Clim.tolist(),
           "k_nat": P.k_nat.tolist(), "Cnat": concentracion_final(P, P.k_nat).tolist(), "soluciones": out},
          open("resultados_detalle.json", "w"), indent=1)
for i in (0, i_rod, len(out) - 1):
    s = out[i]; print(i, round(s["f1"]*100,1), round(s["f2"],1), {k: round(v,1) for k,v in s["costos"].items()})
    print("   x", np.round(s["x"],2).tolist()); print("   N", np.round(s["N"],3).tolist(), "L", np.round(s["L"],2).tolist())
    print("   Cfin", np.round(s["C_final"]).tolist())
