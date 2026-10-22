import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
BG, INK, MUTED, GRID = "#F5EAD8", "#201E1D", "#6B635A", "#D9CBB4"
TEAL, TERRA, VIOLET, OCHRE = "#008C80", "#BF5B2C", "#6250D6", "#C98500"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": INK})
D = json.load(open("../modelo/resultados_detalle.json"))
S, ir = D["soluciones"], D["i_rodilla"]
idx = {"Costo mínimo": 0, "Punto rodilla": ir, "Máxima limpieza": len(S) - 1}

def base(ax):
    ax.set_facecolor(BG)
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]: ax.spines[s].set_color(GRID)

# 1. Frente actual
c = np.array([s["f2"] for s in S]); f = np.array([100 * s["f1"] for s in S])
fig, ax = plt.subplots(figsize=(11, 7.2), facecolor=BG); base(ax); ax.grid(color=GRID, lw=1, zorder=0)
ax.axvspan(0, c[0], color="#E3D3BA", zorder=0)
ax.text(c[0] / 2, 47, "No alcanza\npara cumplir\nla norma", ha="center", va="bottom", color=MUTED, fontsize=13)
ax.plot(c, f, "-o", color=TEAL, lw=2.2, ms=8, zorder=4)
for (nom, i), off in zip(idx.items(), [(14, -8), (16, -50), (-150, -60)]):
    ax.plot(c[i], f[i], "o", ms=20, mfc="none", mec=INK, mew=2, zorder=5)
    ax.annotate(f"{nom}\n{f[i]:.1f} % · {c[i]:.1f} M", (c[i], f[i]), xytext=off, textcoords="offset points", fontsize=14, va="center" if off[1] == -8 else "bottom")
ax.set_xlabel("Costo total f₂ (millones de COP)"); ax.set_ylabel("Contaminante eliminado f₁ (%)")
ax.set_xlim(0, 300); ax.set_ylim(45, 85)
fig.tight_layout(); fig.savefig("./pareto_actual.png", dpi=200, facecolor=BG)

# 2. Composición del costo
comp = [("Costo fijo (movilización y labranza)", "fijo", TEAL), ("Consorcio microbiano", "consorcio", TERRA),
        ("Nutrientes (N y P)", "nutrientes", VIOLET), ("Cal", "cal", OCHRE)]
fig, ax = plt.subplots(figsize=(16, 5.6), facecolor=BG); base(ax)
ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
ys = np.arange(3)[::-1]
for y, (nom, i) in zip(ys, idx.items()):
    left = 0
    for lab, key, col in comp:
        v = S[i]["costos"][key]
        ax.barh(y, v, left=left, height=0.56, color=col, edgecolor=BG, linewidth=2, zorder=3)
        if v > 12: ax.text(left + v / 2, y, f"{v:.0f}", ha="center", va="center", color="white", fontsize=14, fontweight="bold", zorder=4)
        left += v
    ax.text(left + 4, y, f"{left:.0f} M COP", va="center", fontsize=15, fontweight="bold")
ax.set_yticks(ys); ax.set_yticklabels([f"{n}\n({100*S[i]['f1']:.0f} % eliminado)" for n, i in idx.items()])
ax.set_xlim(0, 320); ax.set_xlabel("Costo total (millones de COP)"); ax.grid(axis="x", color=GRID, zorder=0)
h = [plt.Rectangle((0, 0), 1, 1, color=col) for _, _, col in comp]
ax.legend(h, [l for l, _, _ in comp], loc="upper center", bbox_to_anchor=(0.5, 1.17), ncol=4, frameon=False, fontsize=14)
fig.tight_layout(); fig.savefig("./costos_estrategias.png", dpi=200, facecolor=BG)

# 3. Concentración por zona (punto rodilla)
Z, C0, Cl = D["zonas"], np.array(D["C0"]), np.array(D["Clim"])
Cn, Ck = np.array(D["Cnat"]), np.array(S[ir]["C_final"])
fig, ax = plt.subplots(figsize=(16, 6.2), facecolor=BG); base(ax); ax.grid(axis="y", color=GRID, zorder=0)
xs = np.arange(len(Z))
for i in xs:
    ax.plot([i, i], [Ck[i], C0[i]], color=GRID, lw=3, zorder=2)
    ax.plot([i - 0.3, i + 0.3], [Cl[i], Cl[i]], color=INK, lw=2.5, zorder=3)
ax.plot(xs, C0, "o", ms=13, mfc=BG, mec=MUTED, mew=2.5, zorder=4, label="Inicial")
ax.plot(xs + 0.12, Cn, "D", ms=10, color=TERRA, zorder=4, label="Sin tratamiento (90 días)")
ax.plot(xs, Ck, "o", ms=14, color=TEAL, zorder=5, label="Punto rodilla (90 días)")
ax.plot([], [], color=INK, lw=2.5, label="Límite legal de la zona")
for i in xs:
    ax.text(i + 0.36, Cl[i], f"{Cl[i]/1000:.0f} mil", va="center", fontsize=12, color=MUTED)
ax.set_xticks(xs); ax.set_xticklabels(Z, fontsize=16)
ax.set_ylabel("TPH (mg/kg)"); ax.set_ylim(0, 32000); ax.set_xlim(-0.6, len(Z) - 0.2)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", " ")))
ax.legend(loc="upper right", frameon=False, fontsize=14, ncol=2)
fig.tight_layout(); fig.savefig("./zonas_rodilla.png", dpi=200, facecolor=BG)
print("ok")
