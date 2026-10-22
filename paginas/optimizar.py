import numpy as np
import streamlit as st

from biorremediacion import detallar, diagnostico, tabla_resultados
from biorremediacion.exportar import csv_frente, excel_plan, tabla_plan
from biorremediacion.graficas import fig_concentracion, fig_costos, fig_dosis, fig_pareto
from biorremediacion.modelo import concentracion_final
from biorremediacion.solver import frente_a_json
from paginas.comun import (calcular_frente, escenario, frente_disponible, guardados, mcop, miles,
                           parametros, pct)

esc = escenario()
p = parametros(esc)

st.title("🎯 Plan óptimo")
st.markdown("La herramienta busca, para distintos presupuestos, el plan que **más limpia** cumpliendo la norma. "
            "Luego usted elige el plan que más le convenga.")

with st.expander("Opciones del cálculo"):
    G = st.slider("Número de presupuestos a evaluar", 5, 25, 15,
                  help="Más presupuestos = frente más detallado, pero el cálculo tarda más "
                       "(unos 2 segundos por presupuesto en el caso base).")

frente = frente_disponible(esc, G)
if frente is None:
    _, avisos = diagnostico(p)
    if avisos:
        st.warning("El diagnóstico indica que este escenario no puede cumplir la norma; el cálculo lo confirmará.")
    st.info(f"Este escenario aún no se ha calculado. Tardará aproximadamente {max(20, 2 * (G + 2))} s "
            "o más si cambió el número de zonas.")
    if st.button("▶ Calcular planes óptimos", type="primary"):
        frente = calcular_frente(esc, G)
    else:
        st.stop()


def boton_guardar(contenedor):
    """Guarda el escenario y su frente (factible o no) para la página Comparar."""
    with contenedor.popover("💾 Guardar para comparar", width="stretch"):
        nombre = st.text_input("Nombre del escenario", value=f"T = {esc.t_trat:g} d, {esc.temp:g} °C")
        if st.button("Guardar", type="primary"):
            guardados()[nombre] = {"escenario": esc.to_dict(), "G": G, "frente": frente_a_json(frente)}
            st.success(f"Guardado «{nombre}». Véalo en **Comparar escenarios**.")


if frente["estado"] != "ok":
    st.error("**No existe ningún plan que cumpla la norma con estos datos.**")
    st.markdown(frente["mensaje"])
    st.info("Pruebe con más días de tratamiento, un límite legal menos estricto o más consorcio disponible "
            "en la página **Sitio y parámetros**.")
    boton_guardar(st.columns(3)[0])
    st.stop()

sol, ir = frente["soluciones"], frente["i_rodilla"]
n_pts = len(sol)
clave_frente = f"{hash(esc.clave())}_{G}"

# ---- Estado de la selección ------------------------------------------------------
if st.session_state.get("sel_frente") != clave_frente:
    st.session_state.sel_frente = clave_frente
    st.session_state.sel = ir
    st.session_state.ultimo_clic = None

clave_grafica = f"pareto_{clave_frente}"
evento = st.session_state.get(clave_grafica)
if evento:
    puntos = [q["point_index"] for q in evento["selection"]["points"] if q.get("curve_number") == 0]
    if puntos and puntos != st.session_state.ultimo_clic:
        st.session_state.ultimo_clic = puntos
        st.session_state.sel = int(puntos[0])
st.session_state.sel = min(st.session_state.sel, n_pts - 1)


def elegir(i):
    st.session_state.sel = i


def elegir_por_presupuesto():
    tope = st.session_state.presupuesto
    caben = [i for i, s in enumerate(sol) if s["f2"] <= tope + 1e-9]
    st.session_state.aviso_presupuesto = None
    if caben:
        st.session_state.sel = max(caben, key=lambda i: sol[i]["f1"])
    else:
        st.session_state.aviso_presupuesto = (f"Con {mcop(tope)} no alcanza para cumplir la norma: el plan más "
                                              f"barato cuesta {mcop(sol[0]['f2'])}.")


# ---- Resumen y frente -----------------------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Plan más barato que cumple", mcop(sol[0]["f2"]), f"{pct(sol[0]['f1'])} eliminado", delta_color="off")
c2.metric("Mejor relación costo-beneficio", mcop(sol[ir]["f2"]), f"{pct(sol[ir]['f1'])} eliminado",
          delta_color="off")
c3.metric("Máxima limpieza", mcop(sol[-1]["f2"]), f"{pct(sol[-1]['f1'])} eliminado", delta_color="off")

st.subheader("Elija un plan")
b1, b2, b3, b4 = st.columns([1, 1, 1, 1.4])
b1.button("💲 Más barato", on_click=elegir, args=(0,), width="stretch")
b2.button("⭐ Mejor relación", on_click=elegir, args=(ir,), width="stretch")
b3.button("🧹 Máxima limpieza", on_click=elegir, args=(n_pts - 1,), width="stretch")
with b4.popover("💼 Según mi presupuesto", width="stretch"):
    st.number_input("Presupuesto disponible (M COP)", min_value=0.0, value=float(round(sol[ir]["f2"])),
                    step=5.0, key="presupuesto")
    st.button("Buscar el mejor plan que quepa", on_click=elegir_por_presupuesto, type="primary")
if st.session_state.get("aviso_presupuesto"):
    st.warning(st.session_state.aviso_presupuesto)

st.caption("También puede hacer clic en cualquier punto de la gráfica. Cada punto es un plan óptimo: "
           "a la derecha cuesta más, arriba limpia más.")
i = st.session_state.sel
st.plotly_chart(fig_pareto(sol, p.nombres, ir, i), width="stretch", key=clave_grafica,
                on_select="rerun", selection_mode="points")

# ---- Detalle del plan elegido -------------------------------------------------------------
s = detallar(p, sol[i])
etiqueta = {0: "el más barato", ir: "mejor relación costo-beneficio", n_pts - 1: "máxima limpieza"}.get(i, "")
st.subheader(f"Plan elegido: punto {i}" + (f" ({etiqueta})" if etiqueta else ""))
zonas_si = [z for z, y in zip(p.nombres, s["y"]) if y == 1]
zonas_no = [z for z, y in zip(p.nombres, s["y"]) if y == 0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Contaminante eliminado", pct(s["f1"]))
c2.metric("Costo total", mcop(s["f2"]))
c3.metric("Zonas a intervenir", f"{len(zonas_si)} de {p.n}")
fijo = s["costos"]["fijo"] / s["f2"] if s["f2"] > 0 else 0
c4.metric("Parte fija del costo", f"{100 * fijo:.0f} %", help="Movilización de maquinaria y labranza.")

texto = f"Intervenir **{', '.join(zonas_si)}**"
texto += f"; dejar **{', '.join(zonas_no)}** con degradación natural (ya cumplen la norma)." if zonas_no else "."
litros = sol[i]["x"].T @ p.A
partes = [f"{miles(l)} L de consorcio {c.lower()}" for l, c in zip(litros, p.consorcios) if l > 0.5]
partes += [f"{miles(np.sum(sol[i]['N'] * p.A))} kg de nitrógeno",
           f"{miles(np.sum(sol[i]['N'] / 10 * p.A))} kg de fósforo",
           f"{miles(np.sum(sol[i]['L'] * p.A))} kg de cal"]
texto += " Insumos totales: " + ", ".join(partes[:-1]) + " y " + partes[-1] + "."
st.markdown(texto)

t1, t2, t3, t4 = st.tabs(["📋 Plan por zona", "💰 Costos", "🧪 TPH final vs límite", "📑 Todos los planes"])
with t1:
    def formato(v):
        if isinstance(v, str):
            return v
        return miles(v) if abs(v) >= 100 else f"{v:.4g}"
    st.dataframe(tabla_plan(p, sol[i]).map(formato).T, width="stretch")
    st.plotly_chart(fig_dosis(p, sol[i]), width="stretch")
with t2:
    comparar = {"Plan elegido": s["costos"]}
    if i != 0:
        comparar["Más barato"] = detallar(p, sol[0])["costos"]
    if i != n_pts - 1:
        comparar["Máxima limpieza"] = detallar(p, sol[-1])["costos"]
    st.plotly_chart(fig_costos(comparar), width="stretch")
    if i < n_pts - 1:
        extra = sol[-1]["f2"] - s["f2"]
        ganancia = 100 * (sol[-1]["f1"] - s["f1"])
        st.caption(f"Pasar de este plan a la máxima limpieza cuesta {mcop(extra)} más y elimina "
                   f"{ganancia:.1f} puntos porcentuales más de contaminante.")
with t3:
    st.plotly_chart(fig_concentracion(p, concentracion_final(p, p.k_nat), s["C_final"]),
                    width="stretch")
    activas = [z for z, c, l, y in zip(p.nombres, s["C_final"], p.Clim, s["y"]) if y and c >= 0.999 * l]
    if activas:
        st.caption(f"En {', '.join(activas)} el TPH final queda justo en el límite: el plan hace lo mínimo "
                   "necesario para cumplir la norma ahí.")
with t4:
    st.dataframe(tabla_resultados(p, sol), hide_index=True, width="stretch")
    st.caption("Ganancia = puntos de % de limpieza que se obtienen por cada millón adicional.")

# ---- Descargas y guardar ----------------------------------------------------------------------
st.subheader("Descargar y guardar")
c1, c2, c3 = st.columns(3)
c1.download_button("⬇️ Plan elegido (Excel)", data=excel_plan(p, frente, i),
                   file_name=f"plan_biorremediacion_punto{i}.xlsx", width="stretch",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
c2.download_button("⬇️ Todos los planes (CSV)", data=csv_frente(p, frente), file_name="frente_pareto.csv",
                   mime="text/csv", width="stretch")
boton_guardar(c3)
