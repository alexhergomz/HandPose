#!/usr/bin/env python3
"""Genera diagramas vectoriales (SVG) para el tutorial de calibracion."""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Wedge, Circle, Rectangle, Polygon, PathPatch
from matplotlib.path import Path
import matplotlib.font_manager as fm

plt.rcParams["font.family"] = "DejaVu Sans"

INK   = "#1d3557"
TEAL  = "#2a9d8f"
ORANGE= "#e76f51"
RED   = "#e63946"
GOLD  = "#e9c46a"
GRAY  = "#8d99ae"
LIGHT = "#eef2f5"
WHITE = "#ffffff"


def save(fig, name):
    os.makedirs(os.path.dirname(name), exist_ok=True)
    fig.savefig(name, format="svg", bbox_inches="tight", transparent=True)
    fig.savefig(name.replace(".svg", ".png"), format="png", bbox_inches="tight",
                dpi=130, facecolor="white")
    plt.close(fig)
    print("->", name)


def rbox(ax, x, y, w, h, fc, ec=None, lw=1.5, rad=0.06, alpha=1.0, z=2):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.0,rounding_size={rad}",
                       fc=fc, ec=ec or fc, lw=lw, alpha=alpha, zorder=z, mutation_aspect=1)
    ax.add_patch(p)
    return p


def arrow(ax, p0, p1, color=INK, lw=2.2, style="-|>", mut=18, z=3, conn="arc3,rad=0"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=mut,
                 lw=lw, color=color, zorder=z, connectionstyle=conn,
                 shrinkA=2, shrinkB=2))


def camera(ax, x, y, ang_deg, scale=1.0, color=INK, fov=42, reach=2.6,
           fov_color=None, label=None, see=True):
    """Dibuja una camara (vista superior) apuntando a ang_deg, con su cono FOV."""
    a = np.radians(ang_deg)
    # cono FOV
    if fov_color:
        ax.add_patch(Wedge((x, y), reach, ang_deg - fov/2, ang_deg + fov/2,
                     fc=fov_color, ec="none", alpha=0.22 if see else 0.10, zorder=1))
        ax.add_patch(Wedge((x, y), reach, ang_deg - fov/2, ang_deg + fov/2,
                     fc="none", ec=fov_color, lw=1.0, alpha=0.5 if see else 0.25, zorder=1))
    # cuerpo
    bw, bh = 0.5*scale, 0.34*scale
    perp = a + np.pi/2
    dx, dy = np.cos(a), np.sin(a)
    px, py = np.cos(perp), np.sin(perp)
    cx, cy = x - dx*0.12*scale, y - dy*0.12*scale
    corners = [(cx+px*bh/2-dx*bw/2, cy+py*bh/2-dy*bw/2),
               (cx-px*bh/2-dx*bw/2, cy-py*bh/2-dy*bw/2),
               (cx-px*bh/2+dx*bw/2, cy-py*bh/2+dy*bw/2),
               (cx+px*bh/2+dx*bw/2, cy+py*bh/2+dy*bw/2)]
    ax.add_patch(Polygon(corners, closed=True, fc=color, ec="none", zorder=4))
    # lente
    ax.add_patch(Polygon([(cx+dx*bw/2+px*bh/2.6, cy+dy*bw/2+py*bh/2.6),
                          (cx+dx*bw/2-px*bh/2.6, cy+dy*bw/2-py*bh/2.6),
                          (cx+dx*(bw/2+0.18*scale)-px*bh/4, cy+dy*(bw/2+0.18*scale)-py*bh/4),
                          (cx+dx*(bw/2+0.18*scale)+px*bh/4, cy+dy*(bw/2+0.18*scale)+py*bh/4)],
                 closed=True, fc=color, ec="none", zorder=4))
    if label:
        ax.text(x - dx*0.82*scale, y - dy*0.82*scale, label, ha="center", va="center",
                fontsize=10.5, color=color, fontweight="bold")


def board(ax, x, y, w, h, ang=0, n=4, m=3, front_color=TEAL, show_front=True):
    """Tablero ChArUco esquematico (vista superior = una linea con caras)."""
    a = np.radians(ang)
    dx, dy = np.cos(a), np.sin(a)
    px, py = -np.sin(a), np.cos(a)
    # cara frontal (linea gruesa de color)
    ax.plot([x-dx*w/2, x+dx*w/2], [y-dy*w/2, y+dy*w/2], color=INK, lw=5, zorder=5,
            solid_capstyle="round")
    if show_front:
        off = 0.12
        ax.plot([x-dx*w/2+px*off, x+dx*w/2+px*off],
                [y-dy*w/2+py*off, y+dy*w/2+py*off], color=front_color, lw=3, zorder=5,
                solid_capstyle="round")


# ---------------------------------------------------------------- D1: pipeline
def d1_pipeline():
    fig, ax = plt.subplots(figsize=(12.6, 3.0))
    ax.set_xlim(0, 12.6); ax.set_ylim(0, 3.0); ax.axis("off")
    steps = [
        ("1", "Imprimir\ntablero", "ChArUco en papel,\npegado plano", TEAL),
        ("2", "Grabar el\n“oleaje”", "Mover el tablero\nante 2 cámaras", ORANGE),
        ("3", "Calcular la\ncalibración", "Intrínsecos +\nextrínsecos", INK),
        ("4", "Triangular", "Unir las 2 vistas\npor geometría", GOLD),
        ("5", "Mano 3D\nmétrica", "Profundidad real\nen milímetros", RED),
    ]
    n = len(steps); w = 2.05; gap = (12.6 - n*w) / (n-1) if n > 1 else 0
    xs = []
    for i, (num, title, sub, col) in enumerate(steps):
        x = i*(w+gap); xs.append(x)
        rbox(ax, x, 0.55, w, 1.9, fc=LIGHT, ec=col, lw=2.2, rad=0.12)
        ax.add_patch(Circle((x+0.42, 2.05), 0.26, fc=col, ec="none", zorder=3))
        ax.text(x+0.42, 2.05, num, ha="center", va="center", color="white",
                fontsize=14, fontweight="bold", zorder=4)
        ax.text(x+w/2+0.18, 1.72, title, ha="center", va="center", color=INK,
                fontsize=11.5, fontweight="bold")
        ax.text(x+w/2, 0.98, sub, ha="center", va="center", color=GRAY, fontsize=8.8)
    for i in range(n-1):
        arrow(ax, (xs[i]+w+0.02, 1.5), (xs[i+1]-0.02, 1.5), color=GRAY, lw=2.4, mut=16)
    save(fig, "docs/diagrams/d1_pipeline.svg")


# ----------------------------------------------------------- D2: angulo camaras
def d2_angle():
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.9))
    for ax in axes:
        ax.set_xlim(-4.3, 4.3); ax.set_ylim(-1.2, 4.7); ax.axis("off"); ax.set_aspect("equal")

    # --- BIEN: ~80 grados ---
    ax = axes[0]
    obj = (0, 1.7)
    camera(ax, -2.4, 0.0, 58, color=INK, fov=40, reach=3.7, fov_color=TEAL, label="Cámara A")
    camera(ax,  2.4, 0.0, 122, color=INK, fov=40, reach=3.7, fov_color=ORANGE, label="Cámara B")
    board(ax, obj[0], obj[1], 1.4, 0.2, ang=0, front_color=TEAL)
    ax.text(obj[0], obj[1]+0.45, "zona de agarre", ha="center", color=INK, fontsize=9.5,
            fontweight="bold")
    ax.text(0, 2.92, "ambas ven el frente\ndel tablero → sí calibra", ha="center",
            color=TEAL, fontsize=10, fontweight="bold")
    # arco de angulo
    ax.add_patch(Wedge(obj, 0.7, 238, 302, fc="none", ec=GRAY, lw=1.3))
    ax.text(0, 0.78, "~70–90°", ha="center", color=GRAY, fontsize=10, fontweight="bold")
    ax.plot([obj[0], -2.4],[obj[1],0.05], color=GRAY, lw=0.8, ls=":", zorder=0)
    ax.plot([obj[0], 2.4],[obj[1],0.05], color=GRAY, lw=0.8, ls=":", zorder=0)
    ax.text(0, 4.45, "BIEN", ha="center", color=TEAL, fontsize=16, fontweight="bold")

    # --- MAL: ~180 grados ---
    ax = axes[1]
    obj = (0, 1.7)
    camera(ax, -3.0, 1.7, 0, color=INK, fov=34, reach=3.4, fov_color=TEAL)
    camera(ax,  3.0, 1.7, 180, color=GRAY, fov=34, reach=3.4, fov_color=RED, see=False)
    ax.text(-3.0, 0.92, "Cámara A", ha="center", color=INK, fontsize=10.5, fontweight="bold")
    ax.text( 3.0, 0.92, "Cámara B", ha="center", color=GRAY, fontsize=10.5, fontweight="bold")
    board(ax, obj[0], obj[1], 0.2, 1.4, ang=90, front_color=TEAL)
    ax.text(-0.32, 1.7, "frente", ha="center", va="center", color=TEAL, fontsize=8.5, rotation=90)
    ax.text(0.34, 1.7, "dorso", ha="center", va="center", color=RED, fontsize=8.5, rotation=90)
    ax.text(2.8, 0.55, "ve el dorso\n(sin marcadores)", ha="center", color=RED, fontsize=9)
    ax.text(0, 4.45, "MAL  (~180° opuestas)", ha="center", color=RED, fontsize=16, fontweight="bold")
    ax.text(0, 3.35, "solo una detecta el tablero\n→ no hay extrínsecos", ha="center",
            color=RED, fontsize=10, fontweight="bold")
    save(fig, "docs/diagrams/d2_angulo.svg")


# -------------------------------------------------- D3: intrinsecos vs extrinsecos
def d3_intr_extr():
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.4))
    for ax in axes:
        ax.axis("off"); ax.set_aspect("equal")

    # Intrinsecos: rejilla con distorsion de barril
    ax = axes[0]; ax.set_xlim(0, 6); ax.set_ylim(-0.4, 5.4)
    ax.text(3, 5.1, "INTRÍNSECOS", ha="center", color=TEAL, fontsize=14, fontweight="bold")
    ax.text(3, 4.62, "propiedades de cada lente", ha="center", color=GRAY, fontsize=9.5)
    cx, cy, R = 3.0, 2.3, 1.7
    def barrel(px, py):
        dx, dy = px-cx, py-cy; r = np.hypot(dx, dy)
        k = 1 + 0.10*(r/R)**2
        return cx+dx*k, cy+dy*k
    gv = np.linspace(-1, 1, 7)
    for gx in gv:
        pts = [barrel(cx+gx*R, cy+t*R) for t in np.linspace(-1,1,40)]
        ax.plot(*zip(*pts), color=ORANGE, lw=1.1, alpha=0.8)
    for gy in gv:
        pts = [barrel(cx+t*R, cy+gy*R) for t in np.linspace(-1,1,40)]
        ax.plot(*zip(*pts), color=ORANGE, lw=1.1, alpha=0.8)
    ax.add_patch(Circle((cx, cy), 0.08, fc=INK, ec="none", zorder=5))
    ax.annotate("centro óptico", (cx, cy), (cx+0.2, cy-0.1), fontsize=8.5, color=INK)
    ax.text(cx, 0.15, "distorsión del lente\n(peor en las esquinas)", ha="center",
            color=INK, fontsize=9.5, fontweight="bold")

    # Extrinsecos: dos camaras + R,T
    ax = axes[1]; ax.set_xlim(0, 6); ax.set_ylim(-0.4, 5.4)
    ax.text(3, 5.1, "EXTRÍNSECOS", ha="center", color=ORANGE, fontsize=14, fontweight="bold")
    ax.text(3, 4.62, "posición de una cámara respecto a la otra", ha="center",
            color=GRAY, fontsize=9.0)
    camera(ax, 1.2, 1.4, 35, color=INK, scale=1.4, label="A")
    camera(ax, 4.8, 1.4, 145, color=INK, scale=1.4, label="B")
    arrow(ax, (1.65, 1.85), (4.35, 1.85), color=ORANGE, lw=2.4, mut=18, conn="arc3,rad=-0.25")
    ax.text(3.0, 2.95, "R, T", ha="center", color=ORANGE, fontsize=13, fontweight="bold")
    ax.text(3.0, 2.5, "rotación + traslación", ha="center", color=GRAY, fontsize=9)
    board(ax, 3.0, 3.7, 1.5, 0.2, front_color=TEAL)
    ax.text(3.0, 4.05, "tablero visible por\nLAS DOS a la vez", ha="center", color=INK, fontsize=9)
    save(fig, "docs/diagrams/d3_intr_extr.svg")


# ------------------------------------------------------------- D4: tecnica oleaje
def d4_oleaje():
    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    ax.set_xlim(0, 11.5); ax.set_ylim(0, 5.2); ax.axis("off")
    # marco de la imagen de la camara
    fx, fy, fw, fh = 0.4, 0.5, 7.4, 4.4
    ax.add_patch(Rectangle((fx, fy), fw, fh, fc="#fbfcfd", ec=INK, lw=2.0))
    ax.text(fx+fw/2, fy+fh+0.18, "lo que ve UNA cámara", ha="center", color=INK,
            fontsize=10.5, fontweight="bold")

    def mini_board(cx, cy, s, ang=0, color=TEAL):
        a = np.radians(ang)
        for i in range(4):
            for j in range(3):
                if (i+j) % 2 == 0:
                    x0 = (i-2)*s; y0 = (j-1.5)*s
                    pts = [(x0, y0),(x0+s,y0),(x0+s,y0+s),(x0,y0+s)]
                    R = np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]])
                    pts = [(cx+R@np.array(p))[0:2] for p in [np.array(p) for p in pts]]
                    pts = [tuple((R@np.array([px,py]))+[cx,cy]) for px,py in [(x0,y0),(x0+s,y0),(x0+s,y0+s),(x0,y0+s)]]
                    ax.add_patch(Polygon(pts, closed=True, fc=INK, ec="none", zorder=3))
        # borde
        c = [(-2*s,-1.5*s),(2*s,-1.5*s),(2*s,1.5*s),(-2*s,1.5*s)]
        R = np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]])
        c = [tuple((R@np.array(p))+[cx,cy]) for p in c]
        ax.add_patch(Polygon(c, closed=True, fc="none", ec=color, lw=2.2, zorder=3))

    s = 0.26
    poses = [(1.5,3.9,0),(6.6,3.9,18),(1.5,1.4,-15),(6.6,1.4,12),(4.05,2.65,0)]
    for (cx,cy,ang) in poses:
        mini_board(cx, cy, s, ang)
    # flechas tenues entre poses (orden de recorrido)
    order = [(1.5,3.9),(4.05,2.65),(6.6,3.9),(6.6,1.4),(4.05,2.65),(1.5,1.4)]
    for p0,p1 in zip(order, order[1:]):
        arrow(ax, p0, p1, color=GRAY, lw=1.2, mut=11, style="-|>", conn="arc3,rad=0.2", z=2)

    # panel lateral de reglas
    px = 8.2
    rbox(ax, px, 0.5, 3.0, 4.4, fc=LIGHT, ec=INK, lw=1.6, rad=0.10)
    ax.text(px+1.5, 4.55, "Cómo moverlo", ha="center", color=INK, fontsize=11.5, fontweight="bold")
    tips = [(TEAL,"Despacio,\ncon pausas"),
            (ORANGE,"Cubre las\nESQUINAS"),
            (INK,"Inclínalo en\nvarios ángulos"),
            (GOLD,"Cerca y\nlejos")]
    for k,(col,txt) in enumerate(tips):
        yy = 3.85 - k*0.86
        ax.add_patch(Circle((px+0.42, yy), 0.16, fc=col, ec="none"))
        ax.text(px+0.78, yy, txt, ha="left", va="center", color=INK, fontsize=9.6)
    save(fig, "docs/diagrams/d4_oleaje.svg")


# ------------------------------------------------------------ D5: triangulacion
def d5_triangulacion():
    fig, ax = plt.subplots(figsize=(11.0, 5.2))
    ax.set_xlim(0, 11); ax.set_ylim(0, 5.2); ax.axis("off"); ax.set_aspect("equal")
    C1 = (1.3, 1.0); C2 = (9.7, 1.0); P = (5.5, 4.2)
    # rayos
    for C, col in [(C1, TEAL), (C2, ORANGE)]:
        ax.plot([C[0], P[0]+(P[0]-C[0])*0.05], [C[1], P[1]+(P[1]-C[1])*0.05],
                color=col, lw=2.4, zorder=2)
    # planos de imagen
    for C, col, ang in [(C1, TEAL, 58), (C2, ORANGE, 122)]:
        a = np.radians(ang); dx, dy = np.cos(a), np.sin(a); px, py = -dy, dx
        mx, my = C[0]+dx*1.6, C[1]+dy*1.6
        ax.plot([mx-px*0.7, mx+px*0.7],[my-py*0.7, my+py*0.7], color=col, lw=4,
                solid_capstyle="round", zorder=3)
        # punto proyectado
        t = 1.6
        ax.add_patch(Circle((C[0]+dx*t, C[1]+dy*t), 0.10, fc=col, ec="white", lw=1, zorder=5))
    camera(ax, *C1, 58, color=INK, scale=1.3, label="Cámara A")
    camera(ax, *C2, 122, color=INK, scale=1.3, label="Cámara B")
    # punto 3D
    ax.add_patch(Circle(P, 0.17, fc=RED, ec="white", lw=2, zorder=6))
    ax.text(P[0], P[1]+0.5, "yema del dedo", ha="center", color=RED, fontsize=10.5, fontweight="bold")
    ax.text(P[0], P[1]-0.55, "punto 3D (mm)", ha="center", color=INK, fontsize=9.5)
    ax.text(5.5, 0.35, "un punto visto por las 2 cámaras  →  su posición 3D real",
            ha="center", color=INK, fontsize=11.5, fontweight="bold")
    save(fig, "docs/diagrams/d5_triangulacion.svg")


if __name__ == "__main__":
    import os
    os.makedirs("diagrams", exist_ok=True)
    d1_pipeline(); d2_angle(); d3_intr_extr(); d4_oleaje(); d5_triangulacion()
    print("listo")
