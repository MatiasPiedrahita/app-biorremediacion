"""
Datos del caso de estudio como un objeto de configuración (Escenario).

Los valores por defecto son los del caso base de la Entrega 2. Cada dato lleva su
fuente en un comentario; los que no tienen fuente directa se marcan como supuesto.
El sitio y sus 6 zonas son un caso de estudio ILUSTRATIVO.
"""

import copy
import dataclasses
import json
from dataclasses import dataclass, field

import pandas as pd


def _suelos():
    # phi     : fracción recalcitrante (no biodisponible, queda adsorbida)
    # fO_nat  : factor de oxígeno sin labranza                       (supuesto)
    # fO_lab  : factor de oxígeno con labranza periódica             (supuesto)
    # b_cal   : kg de cal por m² para subir 1 unidad de pH en 30 cm
    #           [Vossen (UC): 0.6 / 1.7 / 2.3 t/acre por unidad de pH en 18 cm, escalado a 30 cm]
    return pd.DataFrame(
        {"phi":    [0.05, 0.10, 0.18],
         "fO_nat": [0.85, 0.65, 0.40],
         "fO_lab": [1.00, 0.90, 0.75],
         "b_cal":  [0.23, 0.64, 0.87]},
        index=["arenoso", "franco", "arcilloso"])


def _zonas():
    # A: área (m²)  C0: TPH inicial (mg/kg)  H: humedad (% cap. campo)  pH0: pH inicial
    # B: degradadores nativos (millones UFC/g)  N0: N disponible en el suelo (kg/m²)
    # sensible: 1 si está cerca de una fuente hídrica (ronda de quebrada)
    return pd.DataFrame(
        {"A":        [600,   450,    800,   350,   500,   700],
         "C0":       [30000, 20000,  14000, 12000, 8000,  6000],
         "suelo":    ["arcilloso", "franco", "franco", "arenoso", "arenoso", "arcilloso"],
         "H":        [70,    60,     55,    40,    45,    75],
         "pH0":      [5.5,   5.5,    6.0,   6.5,   6.8,   5.2],
         "B":        [0.80,  0.80,   0.8,   0.5,   1.0,   2.0],
         "N0":       [0.040, 0.030,  0.025, 0.015, 0.015, 0.025],
         "sensible": [0,     1,      0,     1,     0,     0]},
        index=["Z1", "Z2", "Z3", "Z4", "Z5", "Z6"])


def _consorcios():
    return pd.DataFrame(
        {"costo": [30000, 45000],       # COP por litro (supuesto: no hay precio público; cotizar)
         "conc":  [5e8,   1e9],         # UFC/mL  [Biodyne 101 (Colombia): 1e8-1e9 UFC/mL]
         "Q":     [1500,  3000]},       # litros disponibles
        index=["Autóctono", "Comercial"])


def _supervivencia():
    # Supervivencia del inóculo según el tipo de suelo (sigma_{j,s})   (supuesto)
    return pd.DataFrame(
        {"arenoso": [0.60, 0.35], "franco": [0.60, 0.25], "arcilloso": [0.60, 0.12]},
        index=["Autóctono", "Comercial"])


TABLAS = ("suelos", "zonas", "consorcios", "supervivencia")


def _normal(v):
    """Números como float (90 y 90.0 deben dar la misma clave); texto tal cual."""
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    return v


@dataclass
class Escenario:
    # ---- Entorno y tratamiento ------------------------------------------------
    t_trat: float = 90          # tiempo de tratamiento (días)  [Ecopetrol: ~90 d con biodegradación estimulada]
    temp: float = 27.7          # temperatura media (°C)        [IDEAM 1981-2010, Barrancabermeja]
    t_ref: float = 30.0         # temperatura óptima (°C)       [EPA: óptimo 10-45 °C; mesófilos 25-45 °C]
    theta: float = 1.11         # coef. de corrección por temp. [Man (1998): 1.11-1.19 en arcilla con diésel]
    rho: float = 1400           # densidad aparente del suelo (kg/m³)
    prof: float = 0.30          # profundidad tratada (m)       [EPA: landfarms de 30-45 cm]

    # ---- Cinética ---------------------------------------------------------------
    k_max: float = 0.22         # velocidad máxima en condiciones ideales (1/día), calibrada
    k_m: float = 2.0            # biomasa a la mitad del efecto (millones UFC/g)       (supuesto)
    k_s: float = 0.3            # nutriente relativo a la mitad del efecto             (supuesto)
    b_comp: float = 1.0         # población nativa a la que el inóculo sobrevive la mitad (supuesto)
    k_i: float = 40000          # inhibición por toxicidad (mg/kg)  [EPA: >10 000 diluir; >50 000 inhibitorio]
    h_opt: float = 60           # humedad óptima (% cap. campo)     [EPA: 40-85 %]
    sig_h: float = 25           # tolerancia de humedad
    ph_opt: float = 7.0         # pH óptimo                         [EPA: 6-8, óptimo 7]
    sig_ph: float = 2.0         # tolerancia de pH
    ph_max: float = 7.5         # pH máximo permitido al encalar
    frac_c: float = 0.85        # fracción de carbono en los hidrocarburos
    relacion_cn: float = 10 / 100   # C:N:P = 100:10:1  [EPA: 100:10:1 a 100:1:0.5]

    # ---- Norma ------------------------------------------------------------------
    # Colombia no tiene norma nacional; Ecopetrol usa Louisiana 29B: TPH < 1 % (10 000 mg/kg)
    c_lim_general: float = 10000    # límite general (mg/kg)
    c_lim_sensible: float = 5000    # cerca de agua [NOM-138 México, fracción media, uso industrial]
    r_n_general: float = 1.0        # N total permitido = requerimiento 100:10:1 (extremo alto EPA)
    r_n_sensible: float = 0.5       # cerca de agua: equivale a 100:5:0.5 (dentro del rango EPA)

    # ---- Consorcios y costos (COP, 2026) ---------------------------------------
    x_max: float = 3.0          # dosis máxima por consorcio (L/m²) -> ~1e6-1e7 UFC/g de suelo
    c_n: float = 8700           # COP por kg de N  [SIPSA-DANE jun-2026: urea 46 %, ~$200 000/bulto 50 kg]
    c_p: float = 25000          # COP por kg de P  [DAP 18-46-0: $251 800/bulto 50 kg, Tierragro]
    c_cal: float = 300          # COP por kg de cal [cal dolomita: $14 200/bulto 50 kg, Croper]
    c_mov: float = 4_000_000    # COP por zona intervenida (movilización de maquinaria, montaje)
    c_lab: float = 18000        # COP por m² (labranza, riego, muestreo y análisis de TPH durante T)

    # ---- Tablas -----------------------------------------------------------------
    suelos: pd.DataFrame = field(default_factory=_suelos)
    zonas: pd.DataFrame = field(default_factory=_zonas)
    consorcios: pd.DataFrame = field(default_factory=_consorcios)
    supervivencia: pd.DataFrame = field(default_factory=_supervivencia)

    @property
    def masa_suelo(self):
        """kg de suelo por m²."""
        return self.rho * self.prof

    def copia(self, **cambios):
        """Copia independiente (tablas incluidas) con los cambios indicados."""
        nuevo = dataclasses.replace(self, **{t: getattr(self, t).copy() for t in TABLAS})
        for clave, valor in cambios.items():
            setattr(nuevo, clave, copy.deepcopy(valor))
        return nuevo

    def to_dict(self):
        d = {f.name: _normal(getattr(self, f.name)) for f in dataclasses.fields(self) if f.name not in TABLAS}
        for t in TABLAS:
            df = getattr(self, t)
            d[t] = {"index": [str(i) for i in df.index], "columns": list(df.columns),
                    "data": [[_normal(v) for v in fila] for fila in df.itertuples(index=False)]}
        return d

    @classmethod
    def from_dict(cls, d):
        escalares = {f.name for f in dataclasses.fields(cls)} - set(TABLAS)
        kw = {k: v for k, v in d.items() if k in escalares}
        for t in TABLAS:
            if t in d:
                kw[t] = pd.DataFrame(d[t]["data"], index=d[t]["index"], columns=d[t]["columns"])
        return cls(**kw)

    def clave(self):
        """Texto JSON estable: sirve para guardar el escenario y como clave de caché."""
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)


def escenario_base():
    return Escenario()


# Etiquetas para la interfaz: campo -> (nombre, unidad, fuente). "supuesto" = sin fuente directa.
ETIQUETAS = {
    "t_trat": ("Tiempo de tratamiento", "días", "Ecopetrol"),
    "temp": ("Temperatura media del sitio", "°C", "IDEAM, Barrancabermeja"),
    "t_ref": ("Temperatura óptima", "°C", "EPA"),
    "theta": ("Coeficiente de temperatura θ", "", "Man (1998)"),
    "rho": ("Densidad aparente del suelo", "kg/m³", ""),
    "prof": ("Profundidad tratada", "m", "EPA"),
    "k_max": ("Velocidad máxima de degradación K_MAX", "1/día", "calibrado"),
    "k_m": ("Biomasa de media saturación K_M", "millones UFC/g", "supuesto"),
    "k_s": ("Nutriente de media saturación K_S", "", "supuesto"),
    "b_comp": ("Competencia con nativos B_c", "millones UFC/g", "supuesto"),
    "k_i": ("Constante de toxicidad K_I", "mg/kg", "EPA"),
    "h_opt": ("Humedad óptima", "% cap. campo", "EPA"),
    "sig_h": ("Tolerancia de humedad", "% cap. campo", "EPA"),
    "ph_opt": ("pH óptimo", "", "EPA"),
    "sig_ph": ("Tolerancia de pH", "", "EPA"),
    "ph_max": ("pH máximo al encalar", "", ""),
    "frac_c": ("Fracción de carbono del crudo", "", ""),
    "relacion_cn": ("Relación N:C", "", "EPA"),
    "c_lim_general": ("Límite legal general", "mg/kg", "Louisiana 29-B (Ecopetrol)"),
    "c_lim_sensible": ("Límite legal cerca de agua", "mg/kg", "NOM-138 México"),
    "r_n_general": ("Tope de N (fracción del requerido), general", "", "EPA"),
    "r_n_sensible": ("Tope de N (fracción del requerido), cerca de agua", "", "EPA"),
    "x_max": ("Dosis máxima por consorcio", "L/m²", ""),
    "c_n": ("Precio del nitrógeno", "COP/kg N", "SIPSA-DANE 2026"),
    "c_p": ("Precio del fósforo", "COP/kg P", "Tierragro 2026"),
    "c_cal": ("Precio de la cal", "COP/kg", "Croper 2026"),
    "c_mov": ("Movilización por zona intervenida", "COP/zona", ""),
    "c_lab": ("Labranza, riego y monitoreo", "COP/m²", ""),
}

COLUMNAS_ZONAS = {
    "A": "Área (m²)", "C0": "TPH inicial (mg/kg)", "suelo": "Tipo de suelo",
    "H": "Humedad (% cap. campo)", "pH0": "pH inicial", "B": "Microorganismos nativos (millones UFC/g)",
    "N0": "N disponible (kg/m²)", "sensible": "Cerca de agua",
}

NOMBRES_TABLAS = {"zonas": "Zonas", "suelos": "Tipos de suelo", "consorcios": "Consorcios",
                  "supervivencia": "Supervivencia del inóculo"}


def _fmt(v):
    if isinstance(v, float):
        return f"{v:,.6g}".replace(",", " ") if abs(v) < 1e6 else f"{v:,.0f}".replace(",", " ")
    return str(v)


def diferencias(a, b):
    """Lista de textos con lo que cambia del escenario `a` al `b`."""
    da, db = a.to_dict(), b.to_dict()
    out = []
    for campo, (nombre, unidad, _) in ETIQUETAS.items():
        if da[campo] != db[campo]:
            out.append(f"{nombre}: {_fmt(da[campo])} → {_fmt(db[campo])} {unidad}".rstrip())
    for t in TABLAS:
        ta, tb = da[t], db[t]
        if ta["index"] != tb["index"] or ta["columns"] != tb["columns"]:
            out.append(f"{NOMBRES_TABLAS[t]}: cambió la lista de filas "
                       f"({', '.join(ta['index'])} → {', '.join(tb['index'])})")
            continue
        for fila, va, vb in zip(ta["index"], ta["data"], tb["data"]):
            for col, x, y in zip(ta["columns"], va, vb):
                if x != y:
                    nom_col = COLUMNAS_ZONAS.get(col, col) if t == "zonas" else col
                    out.append(f"{NOMBRES_TABLAS[t]} · {fila} · {nom_col}: {_fmt(x)} → {_fmt(y)}")
    return out
