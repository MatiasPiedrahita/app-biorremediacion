import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

BG, INK, MUTED, GRID = "#F5EAD8", "#201E1D", "#6B635A", "#D9CBB4"
ANTES, AHORA, LIT = "#BF5B2C", "#008C80", "#CDBFA8"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": INK})

def intervalo(ax, y, a, b, color, hueco=False, lw=3):
    ax.plot([a, b], [y, y], color=color, lw=lw, solid_capstyle="round", zorder=3)
    for v in (a, b):
        ax.plot(v, y, "o", ms=11, mfc=BG if hueco else color, mec=color, mew=2.5, zorder=4)

def banda(ax, y, a, b):
    ax.barh(y, b - a, left=a, height=0.55, color=LIT, zorder=1)

def fmt_k(v, _):
    return f"{v:g}"

fig, axs = plt.subplots(1, 2, figsize=(17, 6.6), facecolor=BG)
for ax in axs:
    ax.set_facecolor(BG)
    for s in ["top", "right", "left"]: ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="x", color=GRID, lw=1, zorder=0)
    ax.tick_params(axis="y", length=0)

# ---------- Panel A: velocidad k (escala log) ----------
ax = axs[0]
filas = [  # (y, etiqueta, lit, antes, ahora)
    (3.2, "Con tratamiento", (0.019, 0.053), (0.035, 0.068), (0.025, 0.048)),
    (1.0, "Sin tratamiento\n(atenuación natural)", (0.00038, 0.033), (0.000025, 0.0142), (0.0006, 0.0042)),
]
for y, et, lit, an, ah in filas:
    banda(ax, y + 0.55, *lit)
    intervalo(ax, y, *an, ANTES, hueco=True)
    intervalo(ax, y - 0.55, *ah, AHORA)
ax.text(0.019, 3.75 + 0.42, "literatura 0.019–0.053", color=MUTED, fontsize=13)
ax.text(0.00038, 1.55 + 0.42, "literatura 0.0004–0.033 (mediana 0.005)", color=MUTED, fontsize=13)
ax.text(0.068 * 1.3, 3.2, "antes", color=ANTES, va="center", fontsize=13, fontweight="bold")
ax.text(0.048 * 1.3, 2.65, "ahora", color=AHORA, va="center", fontsize=13, fontweight="bold")
ax.text(0.0142 * 1.35, 1.0, "antes", color=ANTES, va="center", fontsize=13, fontweight="bold")
ax.text(0.0042 * 1.35, 0.45, "ahora", color=AHORA, va="center", fontsize=13, fontweight="bold")
ax.set_xscale("log"); ax.set_xlim(1.5e-5, 0.2)
ax.xaxis.set_major_formatter(FuncFormatter(fmt_k))
ax.set_yticks([3.2, 1.0]); ax.set_yticklabels([f[1] for f in filas])
ax.set_ylim(-0.1, 4.6)
ax.set_xlabel("Velocidad de degradación k (día⁻¹, escala logarítmica)")
ax.set_title("Velocidad de degradación", loc="left", fontsize=18, fontweight="bold", pad=14)

# ---------- Panel B: costo por m3 ----------
ax = axs[1]
lit = [(3.6, "Landfarming, Bolivia (2000)", 10, 14),
       (2.9, "Landfarming, EPA (1995)", 42, 84),
       (2.2, "Biopilas, Chile (2022)", 51, 310)]
for y, et, a, b in lit:
    ax.barh(y, b - a, left=a, height=0.45, color=LIT, zorder=1)
    ax.text(b + 5, y, et, va="center", color=MUTED, fontsize=13)
intervalo(ax, 1.2, 8.9, 23.3, ANTES, hueco=True)
intervalo(ax, 0.5, 28.2, 87.1, AHORA)
ax.text(23.3 + 10, 1.2, "antes: USD 9–23", color=ANTES, va="center", fontsize=13, fontweight="bold")
ax.text(87.1 + 10, 0.5, "ahora: USD 28–87", color=AHORA, va="center", fontsize=13, fontweight="bold")
ax.set_xlim(0, 330); ax.set_ylim(0, 4.1)
ax.set_yticks([2.9, 0.85]); ax.set_yticklabels(["Literatura", "Nuestro modelo"])
ax.set_xlabel("Costo total por m³ de suelo tratado (USD)")
ax.set_title("Costo del tratamiento", loc="left", fontsize=18, fontweight="bold", pad=14)

fig.tight_layout(w_pad=4)
fig.savefig("./validacion_rangos.png", dpi=200, facecolor=BG)

# ---------- Frente de Pareto: antes vs ahora ----------
antes_c = [28.66,31.78,34.90,38.02,41.14,44.27,47.39,50.51,53.63,56.75,59.88,63.00,66.12,69.24,72.37,75.49]
antes_f = [68.08,69.48,75.78,77.89,79.33,80.87,81.92,82.72,83.33,83.80,84.18,84.47,84.69,84.85,84.99,85.11]
df = pd.read_csv("../modelo/resultados_pareto.csv")
c, f = df["Costo (M COP)"].values, df["Limpieza (%)"].values
fig, ax = plt.subplots(figsize=(11, 7.2), facecolor=BG); ax.set_facecolor(BG)
for s in ["top", "right"]: ax.spines[s].set_visible(False)
for s in ["left", "bottom"]: ax.spines[s].set_color(GRID)
ax.grid(color=GRID, lw=1, zorder=0)
ax.plot(antes_c, antes_f, "-o", color=ANTES, lw=2, ms=8, mfc=BG, mew=2, zorder=3, label="Antes (datos sin validar)")
ax.plot(c, f, "-o", color=AHORA, lw=2, ms=8, zorder=4, label="Ahora (datos validados)")
i_rod = 3
ax.plot(c[i_rod], f[i_rod], "o", ms=20, mfc="none", mec=INK, mew=2, zorder=5)
ax.annotate(f"Punto rodilla\n{f[i_rod]:.1f} % · {c[i_rod]:.1f} M", (c[i_rod], f[i_rod]), xytext=(18, -52),
            textcoords="offset points", fontsize=14, color=INK)
ax.annotate(f"Costo mínimo\n{f[0]:.1f} % · {c[0]:.1f} M", (c[0], f[0]), xytext=(14, -6),
            textcoords="offset points", fontsize=14, color=INK, va="center")
ax.annotate(f"Máxima limpieza\n{f[-1]:.1f} % · {c[-1]:.1f} M", (c[-1], f[-1]), xytext=(-120, -62),
            textcoords="offset points", fontsize=14, color=INK)
ax.set_xlabel("Costo total f₂ (millones de COP)"); ax.set_ylabel("Contaminante eliminado f₁ (%)")
ax.set_xlim(0, 300); ax.set_ylim(45, 90)
ax.legend(loc="lower right", frameon=False, fontsize=14)
fig.tight_layout()
fig.savefig("./pareto_antes_ahora.png", dpi=200, facecolor=BG)
print("ok")
