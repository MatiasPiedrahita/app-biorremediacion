"""Estado compartido, caché de cálculos y utilidades de formato para las páginas."""

import json
import os

import streamlit as st

from biorremediacion import Parametros, escenario_base, frente_pareto
from biorremediacion.datos import Escenario
from biorremediacion.modelo import miles  # noqa: F401  (se reexporta para las páginas)
from biorremediacion.sensibilidad import analizar
from biorremediacion.solver import frente_desde_json

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_ZONAS = 8
MAX_GUARDADOS_CACHE = 40


# =============================================================================
# Escenario actual
# =============================================================================
def escenario() -> Escenario:
    if "escenario" not in st.session_state:
        st.session_state.escenario = escenario_base()
    return st.session_state.escenario


def fijar_escenario(esc: Escenario, reiniciar_controles=False):
    """Cambia el escenario actual. Con `reiniciar_controles`, los campos de la página
    Sitio se vuelven a llenar con los valores del nuevo escenario."""
    st.session_state.escenario = esc
    if reiniciar_controles:
        for k in [k for k in st.session_state if str(k).startswith("w_")]:
            del st.session_state[k]
        st.session_state.version_editores = st.session_state.get("version_editores", 0) + 1


def es_caso_base(esc=None):
    return (esc or escenario()).clave() == escenario_base().clave()


@st.cache_data(show_spinner=False)
def parametros_de(clave: str) -> Parametros:
    return Parametros(Escenario.from_dict(json.loads(clave)))


def parametros(esc=None) -> Parametros:
    return parametros_de((esc or escenario()).clave())


# =============================================================================
# Caché de frentes y sensibilidad (compartida entre sesiones del mismo servidor)
# =============================================================================
@st.cache_resource
def _almacen():
    return {"frentes": {}, "sensibilidad": {}}


@st.cache_data(show_spinner=False)
def _frente_base_archivo():
    ruta = os.path.join(RAIZ, "datos", "frente_base.json")
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def _guardar(tabla, clave, valor):
    if len(tabla) >= MAX_GUARDADOS_CACHE:
        tabla.pop(next(iter(tabla)))
    tabla[clave] = valor


def frente_disponible(esc, G):
    """Frente ya calculado para (escenario, G), o None."""
    clave = (esc.clave(), int(G))
    almacen = _almacen()["frentes"]
    if clave in almacen:
        return almacen[clave]
    base = _frente_base_archivo()
    if base and base["clave"] == clave[0] and base["G"] == clave[1]:
        frente = frente_desde_json(base["frente"])
        _guardar(almacen, clave, frente)
        return frente
    return None


def calcular_frente(esc, G):
    """Calcula el frente mostrando una barra de progreso."""
    barra = st.progress(0.0, text="Preparando el cálculo…")

    def progreso(i, total, texto):
        barra.progress(min(i / total, 1.0), text=f"Paso {i} de {total} · {texto}")

    frente = frente_pareto(parametros(esc), G=G, progreso=progreso)
    barra.empty()
    _guardar(_almacen()["frentes"], (esc.clave(), int(G)), frente)
    return frente


def sensibilidad_disponible(esc, params, delta):
    return _almacen()["sensibilidad"].get((esc.clave(), tuple(params), delta))


def calcular_sensibilidad(esc, params, delta):
    barra = st.progress(0.0, text="Preparando el análisis…")

    def progreso(i, total, texto):
        barra.progress(i / total, text=f"Variante {i} de {total} · {texto}")

    df = analizar(esc, list(params), delta, progreso=progreso)
    barra.empty()
    _guardar(_almacen()["sensibilidad"], (esc.clave(), tuple(params), delta), df)
    return df


# =============================================================================
# Escenarios guardados para comparar
# =============================================================================
def guardados() -> dict:
    if "guardados" not in st.session_state:
        st.session_state.guardados = {}
    return st.session_state.guardados


# =============================================================================
# Formato
# =============================================================================
def mcop(v, dec=1):
    return f"{miles(v, dec)} M COP"


def pct(v, dec=1):
    """`v` como fracción (0 a 1)."""
    return f"{100 * v:.{dec}f} %"


def resumen_lateral():
    """Recuadro de la barra lateral con el escenario en uso."""
    esc = escenario()
    with st.sidebar:
        st.markdown("**Escenario en uso**")
        st.caption(f"{len(esc.zonas)} zonas · T = {esc.t_trat:g} días · {esc.temp:g} °C · "
                   f"límite {miles(esc.c_lim_general)} / {miles(esc.c_lim_sensible)} mg/kg")
        if es_caso_base(esc):
            st.caption("✅ Caso base de la Entrega 2")
        else:
            st.caption("✏️ Modificado respecto al caso base")
