# Planeador de biorremediación

Aplicación web (Streamlit) para planear la biorremediación de un suelo contaminado con hidrocarburos (TPH). Usa el modelo biobjetivo del proyecto (máxima limpieza contra mínimo costo, método ε-constraint).

Técnicas de Optimización · UPB · 2026 · Santiago Fonseca y Matias Piedrahita.

## Qué permite hacer

1. **Sitio y parámetros**: editar las zonas, el tiempo de tratamiento, la temperatura, la norma, los precios y los supuestos del modelo. Los escenarios se pueden guardar y cargar como JSON.
2. **Diagnóstico**: ver qué pasa sin tratamiento, qué zonas hay que intervenir y qué factor limita cada zona. Avisa si el escenario no puede cumplir la norma.
3. **Plan óptimo**: calcular el frente de Pareto y elegir un plan: el más barato, el de mejor relación costo-beneficio, el de máxima limpieza o el que quepa en un presupuesto. También se puede hacer clic en la gráfica. El plan se descarga en Excel.
4. **Comparar escenarios**: frentes superpuestos, tabla de estrategias y diferencias entre los datos.
5. **Sensibilidad**: gráfico tornado de `K_MAX`, `K_M`, `K_S` y σ con variaciones de ±10, ±20 o ±30 %.

## Correrla localmente

```bash
pip install -r requirements.txt
streamlit run app.py          # o: python -m streamlit run app.py (si "streamlit" no está en el PATH)
```

El caso base carga al instante porque usa `datos/frente_base.json`. Cualquier otro escenario tarda entre 20 y 60 s en calcularse, con barra de progreso. Los resultados quedan en caché mientras el servidor siga encendido.

## Publicarla en Streamlit Community Cloud

1. Cree un repositorio en GitHub y suba esta carpeta. Si no quiere publicarlos, puede excluir `presentacion/`, `documentos/` y `entrega1/`.
2. Entre a <https://share.streamlit.io>, elija **Create app** y seleccione el repositorio y la rama.
3. Use `app.py` como *Main file path*. En **Advanced settings** elija Python 3.12.
4. Despliegue. Cloud instala `requirements.txt` automáticamente.

Cada visitante tiene su propia sesión. Los escenarios guardados para comparar viven solo en esa sesión; para conservarlos, use los botones de descarga y carga de JSON.

## Estructura

```
app.py                  punto de entrada (navegación)
paginas/                una página por paso + comun.py (estado, caché, formato)
biorremediacion/        lógica del modelo (la app no la duplica)
  datos.py              Escenario (dataclass) con datos, fuentes y etiquetas
  modelo.py             Parametros, k, objetivos, costos, diagnóstico
  solver.py             SLSQP + enumeración de zonas + ε-constraint
  sensibilidad.py       análisis de un factor a la vez
  graficas.py           figuras Plotly
  exportar.py           tablas del plan y Excel/CSV
datos/frente_base.json  frente del caso base precalculado
modelo/                 script original (ahora usa el paquete) y sus salidas
tests/                  pruebas de regresión contra los valores de referencia
```

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest tests          # ~35 s
```

Si cambian los datos del caso base, regenere el frente precalculado:

```bash
cd modelo && python biorremediacion_econstraint.py
```
