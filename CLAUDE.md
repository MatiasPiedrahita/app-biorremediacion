# CLAUDE.md — Biorremediación con optimización multiobjetivo

Proyecto final de **Técnicas de Optimización** (UPB, Medellín, 2026), hecho por Santiago Fonseca y Matias Piedrahita.

El modelo decide cómo limpiar un suelo contaminado con hidrocarburos de petróleo (TPH). Para cada zona del sitio elige si intervenirla y cuánto consorcio microbiano, nitrógeno, fósforo y cal aplicar. Tiene dos objetivos en conflicto: **maximizar el porcentaje de contaminante eliminado** y **minimizar el costo**. Se resuelve con el **método ε-constraint**, que genera el frente de Pareto.

Estado: la Entrega 2 está terminada (modelo mejorado, programado en Python y datos validados). Para la entrega final se construyó una **aplicación Streamlit** (`app.py`) sobre el paquete `biorremediacion/`, con escenarios, comparación y sensibilidad. Ver `README.md`.

## Estructura de la carpeta

```
Biorremediacion/
├── CLAUDE.md                     ← este archivo
├── README.md                     ← cómo correr y desplegar la app
├── requirements.txt / requirements-dev.txt
├── app.py                        ← app Streamlit (navegación)
├── paginas/                      ← páginas de la app + comun.py (estado, caché)
├── biorremediacion/              ← paquete del modelo (fuente de verdad)
│   ├── datos.py  modelo.py  solver.py  sensibilidad.py  graficas.py  exportar.py
├── datos/frente_base.json        ← frente del caso base precalculado (lo genera el script)
├── tests/test_regresion.py       ← regresión contra los valores de referencia
├── modelo/
│   ├── biorremediacion_econstraint.py   ← main: usa el paquete, imprime y guarda PNG/CSV/JSON
│   ├── resultados_pareto.csv            ← salida: 16 soluciones no dominadas
│   ├── resultados_detalle.json          ← salida: dosis, k y costos por solución
│   ├── frente_pareto.png, dosis_por_zona.png
│   └── dump_resultados.py               ← genera resultados_detalle.json
├── presentacion/
│   ├── Biorremediacion_ambiental.pptx   ← presentación de la Entrega 2 (40 diapositivas)
│   └── Biorremediacion_ambiental.pdf
├── documentos/
│   ├── Biorremediacion_cambios_formulacion.pdf / .tex   ← formulación completa en LaTeX
│   └── Articulo_Biorremediacion_Entrega1.docx          ← artículo de la Entrega 1 (modelo viejo)
├── figuras/                      ← gráficas de la presentación y los scripts que las generan
└── entrega1/Biorremediacion_ambiental_entrega1.pptx    ← presentación original (histórico)
```

El artículo de la Entrega 1 y `entrega1/` describen el **modelo viejo**, sin factores del entorno. No los uses como referencia del modelo actual.

## Cómo correrlo

```bash
pip install -r requirements.txt
cd modelo
python biorremediacion_econstraint.py      # ~30 s; imprime diagnóstico y tabla, guarda PNG, CSV y ../datos/frente_base.json
python dump_resultados.py                  # opcional: detalle por solución en JSON
cd ..
streamlit run app.py                       # la aplicación
pytest tests                               # pruebas de regresión (~35 s)
```

## El modelo (resumen)

Índices: zonas `i = 1..n` (n = 6), consorcios `j = 1..m` (m = 2), tipo de suelo `s(i)` ∈ {arenoso, franco, arcilloso}.

**Variables por zona.** `y_i` ∈ {0,1} indica si se interviene. `x_ij` es la dosis de consorcio (L/m²). `N_i` es el nitrógeno (kg/m²), `P_i = N_i/10` el fósforo y `L_i` la cal (kg/m²).

**Velocidad de degradación.** Es un producto de factores entre 0 y 1:

```
k_i = k_max · f_bio · f_nut · f_T · f_H · f_pH · f_O · f_tox
```

| Factor | Fórmula | Qué representa |
|---|---|---|
| `f_bio` | `M/(K_M+M)`, con `M = B_i + Σ_j s_ij·a_j·x_ij` | biomasa: nativos más el inóculo que sobrevive. `s_ij = σ_js/(1+B_i/B_c)` |
| `f_nut` | `S/(K_S+S)`, con `S = (N0_i+N_i)/N_req_i` | N disponible frente al requerido. `N_req = 0.10·0.85·C0·ρ·h·1e-6` (C:N:P = 100:10:1) |
| `f_T` | `min(1, θ^(Θ−T_ref))` | temperatura del sitio |
| `f_H` | `exp(−((H−60)/25)²)` | humedad, como % de capacidad de campo |
| `f_pH` | `exp(−((pH−7)/2)²)`, con `pH = pH0 + L/b_s` | la cal sube el pH |
| `f_O` | `fO_nat + (fO_lab − fO_nat)·y_i` | la labranza (intervenir la zona) mejora el oxígeno |
| `f_tox` | `1/(1 + C0/K_I)` | el exceso de crudo inhibe a los microorganismos |

**Concentración final.** Incluye una fracción recalcitrante φ que no se degrada:

```
C_i(T) = C0_i·[φ_s + (1−φ_s)·e^(−k_i·T)]        R_i = (1−φ_s)(1−e^(−k_i·T))
```

**Objetivos.**
- `max f1 = Σ w_i·R_i`, con `w_i = A_i·C0_i / Σ A·C0`. Es la fracción del contaminante total del sitio que se elimina.
- `min f2 = Σ [(c_mov + c_lab·A_i)·y_i + A_i·(Σ_j c_j·x_ij + c_N·N_i + c_P·P_i + c_L·L_i)]`. Está en COP; el script lo reporta en millones.

**Restricciones.**
- R1 `C_i(T) ≤ C_lim_i`: 10 000 mg/kg en general y 5 000 mg/kg cerca de agua.
- R2 `x_ij ≤ x_max·y_i`, con `x_max = 3` L/m².
- R3 `N_i ≤ (r_i·N_req_i − N0_i)·y_i`, con `r = 1.0` en general y `0.5` cerca de agua.
- R4 `P_i = N_i/10`.
- R5 `L_i ≤ (7.5 − pH0_i)·b_s·y_i`.
- R6 `Σ_i A_i·x_ij ≤ Q_j`.
- R7 variables no negativas; `y` binaria.

**Método de solución** (MINLP biobjetivo no convexo):
1. Las zonas que no cumplen la norma solo con degradación natural se fijan en `y = 1`; hoy son Z1–Z4. Las demás se enumeran (2² combinaciones).
2. Para cada `y`, el problema continuo se resuelve con `scipy.optimize.minimize(method="SLSQP")` desde 3 puntos iniciales.
3. ε-constraint: `ε_min` sale de minimizar f2 y `ε_max` es el costo de la máxima f1. Se usa una rejilla de G = 15 (16 presupuestos) y luego se filtran las soluciones dominadas.
4. El punto rodilla es el más alejado de la recta entre los extremos, con el frente normalizado.

SLSQP es local, así que **no garantiza el óptimo global**.

## Estructura del paquete `biorremediacion/`

- `datos.py`: `Escenario` (dataclass) con todos los datos del caso base y su fuente en comentarios; tablas `suelos`, `zonas`, `consorcios`, `supervivencia`. `escenario_base()`, `copia(**cambios)`, `to_dict/from_dict`, `clave()` (JSON estable, usado como clave de caché), `ETIQUETAS` (nombre, unidad, fuente) y `diferencias(a, b)`.
- `modelo.py`: `Parametros(esc)` calcula los derivados (`Nreq`, `Ncap`, `Lcap`, `Clim`, `s`, `aporte`, `w`, `c_fijo`) y también `k_nat`, `obligatorias` y `libres`. Las funciones reciben `p`: `velocidad_k(p, y, x, N, L)`, `factores`, `concentracion_final`, `f1_limpieza`, `f2_costo`, `costos_por_componente`, `detallar`, `diagnostico(p)` → `(tabla, avisos)`.
- `solver.py`: `resolver_subproblema(p, y, …)`, `resolver(p, objetivo, eps, f1_min)` y `frente_pareto(p, G, progreso)`, que devuelve `{estado: "ok"|"infactible", mensaje, soluciones, i_rodilla}`. También `tabla_resultados`, `punto_rodilla` y `frente_a_json/frente_desde_json`.
- `sensibilidad.py`: `analizar(esc, parametros, delta)` resuelve solo los extremos (costo mínimo y máxima limpieza) de cada variante.
- Para cambiar un parámetro: `Parametros(escenario_base().copia(t_trat=60))`. No hay globales.

## Valores de referencia (para pruebas de regresión)

Corresponden al caso base actual (T = 90 días, 27.7 °C). Usa una tolerancia de ±0.5 % en f1 y ±1 M COP en f2, porque SLSQP depende de los puntos iniciales.

| Estrategia | Costo f2 (M COP) | Limpieza f1 | Zonas intervenidas |
|---|---|---|---|
| Costo mínimo | 91.35 | 52.0 % | Z1–Z4 |
| Punto rodilla | 129.50 | 72.9 % | Z1–Z6 |
| Máxima limpieza | 282.11 | 79.0 % | Z1–Z6 |

- El frente tiene 16 puntos no dominados.
- Sin tratamiento, `k_nat` va de 0.0006 a 0.0042 día⁻¹. Con el máximo de insumos, k va de 0.025 a 0.048 día⁻¹.
- En el punto rodilla, Z1 y Z2 quedan exactamente en su límite (la restricción R1 está activa).
- El costo del punto rodilla es 66 % fijo. Pasar de la rodilla a la máxima limpieza cuesta 153 M COP adicionales, casi todo en consorcio.
- Con T = 60 días el caso base es **infactible**: Z1 llega como mínimo a 10 313 mg/kg aun con la dosis máxima. Con T = 75 días ya es factible. Con T = 180 días, el costo mínimo es 40.2 M COP y la limpieza máxima 86.4 % (G = 5).

Si un cambio en el código mueve estos números sin que se haya querido cambiar el modelo, es un error.

## Datos: qué está validado y qué es supuesto

En la Entrega 2 se contrastaron 24 datos con fuentes reales: 8 estaban en rango, 15 se ajustaron y 1 queda como supuesto. Las tablas completas, con fuentes, están en las diapositivas 24–28 de la presentación y en `documentos/Biorremediacion_cambios_formulacion.pdf`.

- **Validados.**
  - Límite TPH de 10 000 mg/kg: Colombia no tiene norma nacional; Ecopetrol usa Louisiana 29-B (< 1 %).
  - Límite cerca de agua de 5 000 mg/kg (NOM-138 de México como referencia).
  - Θ = 27.7 °C (IDEAM, Barrancabermeja) y θ = 1.11 (Man, 1998).
  - Humedad, pH y C:N:P según EPA (1995) y FRTR.
  - TPH inicial de 6 000–30 000 mg/kg.
  - Precios 2026: urea en SIPSA-DANE → `c_N = 8 700` COP/kg N; DAP → `c_P = 25 000`; cal dolomita → `c_L = 300`.
  - Costo total resultante de USD 28–87 por m³, dentro de lo reportado.
- **Supuestos sin fuente directa.** `K_M`, `K_S`, `B_c`, la supervivencia `σ`, los factores de oxígeno y el precio del consorcio (30 000–45 000 COP/L; solo se consigue por cotización).
- **Calibrado.** `K_MAX = 0.22` día⁻¹ se ajustó para que k caiga en los rangos de la literatura.
- El sitio y sus 6 zonas son un **caso de estudio ilustrativo**: los valores son plausibles, pero no salen de un muestreo real.

Regla: **no inventes datos nuevos.** Si la app necesita un valor que no está en el script, pídelo o búscalo con fuente, y márcalo como supuesto cuando no la tenga.

## Para la aplicación

La app ya existe (`streamlit run app.py`). Lineamientos con los que se construyó:

- **No dupliques la lógica del modelo.** Refactoriza el script en un paquete, por ejemplo `bioremediacion/datos.py`, `modelo.py`, `solver.py` y `graficas.py`. Los parámetros deben entrar como argumentos u objetos de configuración (dataclass o dict), no como globales. Mantén el script original funcionando o reemplázalo por un `main` que dé los mismos resultados de referencia.
- **Escenarios previstos para la entrega final:**
  - tiempo T = 60, 90 y 180 días;
  - precio del consorcio;
  - límite legal más estricto;
  - temperatura y tipo de suelo;
  - análisis de sensibilidad de los supuestos (`K_MAX`, `K_M`, `K_S`, σ).

  La app debería permitir editar estos parámetros y las zonas.
- **Rendimiento.** Un frente completo tarda ~40 s. Muestra el progreso, calcula en segundo plano o con caché, y deja que el usuario cambie G (número de presupuestos).
- **Visualizaciones útiles:**
  - frente de Pareto interactivo, donde al elegir un punto se vean dosis por zona, costo por componente y concentración final contra el límite;
  - diagnóstico del sitio sin tratamiento;
  - comparación de escenarios.
- **Infactibilidad.** Si un escenario no puede cumplir la norma (por ejemplo, T muy corto o un límite menor que φ·C0), la app debe decirlo claramente, no fallar.
- Stack sugerido, salvo que se pida otro: Python con **Streamlit** (u otro framework web) y Plotly para gráficas interactivas, reutilizando numpy, scipy y pandas.

## Convenciones

- Idioma: **español** en la interfaz, los comentarios, los nombres de variables del dominio y los mensajes.
- Unidades:
  - concentraciones en mg/kg;
  - dosis en L/m² (consorcio) y kg/m² (N, P, cal);
  - k en día⁻¹ y T en días;
  - costos en COP, mostrados en millones (M COP). Para USD se usó la TRM de 3 174.67 (19 oct. 2026).
- En el código los decimales van con punto. Los textos para usuarios siguen el estilo de la presentación: punto decimal y espacio fino o normal como separador de miles.
- Antes de dar por terminado un cambio al modelo, corre el script y compara con los valores de referencia.
