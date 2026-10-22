import numpy as np
import streamlit as st

from biorremediacion import diagnostico
from biorremediacion.graficas import NOMBRES_FACTORES, fig_concentracion, fig_factores
from biorremediacion.modelo import factores
from paginas.comun import miles, parametros

p = parametros()
tabla, avisos = diagnostico(p)

st.title("🔎 Diagnóstico del sitio")
st.markdown(f"Qué pasaría en **{p.esc.t_trat:g} días** si no se hace nada (solo degradación natural), "
            "y qué tanto se podría lograr con la dosis máxima de insumos. Este cálculo es instantáneo.")

# ---- Avisos ------------------------------------------------------------------
if avisos:
    st.error("**Con estos datos no se puede cumplir la norma en todas las zonas.**")
    for a in avisos:
        st.markdown(f"- {a}")
    st.info("Opciones: alargar el tiempo de tratamiento, revisar el límite legal o considerar otra técnica "
            "(por ejemplo, excavación o lavado) para esas zonas.")
elif len(p.libres) > 4:
    st.warning(f"Hay {len(p.libres)} zonas opcionales: el cálculo del plan probará {2 ** len(p.libres)} "
               "combinaciones y puede tardar varios minutos.")

obligatorias = [z for z, o in zip(p.nombres, p.obligatorias) if o]
c1, c2, c3 = st.columns(3)
c1.metric("Zonas que hay que intervenir", f"{len(obligatorias)} de {p.n}",
          ", ".join(obligatorias) if obligatorias else "ninguna", delta_color="off")
c2.metric("Contaminante total en el sitio",
          f"{miles(np.sum(p.A * p.esc.masa_suelo * p.C0) / 1e9, 1)} t de TPH", delta_color="off",
          help="Suma de área × masa de suelo por m² × TPH inicial.")
cumplen = int(np.sum(tabla["C_nat"] <= tabla["Clim"]))
c3.metric("Zonas que cumplen sin hacer nada", f"{cumplen} de {p.n}")

# ---- Concentración ----------------------------------------------------------------
st.subheader("TPH sin tratamiento frente al límite")
st.caption("Círculo blanco: TPH inicial. Rombo: TPH al final sin hacer nada. Raya negra: límite legal. "
           "Si el rombo queda por encima de la raya, la zona debe intervenirse.")
st.plotly_chart(fig_concentracion(p, tabla["C_nat"].values), width="stretch")

vista = tabla.assign(
    **{"¿Debe intervenirse?": np.where(tabla["obligatoria"], "Sí", "No"),
       "¿Se puede cumplir?": np.where(tabla["C_pot"] <= tabla["Clim"], "Sí", "No")})
vista = vista.rename(columns={
    "suelo": "Suelo", "C0": "TPH inicial (mg/kg)", "k_nat": "k natural (1/día)",
    "C_nat": "TPH final sin tratar (mg/kg)", "k_pot": "k con dosis máxima (1/día)",
    "C_pot": "TPH final con dosis máxima (mg/kg)", "Clim": "Límite (mg/kg)",
    "recalcitrante": "No degradable (mg/kg)"}).drop(columns="obligatoria")
st.dataframe(vista, width="stretch", column_config={
    c: st.column_config.NumberColumn(format="%.0f") for c in vista.columns if "mg/kg" in c} | {
    c: st.column_config.NumberColumn(format="%.4f") for c in vista.columns if "1/día" in c})

# ---- Factores -----------------------------------------------------------------------
st.subheader("¿Qué frena la degradación en cada zona?")
st.caption("Cada factor va de 0 a 1 (1 = condición ideal). La velocidad de degradación es el producto de "
           "todos, así que el valor más bajo es el cuello de botella. Situación sin tratamiento.")
cero = np.zeros(p.n)
f = factores(p, cero, np.zeros((p.n, p.m)), cero, cero)
st.plotly_chart(fig_factores(p, f), width="stretch")

controlables = {"f_bio": "se corrige con consorcio microbiano",
                "f_nut": "se corrige con nitrógeno y fósforo",
                "f_pH": "se corrige con cal",
                "f_O": "mejora con la labranza al intervenir la zona",
                "f_H": "depende del riego/drenaje (el modelo no lo optimiza)",
                "f_T": "depende del clima",
                "f_tox": "depende de qué tan contaminada está la zona"}
lineas = []
for i, zona in enumerate(p.nombres):
    clave = min(f, key=lambda c: f[c][i])
    lineas.append(f"- **{zona}**: lo que más frena es **{NOMBRES_FACTORES[clave].lower()}** "
                  f"({f[clave][i]:.2f}); {controlables[clave]}.")
st.markdown("\n".join(lineas))

st.page_link("paginas/optimizar.py", label="Siguiente: calcular el plan óptimo →", icon="🎯")
