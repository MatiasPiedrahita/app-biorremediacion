import json

import pandas as pd
import streamlit as st

from biorremediacion import Parametros, detallar, escenario_base
from biorremediacion.datos import Escenario, diferencias
from biorremediacion.graficas import fig_costos, fig_frentes
from biorremediacion.solver import frente_a_json, frente_desde_json
from paginas.comun import fijar_escenario, frente_disponible, guardados

st.title("⚖️ Comparar escenarios")
st.markdown("Guarde escenarios desde **Plan óptimo** (botón «Guardar para comparar») y compárelos aquí. "
            "Por ejemplo: 60, 90 y 180 días de tratamiento, otro precio del consorcio o un límite más estricto.")

g = guardados()

# ---- Agregar, cargar y descargar --------------------------------------------------
c1, c2, c3 = st.columns(3)
base = frente_disponible(escenario_base(), 15)
if base and "Caso base" not in g:
    if c1.button("➕ Agregar el caso base", width="stretch"):
        g["Caso base"] = {"escenario": escenario_base().to_dict(), "G": 15, "frente": frente_a_json(base)}
        st.rerun()
if g:
    c2.download_button("⬇️ Descargar comparación (JSON)", data=json.dumps(g, ensure_ascii=False),
                       file_name="comparacion_escenarios.json", mime="application/json",
                       width="stretch")
with c3.popover("⬆️ Cargar comparación", width="stretch"):
    archivo = st.file_uploader("Archivo .json descargado antes desde esta página", type="json")
    if archivo is not None and st.session_state.get("ultima_comparacion") != archivo.file_id:
        st.session_state.ultima_comparacion = archivo.file_id
        try:
            g.update(json.load(archivo))
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo leer el archivo: {e}")

if not g:
    st.info("Todavía no hay escenarios guardados. Calcule un plan y use «Guardar para comparar».")
    st.page_link("paginas/optimizar.py", label="Ir a Plan óptimo →", icon="🎯")
    st.stop()

elegidos = st.multiselect("Escenarios a comparar", list(g), default=list(g)[:6],
                          help="El primero se usa como referencia para las diferencias.")
if not elegidos:
    st.stop()

escenarios = {n: Escenario.from_dict(g[n]["escenario"]) for n in elegidos}
frentes = {n: frente_desde_json(g[n]["frente"]) for n in elegidos}
factibles = [n for n in elegidos if frentes[n]["estado"] == "ok"]

# ---- Tabla resumen --------------------------------------------------------------------------
filas = []
for n in elegidos:
    fr = frentes[n]
    if fr["estado"] != "ok":
        filas.append({"Escenario": n, "Estado": "❌ No puede cumplir la norma"})
        continue
    s, ir = fr["soluciones"], fr["i_rodilla"]
    filas.append({"Escenario": n, "Estado": "✅",
                  "Más barato (M COP)": s[0]["f2"], "Limpieza más barato (%)": 100 * s[0]["f1"],
                  "Mejor relación (M COP)": s[ir]["f2"], "Limpieza mejor relación (%)": 100 * s[ir]["f1"],
                  "Máxima limpieza (M COP)": s[-1]["f2"], "Limpieza máxima (%)": 100 * s[-1]["f1"]})
tabla = pd.DataFrame(filas).set_index("Escenario")
st.subheader("Resumen")
st.dataframe(tabla, width="stretch",
             column_config={c: st.column_config.NumberColumn(format="%.1f") for c in tabla.columns if c != "Estado"})

if len(factibles) >= 2 and factibles[0] == elegidos[0]:
    ref = tabla.loc[factibles[0]]
    lineas = []
    for n in factibles[1:]:
        d_cost = tabla.loc[n, "Más barato (M COP)"] - ref["Más barato (M COP)"]
        d_lim = tabla.loc[n, "Limpieza máxima (%)"] - ref["Limpieza máxima (%)"]
        lineas.append(f"- **{n}** frente a **{factibles[0]}**: cumplir la norma cuesta {d_cost:+.1f} M COP y la "
                      f"limpieza máxima posible cambia {d_lim:+.1f} puntos.")
    st.markdown("\n".join(lineas))

# ---- Gráficas -------------------------------------------------------------------------------
if factibles:
    st.subheader("Frentes de Pareto")
    st.plotly_chart(fig_frentes({n: frentes[n]["soluciones"] for n in factibles}), width="stretch")

    st.subheader("Costo del plan de mejor relación costo-beneficio")
    costos = {}
    for n in factibles:
        p = Parametros(escenarios[n])
        costos[n] = detallar(p, frentes[n]["soluciones"][frentes[n]["i_rodilla"]])["costos"]
    st.plotly_chart(fig_costos(costos), width="stretch")

# ---- Qué cambia entre escenarios ---------------------------------------------------------------
st.subheader("¿Qué cambia entre escenarios?")
ref_nombre = elegidos[0]
for n in elegidos[1:]:
    cambios = diferencias(escenarios[ref_nombre], escenarios[n])
    with st.expander(f"{n} frente a {ref_nombre} ({len(cambios)} cambios)"):
        st.markdown("\n".join(f"- {c}" for c in cambios) if cambios else "Mismos datos.")

# ---- Administrar ---------------------------------------------------------------------------------
st.subheader("Administrar")
c1, c2 = st.columns(2)
nombre = c1.selectbox("Escenario", elegidos)
if c1.button("✏️ Abrirlo para editar en «Sitio y parámetros»"):
    fijar_escenario(escenarios[nombre], reiniciar_controles=True)
    st.success(f"Ahora está usando «{nombre}».")
if c2.button("🗑️ Quitar de la comparación"):
    del g[nombre]
    st.rerun()
