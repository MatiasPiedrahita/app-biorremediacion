import streamlit as st

from paginas.comun import escenario, frente_disponible, mcop, pct

st.title("🌱 Planeador de biorremediación")
st.markdown(
    "Esta herramienta ayuda a planear la limpieza de un suelo contaminado con **hidrocarburos de "
    "petróleo (TPH)** usando microorganismos. Para cada zona del sitio decide **si conviene "
    "intervenirla** y **cuánto aplicar** de consorcio microbiano, nitrógeno, fósforo y cal.\n\n"
    "Hay dos metas que chocan: **limpiar lo más posible** y **gastar lo menos posible**. Por eso la "
    "herramienta no entrega un único plan, sino un menú de planes óptimos (el *frente de Pareto*): "
    "cada uno es el que más limpia para su presupuesto. Todos cumplen el límite legal de TPH.")

frente = frente_disponible(escenario(), 15)
if frente and frente["estado"] == "ok":
    s, ir = frente["soluciones"], frente["i_rodilla"]
    st.subheader("Resultado del escenario actual")
    c1, c2, c3 = st.columns(3)
    c1.metric("Plan más barato que cumple la norma", mcop(s[0]["f2"]), f"{pct(s[0]['f1'])} eliminado",
              delta_color="off")
    c2.metric("Mejor relación costo-beneficio", mcop(s[ir]["f2"]), f"{pct(s[ir]['f1'])} eliminado",
              delta_color="off")
    c3.metric("Máxima limpieza posible", mcop(s[-1]["f2"]), f"{pct(s[-1]['f1'])} eliminado",
              delta_color="off")

st.subheader("Cómo usarla")
pasos = [
    ("paginas/sitio.py", "1 · Sitio y parámetros",
     "Describa las zonas (área, contaminación, suelo, humedad, pH…), el tiempo de tratamiento, la norma y "
     "los precios. Viene cargado un caso de estudio para probar."),
    ("paginas/diagnostico.py", "2 · Diagnóstico",
     "Vea qué pasaría sin hacer nada, qué zonas hay que intervenir sí o sí y qué frena la degradación en "
     "cada una. Si el escenario es imposible de cumplir, aquí se avisa."),
    ("paginas/optimizar.py", "3 · Plan óptimo",
     "Calcule los planes óptimos, elija uno (el más barato, el de mejor relación costo-beneficio, el de "
     "máxima limpieza o el que quepa en su presupuesto) y descárguelo en Excel."),
    ("paginas/comparar.py", "4 · Comparar escenarios",
     "Guarde varios escenarios (por ejemplo 60, 90 y 180 días) y compárelos lado a lado."),
    ("paginas/sensibilidad.py", "5 · Sensibilidad",
     "Mida cuánto cambian los resultados si los supuestos del modelo están errados en ±10–30 %."),
]
for ruta, titulo, texto in pasos:
    with st.container(border=True):
        st.page_link(ruta, label=f"**{titulo}**")
        st.caption(texto)

with st.expander("📖 Glosario"):
    st.markdown(
        "- **TPH**: hidrocarburos totales de petróleo, en mg por kg de suelo.\n"
        "- **Límite legal**: TPH máximo permitido al final. Colombia no tiene norma nacional; se usa "
        "10 000 mg/kg (Louisiana 29-B, usada por Ecopetrol) y 5 000 mg/kg cerca de fuentes de agua "
        "(NOM-138 de México como referencia).\n"
        "- **Consorcio microbiano**: mezcla de microorganismos que degradan el crudo. Se aplica en L/m².\n"
        "- **Nitrógeno, fósforo y cal**: nutrientes y corrector de pH que aceleran a los microorganismos.\n"
        "- **Fracción recalcitrante**: parte del crudo pegada al suelo que no se degrada.\n"
        "- **Velocidad de degradación k**: qué tan rápido baja el TPH (1/día).\n"
        "- **Frente de Pareto**: conjunto de planes en los que no se puede limpiar más sin gastar más.\n"
        "- **Mejor relación costo-beneficio (punto rodilla)**: el plan donde gastar más ya rinde poco.")

st.caption("El sitio y sus 6 zonas son un caso de estudio ilustrativo: los valores son plausibles y están "
           "contrastados con literatura y precios de 2026, pero no salen de un muestreo real. Algunos "
           "parámetros del modelo son supuestos sin fuente directa (se marcan en la página 1). El método "
           "numérico (SLSQP) es local y no garantiza el óptimo global.")
