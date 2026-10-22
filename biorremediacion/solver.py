"""
Solución del MINLP biobjetivo: enumeración de y, SLSQP para el problema continuo
y método ε-constraint para el frente de Pareto.

SLSQP es local: no garantiza el óptimo global.
"""

import itertools

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .modelo import concentracion_final, diagnostico, f1_limpieza, f2_costo, velocidad_k


def desempacar(p, z, S):
    """Convierte el vector de SciPy en las matrices x, N, L de todo el sitio."""
    x, N, L = np.zeros((p.n, p.m)), np.zeros(p.n), np.zeros(p.n)
    zz = z.reshape(len(S), p.m + 2)
    x[S], N[S], L[S] = zz[:, :p.m], zz[:, p.m], zz[:, p.m + 1]
    return x, N, L


# =============================================================================
# Subproblema con y fijo
# =============================================================================
def resolver_subproblema(p, y, objetivo, eps=None, f1_min=None, n_inicios=3, semilla=0):
    """
    Con y fijo, resuelve el problema continuo en x, N, L con SLSQP.
      objetivo = "max_f1"  -> máx f1  s.a. f2 <= eps (si eps no es None)
      objetivo = "min_f2"  -> mín f2  s.a. f1 >= f1_min (si f1_min no es None)
    Siempre se exige cumplir la norma y la disponibilidad de consorcios.
    Usa varios puntos iniciales (multi-arranque) para evitar óptimos locales.
    Devuelve (f1, f2, x, N, L) o None si no encuentra una solución factible.
    """
    S = np.where(y == 1)[0]
    if len(S) == 0:                      # nada que decidir: solo degradación natural
        x, N, L = np.zeros((p.n, p.m)), np.zeros(p.n), np.zeros(p.n)
        k = velocidad_k(p, y, x, N, L)
        ok = np.all(concentracion_final(p, k) <= p.Clim + 1e-6)
        return (f1_limpieza(p, k), 0.0, x, N, L) if ok else None

    ub = np.column_stack([np.full((len(S), p.m), p.esc.x_max), p.Ncap[S], p.Lcap[S]]).ravel()
    limites = [(0, u) for u in ub]

    cache = {}                           # guarda cálculos para no repetirlos
    def evaluar(z):
        clave = z.tobytes()
        if clave not in cache:
            x, N, L = desempacar(p, z, S)
            k = velocidad_k(p, y, x, N, L)
            cache[clave] = (k, f1_limpieza(p, k), f2_costo(p, y, x, N, L), x)
        return cache[clave]

    restricciones = [
        # Norma: C_final <= C_lim en las zonas intervenidas (escalado)
        {"type": "ineq", "fun": lambda z: (p.Clim[S] - concentracion_final(p, evaluar(z)[0])[S]) / p.Clim[S]},
        # Disponibilidad de consorcios: sum_i A_i x_ij <= Q_j
        {"type": "ineq", "fun": lambda z: (p.Q - p.A @ desempacar(p, z, S)[0]) / p.Q},
    ]
    if eps is not None:
        restricciones.append({"type": "ineq", "fun": lambda z: (eps - evaluar(z)[2]) / max(eps, 1)})
    if f1_min is not None:
        restricciones.append({"type": "ineq", "fun": lambda z: evaluar(z)[1] - f1_min})

    if objetivo == "max_f1":
        fobj = lambda z: -evaluar(z)[1]
    else:
        fobj = lambda z: evaluar(z)[2] / 100

    # Puntos iniciales: medio, solo bioestimulación, todo al máximo (+ aleatorios opcionales)
    rng = np.random.default_rng(semilla)
    inicios = [0.5 * ub,
               np.column_stack([np.zeros((len(S), p.m)), p.Ncap[S], p.Lcap[S]]).ravel(),
               ub.copy()]
    inicios += [rng.uniform(0, 1, len(ub)) * ub for _ in range(max(0, n_inicios - 3))]

    mejor = None
    for z0 in inicios:
        res = minimize(fobj, z0, method="SLSQP", bounds=limites,
                       constraints=restricciones, options={"maxiter": 300, "ftol": 1e-9})
        z = np.clip(res.x, 0, ub)
        factible = all(np.all(r["fun"](z) >= -1e-5) for r in restricciones)
        if factible and (mejor is None or fobj(z) < fobj(mejor)):
            mejor = z
    if mejor is None:
        return None
    k, f1, f2, x = evaluar(mejor)
    _, N, L = desempacar(p, mejor, S)
    return f1, f2, x, N, L


# =============================================================================
# Problema completo: enumeración de zonas intervenidas
# =============================================================================
def combinaciones_y(p):
    """Genera todos los vectores y posibles (las obligatorias siempre en 1)."""
    for bits in itertools.product([0, 1], repeat=len(p.libres)):
        y = p.obligatorias.astype(int).copy()
        y[p.libres] = bits
        yield y


def resolver(p, objetivo, eps=None, f1_min=None):
    """Prueba todas las combinaciones de y y devuelve la mejor solución (o None)."""
    mejor = None
    for y in combinaciones_y(p):
        if eps is not None and np.sum(p.c_fijo * y) / 1e6 > eps:
            continue                         # ni siquiera alcanza para los costos fijos
        sol = resolver_subproblema(p, y, objetivo, eps, f1_min)
        if sol is None:
            continue
        f1, f2 = sol[0], sol[1]
        mejora = (mejor is None or
                  (objetivo == "max_f1" and (f1 > mejor["f1"] + 1e-6 or
                                             (abs(f1 - mejor["f1"]) <= 1e-6 and f2 < mejor["f2"]))) or
                  (objetivo == "min_f2" and f2 < mejor["f2"]))
        if mejora:
            mejor = {"f1": f1, "f2": f2, "y": y, "x": sol[2], "N": sol[3], "L": sol[4]}
    return mejor


# =============================================================================
# Método ε-constraint
# =============================================================================
def frente_pareto(p, G=15, progreso=None):
    """
    Genera el frente de Pareto con una rejilla de G intervalos de presupuesto.

    `progreso(i, total, texto)` se llama después de cada paso (opcional).
    Devuelve un dict con:
      estado      "ok" o "infactible"
      mensaje     explicación para el usuario
      soluciones  lista de dicts {f1, f2, y, x, N, L} ordenada por costo
      i_rodilla   índice del punto rodilla (None si es infactible)
    """
    G = max(1, int(G))
    total = G + 2
    avisar = progreso or (lambda i, total, texto: None)

    # Paso 1: extremos del rango de presupuesto
    sol_min = resolver(p, "min_f2")                      # costo mínimo que cumple la norma
    avisar(1, total, "Costo mínimo que cumple la norma")
    if sol_min is None:
        _, avisos = diagnostico(p)
        motivo = (" ".join(avisos) if avisos else
                  "Las zonas cumplen por separado, pero no hay suficiente consorcio disponible "
                  "(litros) o la combinación de restricciones no deja ningún plan que cumpla la norma.")
        return {"estado": "infactible", "soluciones": [], "i_rodilla": None,
                "mensaje": "Con estos datos no existe ningún plan que cumpla la norma. " + motivo}

    sol_max = resolver(p, "max_f1")                      # máxima limpieza posible
    sol_max = resolver(p, "min_f2", f1_min=sol_max["f1"] - 1e-4) or sol_max  # la más barata con esa limpieza
    avisar(2, total, "Máxima limpieza posible")
    eps_min, eps_max = sol_min["f2"], sol_max["f2"]

    # Pasos 2 y 3: rejilla de presupuestos y resolución de P(ε)
    soluciones = [sol_min]
    if eps_max - eps_min > 1e-6:
        for q, eps in enumerate(np.linspace(eps_min, eps_max, G + 1)[1:-1], start=1):
            sol = resolver(p, "max_f1", eps=eps)
            texto = f"Presupuesto {q} de {G - 1}: {eps:.2f} M COP"
            if sol is not None:
                soluciones.append(sol)
                texto += f" -> limpieza {100 * sol['f1']:.1f} %, costo {sol['f2']:.2f}"
            avisar(2 + q, total, texto)
    soluciones.append(sol_max)
    avisar(total, total, "Listo")

    # Paso 4: filtrar soluciones dominadas o repetidas
    pareto = []
    for a in soluciones:
        dominada = any((b["f1"] >= a["f1"] - 1e-6 and b["f2"] <= a["f2"] + 1e-6) and
                       (b["f1"] > a["f1"] + 1e-6 or b["f2"] < a["f2"] - 1e-6) for b in soluciones)
        repetida = any(abs(a["f1"] - b["f1"]) < 1e-6 and abs(a["f2"] - b["f2"]) < 1e-6 for b in pareto)
        if not dominada and not repetida:
            pareto.append(a)
    pareto = sorted(pareto, key=lambda s: s["f2"])
    return {"estado": "ok", "soluciones": pareto, "i_rodilla": punto_rodilla(pareto),
            "mensaje": f"Rango de presupuesto: {eps_min:.2f} a {eps_max:.2f} millones COP"}


def tabla_resultados(p, pareto):
    filas = []
    for q, s in enumerate(pareto):
        filas.append({"Punto": q, "Costo (M COP)": round(s["f2"], 2),
                      "Limpieza (%)": round(100 * s["f1"], 2),
                      "Zonas intervenidas": ", ".join(np.array(p.nombres)[np.asarray(s["y"]) == 1])})
    df = pd.DataFrame(filas)
    # Paso 5: ganancia marginal = puntos de % de limpieza por cada millón adicional
    df["Ganancia (%/M COP)"] = (df["Limpieza (%)"].diff() / df["Costo (M COP)"].diff()).round(3)
    return df


def punto_rodilla(pareto):
    """Punto más alejado de la recta entre los extremos (frente normalizado)."""
    f1 = np.array([s["f1"] for s in pareto]); f2 = np.array([s["f2"] for s in pareto])
    a = (f2 - f2.min()) / (np.ptp(f2) + 1e-12); b = (f1 - f1.min()) / (np.ptp(f1) + 1e-12)
    return int(np.argmax(b - a))


# =============================================================================
# Serialización (JSON) de un frente
# =============================================================================
def frente_a_json(frente):
    def conv(s):
        return {k: (np.asarray(v).tolist() if k in ("y", "x", "N", "L") else float(v))
                for k, v in s.items()}
    return {**frente, "soluciones": [conv(s) for s in frente["soluciones"]]}


def frente_desde_json(d):
    def conv(s):
        return {"f1": s["f1"], "f2": s["f2"], "y": np.array(s["y"], dtype=int),
                "x": np.array(s["x"], dtype=float), "N": np.array(s["N"], dtype=float),
                "L": np.array(s["L"], dtype=float)}
    return {**d, "soluciones": [conv(s) for s in d["soluciones"]]}

