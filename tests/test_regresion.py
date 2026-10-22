"""Pruebas de regresión contra los valores de referencia de CLAUDE.md (caso base)."""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from biorremediacion import Parametros, detallar, diagnostico, escenario_base, frente_pareto  # noqa: E402
from biorremediacion.datos import Escenario  # noqa: E402
from biorremediacion.modelo import dosis_maxima, velocidad_k  # noqa: E402
from biorremediacion.sensibilidad import analizar  # noqa: E402


@pytest.fixture(scope="module")
def base():
    p = Parametros(escenario_base())
    return p, frente_pareto(p, G=15)


def test_k_natural_y_maximo():
    p = Parametros(escenario_base())
    assert p.k_nat.min() == pytest.approx(0.0006, abs=5e-5)
    assert p.k_nat.max() == pytest.approx(0.0042, abs=5e-5)
    y, x, N, _ = dosis_maxima(p)
    k = velocidad_k(p, y, x, N, p.Lcap)          # "máximo de insumos" como en CLAUDE.md
    assert k.min() == pytest.approx(0.025, abs=1e-3)
    assert k.max() == pytest.approx(0.048, abs=1e-3)
    assert list(np.array(p.nombres)[p.obligatorias]) == ["Z1", "Z2", "Z3", "Z4"]


def test_frente_base(base):
    p, frente = base
    assert frente["estado"] == "ok"
    sol = frente["soluciones"]
    assert len(sol) == 16
    referencia = [(0, 91.35, 0.520, [1, 1, 1, 1, 0, 0]),
                  (frente["i_rodilla"], 129.50, 0.729, [1] * 6),
                  (-1, 282.11, 0.790, [1] * 6)]
    for i, f2, f1, y in referencia:
        assert sol[i]["f2"] == pytest.approx(f2, abs=1.0)
        assert sol[i]["f1"] == pytest.approx(f1, abs=0.005)
        assert list(sol[i]["y"]) == y


def test_rodilla_r1_activa_y_costos(base):
    p, frente = base
    rod = detallar(p, frente["soluciones"][frente["i_rodilla"]])
    assert rod["C_final"][0] == pytest.approx(p.Clim[0], rel=1e-3)   # Z1 en su límite
    assert rod["C_final"][1] == pytest.approx(p.Clim[1], rel=1e-3)   # Z2 en su límite
    assert rod["costos"]["fijo"] / rod["f2"] == pytest.approx(0.66, abs=0.01)
    extra = frente["soluciones"][-1]["f2"] - rod["f2"]
    assert extra == pytest.approx(153, abs=1.5)


def test_escenario_ida_y_vuelta():
    esc = escenario_base()
    otro = Escenario.from_dict(esc.to_dict())
    assert otro.clave() == esc.clave()
    cambiado = esc.copia(t_trat=60)
    assert cambiado.t_trat == 60 and esc.t_trat == 90
    cambiado.zonas.loc["Z1", "A"] = 1
    assert esc.zonas.loc["Z1", "A"] == 600


def test_escenario_infactible_no_falla():
    # Límite menor que la fracción recalcitrante de Z1 (0.18 · 30 000 = 5 400 mg/kg)
    p = Parametros(escenario_base().copia(c_lim_general=1000))
    _, avisos = diagnostico(p)
    assert any(a.startswith("Z1") for a in avisos)
    frente = frente_pareto(p, G=3)
    assert frente["estado"] == "infactible"
    assert frente["soluciones"] == [] and "Z1" in frente["mensaje"]


def test_sensibilidad_base_coincide():
    df = analizar(escenario_base(), ["k_max"], 0.2)
    fila_base = df[df["variacion"] == 0].iloc[0]
    assert fila_base["costo_min"] == pytest.approx(91.35, abs=1.0)
    assert fila_base["limpieza_max"] == pytest.approx(79.0, abs=0.5)
    # Más velocidad de degradación -> cumplir la norma cuesta menos
    sube = df[(df["parametro"] == "k_max") & (df["variacion"] > 0)].iloc[0]
    assert sube["costo_min"] < fila_base["costo_min"]
