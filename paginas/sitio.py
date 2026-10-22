import json

import pandas as pd
import streamlit as st

from biorremediacion import escenario_base
from biorremediacion.datos import COLUMNAS_ZONAS, ETIQUETAS, Escenario, diferencias
from paginas.comun import MAX_ZONAS, escenario, fijar_escenario

esc = escenario()
ver = st.session_state.get("version_editores", 0)

st.title("🗺️ Sitio y parámetros")
st.markdown("Aquí se describe el sitio contaminado y las condiciones del tratamiento. Los cambios se aplican "
            "de inmediato; luego vaya a **Diagnóstico** o **Plan óptimo**.")

# ---- Barra de acciones -------------------------------------------------------
c1, c2, c3 = st.columns([1, 1, 2])
c1.button("↺ Restaurar caso base", on_click=fijar_escenario, args=(escenario_base(), True),
          width="stretch")
c2.download_button("⬇️ Descargar escenario", data=json.dumps(esc.to_dict(), ensure_ascii=False, indent=1),
                   file_name="escenario_biorremediacion.json", mime="application/json",
                   width="stretch")
with c3.popover("⬆️ Cargar escenario guardado", width="stretch"):
    archivo = st.file_uploader("Archivo .json descargado antes desde esta página", type="json")
    if archivo is not None and st.session_state.get("ultimo_archivo") != archivo.file_id:
        st.session_state.ultimo_archivo = archivo.file_id
        try:
            fijar_escenario(Escenario.from_dict(json.load(archivo)), reiniciar_controles=True)
            st.rerun()
        except Exception as e:  # archivo de otro tipo o dañado
            st.error(f"No se pudo leer el archivo: {e}")


# ---- Ayudas para los campos ---------------------------------------------------
def campo(nombre_campo, col=None, paso=None, formato=None, minimo=0.0, maximo=None, ayuda=None):
    nombre, unidad, fuente = ETIQUETAS[nombre_campo]
    clave = f"w_{nombre_campo}"
    if clave not in st.session_state:
        st.session_state[clave] = float(getattr(esc, nombre_campo))
    etiqueta = f"{nombre} ({unidad})" if unidad else nombre
    if fuente == "supuesto":
        etiqueta += " ⚠️"
    texto_ayuda = ayuda or ""
    if fuente:
        texto_ayuda += ("  \n" if texto_ayuda else "") + (
            "Supuesto sin fuente directa." if fuente == "supuesto" else f"Fuente: {fuente}.")
    return (col or st).number_input(etiqueta, key=clave, min_value=minimo, max_value=maximo, step=paso,
                                    format=formato, help=texto_ayuda or None)


def editor(nombre, df_inicial, **kw):
    """data_editor con datos de partida estables mientras la página está abierta."""
    clave = f"ed_{nombre}_{ver}"
    if clave not in st.session_state:
        st.session_state[f"inicial_{nombre}_{ver}"] = df_inicial
    return st.data_editor(st.session_state[f"inicial_{nombre}_{ver}"], key=clave, **kw)


def poner_tiempo(t):
    st.session_state.w_t_trat = float(t)


valores = {}
errores = []

# ---- Tratamiento --------------------------------------------------------------
st.subheader("Tratamiento y clima")
c1, c2 = st.columns(2)
with c1:
    valores["t_trat"] = campo("t_trat", paso=5.0, formato="%.0f", minimo=1.0, maximo=730.0,
                              ayuda="Días que dura el tratamiento antes de medir el TPH final.")
    b = st.columns(3)
    for col, t in zip(b, (60, 90, 180)):
        col.button(f"{t} días", on_click=poner_tiempo, args=(t,), width="stretch")
with c2:
    valores["temp"] = campo("temp", paso=0.5, formato="%.1f", minimo=-10.0, maximo=50.0,
                            ayuda="Temperatura media del suelo durante el tratamiento.")

# ---- Zonas --------------------------------------------------------------------
st.subheader("Zonas del sitio")
st.caption(f"Una fila por zona (máximo {MAX_ZONAS}). Puede agregar filas al final de la tabla o borrarlas "
           "seleccionándolas. «Cerca de agua» aplica el límite más estricto y menos nitrógeno.")
suelos_validos = list(esc.suelos.index)
z = esc.zonas.copy()
z.insert(0, "Zona", z.index)
z["sensible"] = z["sensible"].astype(bool)
zonas_ed = editor(
    "zonas", z.reset_index(drop=True), num_rows="dynamic", hide_index=True, width="stretch",
    column_config={
        "Zona": st.column_config.TextColumn("Zona", required=True, max_chars=12),
        "A": st.column_config.NumberColumn(COLUMNAS_ZONAS["A"], min_value=1, step=10, required=True),
        "C0": st.column_config.NumberColumn(COLUMNAS_ZONAS["C0"], min_value=1, max_value=300000, step=500,
                                            required=True),
        "suelo": st.column_config.SelectboxColumn(COLUMNAS_ZONAS["suelo"], options=suelos_validos,
                                                  required=True),
        "H": st.column_config.NumberColumn(COLUMNAS_ZONAS["H"], min_value=0, max_value=100, step=1,
                                           required=True),
        "pH0": st.column_config.NumberColumn(COLUMNAS_ZONAS["pH0"], min_value=3, max_value=10, step=0.1,
                                             format="%.1f", required=True),
        "B": st.column_config.NumberColumn(COLUMNAS_ZONAS["B"], min_value=0, max_value=100, step=0.1,
                                           format="%.2f", required=True),
        "N0": st.column_config.NumberColumn(COLUMNAS_ZONAS["N0"], min_value=0, max_value=5, step=0.005,
                                            format="%.3f", required=True),
        "sensible": st.column_config.CheckboxColumn(COLUMNAS_ZONAS["sensible"], default=False),
    })
zonas_ed = zonas_ed.copy()
zonas_ed["sensible"] = zonas_ed["sensible"].fillna(False).astype(bool).astype(int)
zonas_ed["Zona"] = zonas_ed["Zona"].astype(str).str.strip()
if zonas_ed.drop(columns="sensible").isna().any().any() or (zonas_ed["Zona"].isin(["", "None", "nan"])).any():
    errores.append("Hay celdas vacías en la tabla de zonas. Complete todas las columnas de cada fila.")
elif zonas_ed["Zona"].duplicated().any():
    errores.append("Hay dos zonas con el mismo nombre. Cada zona debe tener un nombre distinto.")
elif len(zonas_ed) == 0:
    errores.append("Debe haber al menos una zona.")
elif len(zonas_ed) > MAX_ZONAS:
    errores.append(f"Hay {len(zonas_ed)} zonas; el máximo es {MAX_ZONAS} para que el cálculo no tarde demasiado.")
zonas_nuevas = zonas_ed.set_index("Zona")[list(esc.zonas.columns)]
zonas_nuevas.index.name = None

# ---- Norma ----------------------------------------------------------------------
st.subheader("Norma (límite de TPH al final)")
c1, c2 = st.columns(2)
valores["c_lim_general"] = campo("c_lim_general", c1, paso=500.0, formato="%.0f", minimo=1.0)
valores["c_lim_sensible"] = campo("c_lim_sensible", c2, paso=500.0, formato="%.0f", minimo=1.0)
with st.expander("Topes de nitrógeno"):
    c1, c2 = st.columns(2)
    valores["r_n_general"] = campo("r_n_general", c1, paso=0.05, formato="%.2f", maximo=3.0,
                                   ayuda="1.0 = el N que pide la relación C:N:P 100:10:1.")
    valores["r_n_sensible"] = campo("r_n_sensible", c2, paso=0.05, formato="%.2f", maximo=3.0,
                                    ayuda="Menos N cerca del agua para evitar lixiviación.")

# ---- Precios y consorcios ----------------------------------------------------------
st.subheader("Precios e insumos")
c1, c2, c3 = st.columns(3)
valores["c_n"] = campo("c_n", c1, paso=100.0, formato="%.0f")
valores["c_p"] = campo("c_p", c2, paso=500.0, formato="%.0f")
valores["c_cal"] = campo("c_cal", c3, paso=10.0, formato="%.0f")
valores["c_mov"] = campo("c_mov", c1, paso=100000.0, formato="%.0f")
valores["c_lab"] = campo("c_lab", c2, paso=500.0, formato="%.0f")
valores["x_max"] = campo("x_max", c3, paso=0.5, formato="%.1f", minimo=0.0, maximo=20.0)

st.markdown("**Consorcios microbianos**")
st.caption("⚠️ El precio del consorcio es un supuesto (30 000–45 000 COP/L): solo se consigue por cotización.")
cons_ed = editor(
    "consorcios", esc.consorcios.copy(), num_rows="fixed", width="stretch",
    column_config={
        "costo": st.column_config.NumberColumn("Precio (COP/L) ⚠️", min_value=0, step=1000, required=True),
        "conc": st.column_config.NumberColumn("Concentración (UFC/mL)", min_value=0, format="%.2e",
                                              required=True),
        "Q": st.column_config.NumberColumn("Litros disponibles", min_value=0, step=100, required=True),
    })
if cons_ed.isna().any().any():
    errores.append("Complete todos los datos de los consorcios.")

# ---- Avanzado ------------------------------------------------------------------------
with st.expander("⚙️ Avanzado: parámetros del modelo (⚠️ = supuesto sin fuente directa)"):
    st.caption("Normalmente no hace falta tocarlos. Úselos para escenarios de sensibilidad o si tiene "
               "datos de laboratorio del sitio.")
    c1, c2, c3 = st.columns(3)
    valores["k_max"] = campo("k_max", c1, paso=0.01, formato="%.3f", minimo=0.001)
    valores["k_m"] = campo("k_m", c2, paso=0.1, formato="%.2f", minimo=0.01)
    valores["k_s"] = campo("k_s", c3, paso=0.05, formato="%.2f", minimo=0.01)
    valores["b_comp"] = campo("b_comp", c1, paso=0.1, formato="%.2f", minimo=0.01)
    valores["k_i"] = campo("k_i", c2, paso=1000.0, formato="%.0f", minimo=1.0)
    valores["theta"] = campo("theta", c3, paso=0.01, formato="%.2f", minimo=1.0)
    valores["t_ref"] = campo("t_ref", c1, paso=0.5, formato="%.1f")
    valores["h_opt"] = campo("h_opt", c2, paso=1.0, formato="%.0f", maximo=100.0)
    valores["sig_h"] = campo("sig_h", c3, paso=1.0, formato="%.0f", minimo=1.0)
    valores["ph_opt"] = campo("ph_opt", c1, paso=0.1, formato="%.1f")
    valores["sig_ph"] = campo("sig_ph", c2, paso=0.1, formato="%.1f", minimo=0.1)
    valores["ph_max"] = campo("ph_max", c3, paso=0.1, formato="%.1f")
    valores["rho"] = campo("rho", c1, paso=50.0, formato="%.0f", minimo=100.0)
    valores["prof"] = campo("prof", c2, paso=0.05, formato="%.2f", minimo=0.01)
    valores["frac_c"] = campo("frac_c", c3, paso=0.01, formato="%.2f", maximo=1.0)
    valores["relacion_cn"] = campo("relacion_cn", c1, paso=0.01, formato="%.3f", maximo=1.0)

    st.markdown("**Tipos de suelo**")
    suelos_ed = editor(
        "suelos", esc.suelos.copy(), num_rows="fixed", width="stretch",
        column_config={
            "phi": st.column_config.NumberColumn("Fracción recalcitrante φ", min_value=0, max_value=0.99,
                                                 step=0.01, format="%.2f", required=True),
            "fO_nat": st.column_config.NumberColumn("Oxígeno sin labranza ⚠️", min_value=0, max_value=1,
                                                    step=0.05, format="%.2f", required=True),
            "fO_lab": st.column_config.NumberColumn("Oxígeno con labranza ⚠️", min_value=0, max_value=1,
                                                    step=0.05, format="%.2f", required=True),
            "b_cal": st.column_config.NumberColumn("Cal por unidad de pH (kg/m²)", min_value=0.01,
                                                   step=0.01, format="%.2f", required=True),
        })
    st.markdown("**Supervivencia del inóculo σ ⚠️** (fracción que sobrevive, por consorcio y suelo)")
    sup_ed = editor(
        "supervivencia", esc.supervivencia.copy(), num_rows="fixed", width="stretch",
        column_config={c: st.column_config.NumberColumn(c, min_value=0, max_value=1, step=0.05,
                                                        format="%.2f", required=True)
                       for c in esc.supervivencia.columns})
    if suelos_ed.isna().any().any() or sup_ed.isna().any().any():
        errores.append("Complete todos los datos de suelos y supervivencia.")

# ---- Validaciones cruzadas y aplicar cambios -------------------------------------------------
if valores["c_lim_sensible"] > valores["c_lim_general"]:
    st.warning("El límite cerca de agua es mayor que el general; normalmente debería ser más estricto.")

st.divider()
if errores:
    for e in errores:
        st.error(e)
    st.info("Los cambios no se aplicarán hasta corregir lo anterior. Se sigue usando el último escenario válido.")
else:
    nuevo = esc.copia(**valores, zonas=zonas_nuevas, consorcios=pd.DataFrame(cons_ed),
                      suelos=pd.DataFrame(suelos_ed), supervivencia=pd.DataFrame(sup_ed))
    if nuevo.clave() != esc.clave():
        fijar_escenario(nuevo)
    cambios = diferencias(escenario_base(), nuevo)
    if cambios:
        with st.expander(f"✏️ Cambios respecto al caso base ({len(cambios)})", expanded=False):
            st.markdown("\n".join(f"- {c}" for c in cambios))
    else:
        st.success("Está usando el caso base de la Entrega 2.")
    st.page_link("paginas/diagnostico.py", label="Siguiente: ver el diagnóstico del sitio →", icon="🔎")
