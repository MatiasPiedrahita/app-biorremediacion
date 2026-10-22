"""Figuras interactivas (Plotly) para la aplicación."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Paleta de la presentación (validada para daltonismo; el ocre siempre va con etiqueta o tabla)
TEAL, TERRA, VIOLET, OCHRE = "#008C80", "#BF5B2C", "#6250D6", "#C98500"
INK, MUTED, GRID, ZONA_GRIS = "#201E1D", "#6B635A", "#E4DCCF", "#EFE6D8"
CATEGORICOS = [TEAL, TERRA, VIOLET, OCHRE, "#3D7DCA", "#8A6F4E"]

COMPONENTES = [("fijo", "Costo fijo (movilización y labranza)", TEAL),
               ("consorcio", "Consorcio microbiano", TERRA),
               ("nutrientes", "Nutrientes (N y P)", VIOLET),
               ("cal", "Cal", OCHRE)]

NOMBRES_FACTORES = {"f_bio": "Microorganismos", "f_nut": "Nutrientes", "f_T": "Temperatura",
                    "f_H": "Humedad", "f_pH": "pH", "f_O": "Oxígeno", "f_tox": "Toxicidad del crudo"}


def _estilo(fig, alto=420, **kw):
    layout = dict(height=alto, margin=dict(l=10, r=10, t=40, b=10), separators=". ",
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  font=dict(color=INK, size=13), hoverlabel=dict(bgcolor="white"),
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    layout.update(kw)
    fig.update_layout(**layout)
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    return fig


def fig_pareto(soluciones, nombres, i_rod, i_sel=None):
    """Frente de Pareto clicable. customdata = índice del punto."""
    f2 = np.array([s["f2"] for s in soluciones]); f1 = np.array([100 * s["f1"] for s in soluciones])
    zonas = [", ".join(np.array(nombres)[np.asarray(s["y"]) == 1]) for s in soluciones]
    fig = go.Figure()
    fig.add_vrect(x0=0, x1=f2[0], fillcolor=ZONA_GRIS, line_width=0, layer="below",
                  annotation_text="No alcanza para<br>cumplir la norma", annotation_position="top left",
                  annotation_font_color=MUTED)
    fig.add_trace(go.Scatter(
        x=f2, y=f1, mode="lines+markers", name="Planes óptimos",
        line=dict(color=TEAL, width=2), marker=dict(size=11, color=TEAL, line=dict(color="white", width=2)),
        customdata=np.column_stack([np.arange(len(f2)), zonas]),
        hovertemplate="<b>Punto %{customdata[0]}</b><br>Costo: %{x:.1f} M COP<br>"
                      "Limpieza: %{y:.1f} %<br>Zonas: %{customdata[1]}<extra></extra>"))
    marcas = {0: "Costo mínimo", i_rod: "Mejor relación<br>costo-beneficio", len(f2) - 1: "Máxima limpieza"}
    for i, texto in marcas.items():
        fig.add_annotation(x=f2[i], y=f1[i], text=f"{texto}<br>{f1[i]:.1f} % · {f2[i]:.1f} M",
                           showarrow=True, arrowcolor=MUTED, ax=40 if i < len(f2) - 1 else -40,
                           ay=40 if i != i_rod else -45, font=dict(size=11, color=INK))
    if i_sel is not None:
        fig.add_trace(go.Scatter(x=[f2[i_sel]], y=[f1[i_sel]], mode="markers", name="Plan elegido",
                                 marker=dict(size=22, color="rgba(0,0,0,0)", line=dict(color=INK, width=2.5)),
                                 hoverinfo="skip"))
    rango = max(f2[-1] - f2[0], 1)
    fig.update_xaxes(title="Costo total (millones de COP)", range=[f2[0] - 0.15 * rango, f2[-1] + 0.08 * rango])
    fig.update_yaxes(title="Contaminante eliminado (%)", range=[f1.min() - 4, f1.max() + 4])
    return _estilo(fig, alto=460, clickmode="event+select")


def fig_frentes(frentes):
    """Varios frentes superpuestos. `frentes` = {nombre: lista de soluciones}."""
    fig = go.Figure()
    for (nombre, sol), color in zip(frentes.items(), CATEGORICOS):
        f2 = [s["f2"] for s in sol]; f1 = [100 * s["f1"] for s in sol]
        fig.add_trace(go.Scatter(x=f2, y=f1, mode="lines+markers", name=nombre,
                                 line=dict(color=color, width=2), marker=dict(size=8, color=color),
                                 hovertemplate=f"<b>{nombre}</b><br>Costo: %{{x:.1f}} M COP<br>"
                                               "Limpieza: %{y:.1f} %<extra></extra>"))
    fig.update_xaxes(title="Costo total (millones de COP)")
    fig.update_yaxes(title="Contaminante eliminado (%)")
    return _estilo(fig, alto=460)


def fig_dosis(p, sol):
    """Dosis por zona de una solución: un panel por insumo (unidades distintas)."""
    paneles = [(f"Consorcio {c.lower()} (L/m²)", sol["x"][:, j]) for j, c in enumerate(p.consorcios)]
    paneles += [("Nitrógeno (kg/m²)", sol["N"]), ("Cal (kg/m²)", sol["L"])]
    fig = make_subplots(rows=1, cols=len(paneles), subplot_titles=[t for t, _ in paneles],
                        horizontal_spacing=0.06)
    for c, (titulo, v) in enumerate(paneles, start=1):
        fig.add_trace(go.Bar(x=p.nombres, y=v, marker_color=TEAL, showlegend=False,
                             hovertemplate="%{x}: %{y:.3f}<extra>" + titulo + "</extra>"), row=1, col=c)
    fig.update_annotations(font_size=12)
    return _estilo(fig, alto=300, bargap=0.35)


def fig_costos(estrategias):
    """Barras apiladas del costo por componente. `estrategias` = {nombre: dict de costos}."""
    nombres = list(estrategias)[::-1]
    fig = go.Figure()
    for clave, texto, color in COMPONENTES:
        v = [estrategias[n][clave] for n in nombres]
        fig.add_trace(go.Bar(y=nombres, x=v, name=texto, orientation="h", marker_color=color,
                             marker_line=dict(color="white", width=2),
                             text=[f"{x:.0f}" if x > 0.08 * max(sum(estrategias[n].values()) for n in nombres)
                                   else "" for x in v],
                             textposition="inside", insidetextfont=dict(color="white"),
                             hovertemplate="%{y}<br>" + texto + ": %{x:.2f} M COP<extra></extra>"))
    for n in nombres:
        total = sum(estrategias[n].values())
        fig.add_annotation(y=n, x=total, text=f"<b>{total:.1f} M</b>", showarrow=False, xanchor="left", xshift=6)
    fig.update_xaxes(title="Costo (millones de COP)")
    return _estilo(fig, alto=140 + 60 * len(nombres), barmode="stack")


def fig_concentracion(p, C_nat, C_fin=None, titulo_plan="Con el plan"):
    """TPH inicial, sin tratamiento y con el plan frente al límite de cada zona."""
    x = np.arange(p.n)
    fig = go.Figure()
    for i in x:
        fin = C_fin[i] if C_fin is not None else C_nat[i]
        fig.add_shape(type="line", x0=i, x1=i, y0=fin, y1=p.C0[i], line=dict(color=GRID, width=4), layer="below")
        fig.add_shape(type="line", x0=i - 0.32, x1=i + 0.32, y0=p.Clim[i], y1=p.Clim[i],
                      line=dict(color=INK, width=2.5))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color=INK, width=2.5),
                             name="Límite legal"))
    fig.add_trace(go.Scatter(x=x, y=p.C0, mode="markers", name="Inicial",
                             marker=dict(size=13, color="white", line=dict(color=MUTED, width=2.5)),
                             hovertemplate="%{text}<br>Inicial: %{y:,.0f} mg/kg<extra></extra>", text=p.nombres))
    fig.add_trace(go.Scatter(x=x + (0.12 if C_fin is not None else 0), y=C_nat, mode="markers",
                             name=f"Sin tratamiento ({p.esc.t_trat:g} días)",
                             marker=dict(size=11, symbol="diamond", color=TERRA),
                             hovertemplate="%{text}<br>Sin tratamiento: %{y:,.0f} mg/kg<extra></extra>",
                             text=p.nombres))
    if C_fin is not None:
        fig.add_trace(go.Scatter(x=x, y=C_fin, mode="markers", name=f"{titulo_plan} ({p.esc.t_trat:g} días)",
                                 marker=dict(size=14, color=TEAL, line=dict(color="white", width=2)),
                                 hovertemplate="%{text}<br>Con el plan: %{y:,.0f} mg/kg<extra></extra>",
                                 text=p.nombres))
    fig.update_xaxes(tickvals=x, ticktext=p.nombres, range=[-0.6, p.n - 0.4])
    fig.update_yaxes(title="TPH (mg/kg)", rangemode="tozero")
    return _estilo(fig, alto=400)


def fig_factores(p, f):
    """Mapa de calor de los factores de k (1 = sin limitación)."""
    claves = list(NOMBRES_FACTORES)
    z = np.array([f[c] for c in claves])
    fig = go.Figure(go.Heatmap(
        z=z, x=p.nombres, y=[NOMBRES_FACTORES[c] for c in claves], zmin=0, zmax=1,
        colorscale=[[0, "#F6EFE4"], [1, TEAL]], text=np.round(z, 2), texttemplate="%{text}",
        xgap=2, ygap=2, colorbar=dict(title="1 = ideal", thickness=12),
        hovertemplate="%{x} · %{y}: %{z:.2f}<extra></extra>"))
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(gridcolor="rgba(0,0,0,0)")
    return _estilo(fig, alto=360)


def fig_tornado(df, columna, titulo, unidad):
    """Gráfico tornado: cambio de `columna` frente al caso base para −δ y +δ."""
    base = df.loc[df["parametro"] == "base", columna].iloc[0]
    var = df[df["parametro"] != "base"]
    etiquetas = list(dict.fromkeys(var["etiqueta"]))
    # ordenar por el tamaño del efecto (el mayor arriba)
    efecto = {e: np.nanmax(np.abs(var.loc[var["etiqueta"] == e, columna] - base)) if
              var.loc[var["etiqueta"] == e, columna].notna().any() else 0 for e in etiquetas}
    etiquetas = sorted(etiquetas, key=lambda e: efecto[e])
    fig = go.Figure()
    for signo, color, nombre in ((-1, VIOLET, "Parámetro −"), (1, TEAL, "Parámetro +")):
        filas = [var[(var["etiqueta"] == e) & (np.sign(var["variacion"]) == signo)].iloc[0] for e in etiquetas]
        delta = [r[columna] - base for r in filas]
        texto = ["infactible" if np.isnan(d) else f"{d:+.1f}" for d in delta]
        fig.add_trace(go.Bar(y=etiquetas, x=[0 if np.isnan(d) else d for d in delta], orientation="h",
                             name=f"{nombre}{abs(filas[0]['variacion']):.0%}", marker_color=color,
                             text=texto, textposition="outside",
                             hovertemplate="%{y}<br>Cambio: %{x:+.2f} " + unidad + "<extra></extra>"))
    fig.add_vline(x=0, line_color=INK, line_width=1.5)
    fig.update_xaxes(title=f"Cambio frente al caso base ({base:.1f} {unidad})")
    fig.update_layout(title=dict(text=titulo, font=dict(size=14)))
    return _estilo(fig, alto=120 + 70 * len(etiquetas), barmode="group", margin=dict(l=10, r=40, t=70, b=10))
