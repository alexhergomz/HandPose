#!/usr/bin/env python3
"""
Genera un tablero ChArUco listo para imprimir (A4) para calibrar las camaras.
Uso:  python generar_charuco.py   ->  docs/charuco_board.png
"""
import os

import cv2
import numpy as np

SQUARES_X = 5          # casillas horizontales
SQUARES_Y = 7          # casillas verticales
SQUARE_LEN = 0.035     # lado de casilla en METROS (mide el impreso y ajusta esto)
MARKER_LEN = 0.026     # lado del marcador ArUco en metros (~0.75 del cuadro)
DICT = cv2.aruco.DICT_5X5_100

dictionary = cv2.aruco.getPredefinedDictionary(DICT)
board = cv2.aruco.CharucoBoard((SQUARES_X, SQUARES_Y), SQUARE_LEN, MARKER_LEN, dictionary)

# ~300 DPI sobre A4 (210x297mm) con margen
img = board.generateImage((1764, 2480), marginSize=40, borderBits=1)
os.makedirs("docs", exist_ok=True)
cv2.imwrite("docs/charuco_board.png", img)
print("Escrito docs/charuco_board.png")
print(f"Config: {SQUARES_X}x{SQUARES_Y} casillas, cuadro={SQUARE_LEN*1000:.0f}mm, "
      f"marcador={MARKER_LEN*1000:.0f}mm, dict=DICT_5X5_100")
print("IMPORTANTE: tras imprimir, mide un cuadro real con regla y corrige SQUARE_LEN.")
