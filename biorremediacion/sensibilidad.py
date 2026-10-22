"""
Análisis de sensibilidad de un factor a la vez sobre los supuestos del modelo.

Para no recalcular el frente completo, en cada variante se resuelven solo los dos
extremos: el costo mínimo para cumplir la norma y la máxima limpieza posible.
"""

import pandas as pd

from .modelo import Parametros
from .solver import resolver

# clave -> (etiqueta para el usuario, cómo aplicar el factor al escenario)
PARAMETROS_SENSIBILIDAD = {
    "k_max": "Velocidad máxima de degradación (K_MAX)",
    "k_m": "Biomasa de media saturación (K_M)",
    "k_s": "Nutriente de media saturación (K_S)",
    "sigma": "Supervivencia del inóculo (σ)",
}


def variar(esc, parametro, factor):
    """Escenario con `parametro` multiplicado por `factor`."""
    if parametro == "sigma":
        # σ es una fracción: se escala toda la tabla y se limita a 1
        return esc.copia(supervivencia=(esc.supervivencia * factor).clip(upper=1.0))
    return esc.copia(**{parametro: getattr(esc, parametro) * factor})


def extremos(esc):
    """(costo mínimo en M COP, máxima limpieza en %) o None si es infactible."""
    p = Parametros(esc)
    sol_min = resolver(p, "min_f2")
    if sol_min is None:
        return None
    sol_max = resolver(p, "max_f1")
    return sol_min["f2"], 100 * sol_max["f1"]


def analizar(esc, parametros, delta, progreso=None):
    """
    Varía cada parámetro en ±delta (fracción, p. ej. 0.2) manteniendo los demás fijos.

    Devuelve un DataFrame con una fila por variante (más el caso base, variacion = 0):
    parametro, etiqueta, variacion, costo_min, limpieza_max, estado.
    """
    variantes = [("base", 0.0)] + [(par, s * delta) for par in parametros for s in (-1, 1)]
    filas = []
    for q, (par, v) in enumerate(variantes, start=1):
        e = esc if par == "base" else variar(esc, par, 1 + v)
        r = extremos(e)
        filas.append({"parametro": par,
                      "etiqueta": PARAMETROS_SENSIBILIDAD.get(par, "Caso base"),
                      "variacion": v,
                      "costo_min": r[0] if r else float("nan"),
                      "limpieza_max": r[1] if r else float("nan"),
                      "estado": "ok" if r else "infactible"})
        if progreso:
            progreso(q, len(variantes), f"{filas[-1]['etiqueta']} {v:+.0%}")
    return pd.DataFrame(filas)
