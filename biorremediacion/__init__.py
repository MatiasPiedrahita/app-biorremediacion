"""Biorremediación de suelos con TPH: modelo biobjetivo y método ε-constraint."""

from .datos import Escenario, escenario_base
from .modelo import Parametros, detallar, diagnostico
from .solver import frente_pareto, punto_rodilla, resolver, tabla_resultados
