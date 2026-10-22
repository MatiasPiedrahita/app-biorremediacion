"""
Modelo: parámetros derivados, velocidad de degradación, objetivos y diagnóstico.

Todas las funciones reciben un objeto Parametros `p` construido a partir de un
Escenario, así que se pueden evaluar varios escenarios a la vez.
"""

import numpy as np
import pandas as pd

from .datos import Escenario


class Parametros:
    """Parámetros derivados de un escenario (se calculan una sola vez)."""

    def __init__(self, esc: Escenario):
        self.esc = esc
        z = esc.zonas
        s = esc.suelos.loc[z["suelo"]].reset_index(drop=True)
        self.nombres = list(z.index)
        self.consorcios = list(esc.consorcios.index)
        self.n, self.m = len(z), len(esc.consorcios)
        self.A, self.C0 = z["A"].values.astype(float), z["C0"].values.astype(float)
        self.B = z["B"].values.astype(float)
        self.N0 = z["N0"].values.astype(float)
        self.pH0 = z["pH0"].values.astype(float)
        self.phi, self.b = s["phi"].values.astype(float), s["b_cal"].values.astype(float)
        self.fO_nat, self.fO_lab = s["fO_nat"].values.astype(float), s["fO_lab"].values.astype(float)
        sensible = z["sensible"].values.astype(int) == 1

        # Factores ambientales que no dependen de las decisiones
        self.fT = min(1.0, esc.theta ** (esc.temp - esc.t_ref))
        self.fH = np.exp(-((z["H"].values.astype(float) - esc.h_opt) / esc.sig_h) ** 2)
        self.ftox = 1 / (1 + self.C0 / esc.k_i)

        # Nitrógeno requerido según C:N:P (kg N/m²)
        self.Nreq = esc.relacion_cn * esc.frac_c * self.C0 * 1e-6 * esc.masa_suelo
        r = np.where(sensible, esc.r_n_sensible, esc.r_n_general)
        self.Ncap = np.maximum(r * self.Nreq - self.N0, 0)          # dosis máx. de N
        self.Lcap = np.maximum((esc.ph_max - self.pH0) * self.b, 0) # dosis máx. de cal
        self.Clim = np.where(sensible, esc.c_lim_sensible, esc.c_lim_general).astype(float)

        # Aporte de cada consorcio a la biomasa (millones UFC/g por cada L/m²)
        self.aporte = esc.consorcios["conc"].values.astype(float) * 1000 / (esc.masa_suelo * 1000) / 1e6
        # Supervivencia efectiva: depende del suelo y de la competencia con nativos
        sig = esc.supervivencia[list(z["suelo"])].values.astype(float).T      # (n, m)
        self.s = sig / (1 + self.B / esc.b_comp)[:, None]

        self.c_x = esc.consorcios["costo"].values.astype(float)
        self.Q = esc.consorcios["Q"].values.astype(float)
        self.c_fijo = esc.c_mov + esc.c_lab * self.A
        self.w = self.A * self.C0 / np.sum(self.A * self.C0)          # peso de cada zona

        # Zonas que NO cumplen la norma solo con degradación natural -> deben intervenirse
        self.k_nat = velocidad_k(self, np.zeros(self.n), np.zeros((self.n, self.m)),
                                 np.zeros(self.n), np.zeros(self.n))
        self.obligatorias = concentracion_final(self, self.k_nat) > self.Clim
        self.libres = np.where(~self.obligatorias)[0]


# =============================================================================
# Velocidad de degradación, objetivos
# =============================================================================
def factores(p, y, x, N, L):
    """Cada factor de k (entre 0 y 1) por zona."""
    esc = p.esc
    M = p.B + (p.s * p.aporte * x).sum(axis=1)       # biomasa activa total
    S = (p.N0 + N) / p.Nreq                           # N disponible / N requerido
    pH = p.pH0 + L / p.b
    return {
        "f_bio": M / (esc.k_m + M),
        "f_nut": S / (esc.k_s + S),
        "f_T": np.full(p.n, p.fT),
        "f_H": p.fH,
        "f_pH": np.exp(-((pH - esc.ph_opt) / esc.sig_ph) ** 2),
        "f_O": p.fO_nat + (p.fO_lab - p.fO_nat) * y,  # la labranza mejora el oxígeno
        "f_tox": p.ftox,
    }


def velocidad_k(p, y, x, N, L):
    """k_i = k_max · f_bio · f_nut · f_T · f_H · f_pH · f_O · f_tox"""
    f = factores(p, y, x, N, L)
    return p.esc.k_max * f["f_bio"] * f["f_nut"] * p.fT * p.fH * f["f_pH"] * f["f_O"] * p.ftox


def concentracion_final(p, k):
    return p.C0 * (p.phi + (1 - p.phi) * np.exp(-k * p.esc.t_trat))


def remocion(p, k):
    """Fracción eliminada en cada zona, R_i."""
    return (1 - p.phi) * (1 - np.exp(-k * p.esc.t_trat))


def f1_limpieza(p, k):
    """Fracción del contaminante total del sitio eliminada (0 a 1)."""
    return np.sum(p.w * remocion(p, k))


def f2_costo(p, y, x, N, L):
    """Costo total en millones de COP."""
    esc = p.esc
    insumos = x @ p.c_x + esc.c_n * N + esc.c_p * N / 10 + esc.c_cal * L     # COP/m²
    return np.sum(p.c_fijo * y + p.A * insumos) / 1e6


def costos_por_componente(p, sol):
    """Costo de una solución separado en fijo, consorcio, nutrientes y cal (M COP)."""
    esc, y, x, N, L = p.esc, sol["y"], sol["x"], sol["N"], sol["L"]
    return {"fijo": float(np.sum(p.c_fijo * y) / 1e6),
            "consorcio": float(np.sum(p.A * (x @ p.c_x)) / 1e6),
            "nutrientes": float(np.sum(p.A * (esc.c_n * N + esc.c_p * N / 10)) / 1e6),
            "cal": float(np.sum(p.A * esc.c_cal * L) / 1e6)}


def detallar(p, sol):
    """Agrega k, concentración final y costos por componente a una solución."""
    k = velocidad_k(p, sol["y"], sol["x"], sol["N"], sol["L"])
    return {**sol, "k": k, "C_final": concentracion_final(p, k),
            "costos": costos_por_componente(p, sol)}


# =============================================================================
# Diagnóstico del sitio
# =============================================================================
def dosis_maxima(p):
    """Insumos que dan la k más alta posible en cada zona (ignora la disponibilidad Q).
    La cal se lleva hasta el pH óptimo, no más, porque pasarse reduce f_pH."""
    y = np.ones(p.n)
    x = np.full((p.n, p.m), p.esc.x_max)
    N = p.Ncap.copy()
    L = np.clip((p.esc.ph_opt - p.pH0) * p.b, 0, p.Lcap)
    return y, x, N, L


def diagnostico(p):
    """Tabla del sitio sin tratamiento y con el máximo de insumos, más avisos.

    Devuelve (tabla, avisos). `avisos` es una lista de textos para el usuario que
    explican por qué el escenario podría no tener solución.
    """
    k_pot = velocidad_k(p, *dosis_maxima(p))
    C_nat, C_pot = concentracion_final(p, p.k_nat), concentracion_final(p, k_pot)
    recal = p.phi * p.C0
    tabla = pd.DataFrame({
        "suelo": list(p.esc.zonas["suelo"]),
        "C0": p.C0,
        "k_nat": p.k_nat,
        "C_nat": C_nat,
        "k_pot": k_pot,
        "C_pot": C_pot,
        "Clim": p.Clim,
        "recalcitrante": recal,
        "obligatoria": p.obligatorias,
    }, index=p.nombres)

    avisos = []
    t = p.esc.t_trat
    for i, z in enumerate(p.nombres):
        if recal[i] > p.Clim[i]:
            avisos.append(f"{z}: la fracción que no se degrada ({miles(recal[i])} mg/kg) ya supera el "
                          f"límite ({miles(p.Clim[i])} mg/kg). La biorremediación sola nunca podrá "
                          "cumplir la norma en esta zona.")
        elif C_pot[i] > p.Clim[i]:
            avisos.append(f"{z}: ni con la dosis máxima de todos los insumos se llega al límite en "
                          f"{t:g} días (quedaría en {miles(C_pot[i])} mg/kg y el límite es "
                          f"{miles(p.Clim[i])} mg/kg). Pruebe con más tiempo de tratamiento.")
    return tabla, avisos


def miles(v, dec=0):
    """Número con punto decimal y espacio como separador de miles (estilo de la presentación)."""
    return f"{v:,.{dec}f}".replace(",", " ")
