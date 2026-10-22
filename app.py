"""
Aplicación para planear la biorremediación de un suelo contaminado con TPH.

Ejecutar:  streamlit run app.py
"""

import streamlit as st

from paginas.comun import resumen_lateral

st.set_page_config(page_title="Planeador de biorremediación", page_icon="🌱", layout="wide")

paginas = [
    st.Page("paginas/inicio.py", title="Inicio", icon="🏠", default=True),
    st.Page("paginas/sitio.py", title="1 · Sitio y parámetros", icon="🗺️"),
    st.Page("paginas/diagnostico.py", title="2 · Diagnóstico", icon="🔎"),
    st.Page("paginas/optimizar.py", title="3 · Plan óptimo", icon="🎯"),
    st.Page("paginas/comparar.py", title="4 · Comparar escenarios", icon="⚖️"),
    st.Page("paginas/sensibilidad.py", title="5 · Sensibilidad", icon="📈"),
]
nav = st.navigation(paginas)
resumen_lateral()
st.sidebar.caption("Técnicas de Optimización · UPB 2026  \nSantiago Fonseca · Matias Piedrahita")
nav.run()
