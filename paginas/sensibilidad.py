import streamlit as st

from biorremediacion.graficas import fig_tornado
from biorremediacion.sensibilidad import PARAMETROS_SENSIBILIDAD
from paginas.comun import calcular_sensibilidad, escenario, sensibilidad_disponible

esc = escenario()

st.title("📈 Sensibilidad de los supuestos")
st.markdown(
    "Algunos parámetros del modelo no tienen fuente directa (son supuestos) o fueron calibrados. Aquí se "
    "mide cuánto cambian los resultados si cada uno estuviera errado, **uno a la vez** y dejando los demás "
    "fijos. Se reportan dos números por variante: lo que cuesta cumplir la norma (plan más barato) y la "
    "máxima limpieza posible.")

c1, c2 = st.columns([2, 1])
params = c1.multiselect("Parámetros a variar", list(PARAMETROS_SENSIBILIDAD),
                        default=list(PARAMETROS_SENSIBILIDAD), format_func=PARAMETROS_SENSIBILIDAD.get)
delta = c2.select_slider("Variación", options=[0.1, 0.2, 0.3], value=0.2, format_func=lambda v: f"±{v:.0%}")
if not params:
    st.stop()

df = sensibilidad_disponible(esc, params, delta)
if df is None:
    st.info(f"Se resolverán {1 + 2 * len(params)} variantes del escenario actual "
            f"(aproximadamente {5 * (1 + 2 * len(params))} s).")
    if st.button("▶ Calcular sensibilidad", type="primary"):
        df = calcular_sensibilidad(esc, params, delta)
    else:
        st.stop()

base = df[df["parametro"] == "base"].iloc[0]
if base["estado"] != "ok":
    st.error("El escenario actual no puede cumplir la norma, así que no hay un caso base con qué comparar. "
             "Ajuste el escenario en **Sitio y parámetros**.")
    st.stop()

c1, c2 = st.columns(2)
c1.plotly_chart(fig_tornado(df, "costo_min", "Costo de cumplir la norma (plan más barato)", "M COP"),
                width="stretch")
c2.plotly_chart(fig_tornado(df, "limpieza_max", "Máxima limpieza posible", "puntos %"),
                width="stretch")

var = df[df["parametro"] != "base"].copy()
var["efecto"] = (var["costo_min"] - base["costo_min"]).abs()
infactibles = var[var["estado"] != "ok"]
if not infactibles.empty:
    st.warning("Con estas variaciones ya no se puede cumplir la norma: " +
               ", ".join(f"{r.etiqueta} {r.variacion:+.0%}" for r in infactibles.itertuples()) + ".")
validas = var[var["estado"] == "ok"]
if not validas.empty:
    mayor = validas.loc[validas["efecto"].idxmax()]
    st.markdown(f"El supuesto que más mueve el costo es **{mayor['etiqueta']}**: con {mayor['variacion']:+.0%} "
                f"el plan más barato pasa de {base['costo_min']:.1f} a {mayor['costo_min']:.1f} M COP. "
                "Los supuestos con barras cortas casi no afectan la decisión; los de barras largas convendría "
                "medirlos en laboratorio antes de ejecutar el plan.")

tabla = df.assign(variacion=df["variacion"].map(lambda v: f"{v:+.0%}"))[
    ["etiqueta", "variacion", "costo_min", "limpieza_max", "estado"]].rename(columns={
        "etiqueta": "Parámetro", "variacion": "Variación", "costo_min": "Costo plan más barato (M COP)",
        "limpieza_max": "Máxima limpieza (%)", "estado": "Estado"})
with st.expander("Ver tabla"):
    st.dataframe(tabla, hide_index=True, width="stretch", column_config={
        c: st.column_config.NumberColumn(format="%.2f") for c in tabla.columns[2:4]})
    st.download_button("⬇️ Descargar (CSV)", tabla.to_csv(index=False).encode("utf-8-sig"),
                       file_name="sensibilidad.csv", mime="text/csv")
