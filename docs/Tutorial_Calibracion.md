# Tutorial: Calibración de dos cámaras para reconstrucción 3D de la mano

> Objetivo: pasar de la *estimación aproximada sin calibración* (la que ya tenemos,
> usando la palma como referencia) a **3D métrico real** por triangulación de las dos
> vistas. Con esto cada punto visto por ≥2 cámaras se reconstruye en milímetros.

---

## 0. Resumen en una frase

Imprimes un **tablero ChArUco**, grabas un video corto **moviéndolo despacio** delante
de las dos cámaras a la vez, y un programa (**Pose2Sim** o **Anipose**) calcula la
geometría de las cámaras. Después, los keypoints 2D de la mano que ya genera
`hand_pose.py` se **triangulan** a 3D métrico.

---

## 1. Lo que necesitas

| Elemento | Detalle |
|---|---|
| Tablero ChArUco | Generado con `generar_charuco.py` → `docs/charuco_board.png` (ya creado) |
| Impresora + cartón rígido | Imprimir el tablero y pegarlo plano (sin arrugas) |
| Regla | Para medir el lado real de un cuadro tras imprimir |
| Las 2 cámaras fijas | En trípode/soporte, **que no se muevan** durante todo el proceso |
| Software | `opencv`, y **Pose2Sim** *o* **Anipose** (recomendado) |

---

## 2. Conceptos clave (qué estás calibrando)

Calibrar = encontrar **tres cosas**:

1. **Intrínsecos** (de cada cámara por separado): distancia focal, centro óptico y
   **distorsión del lente**. La distorsión es peor en las **esquinas** de la imagen.
2. **Extrínsecos** (entre las dos cámaras): la **rotación y traslación** relativa de una
   cámara respecto a la otra. Esto solo se puede medir cuando **ambas cámaras ven el
   tablero al mismo tiempo**.
3. **Sincronización temporal**: saber qué fotograma de la cámara A corresponde al de la
   cámara B. Esto **ya lo tienes** con `sync_audio.py` (por audio).

---

## 3. Paso crítico de hardware: ángulo de las cámaras

> **Este es el cambio más importante y casi nadie lo menciona.**

Tus cámaras actuales están **casi opuestas** (~150–180°). Para calibrar por triangulación
necesitas que **ambas vean el tablero (y la mano) a la vez** → necesitan **campo de visión
compartido**.

- ✅ Coloca las cámaras a **~70–90° entre sí**, las dos apuntando a la zona del agarre.
- ✅ Que la **zona donde agarras la lata** quede dentro del campo común de las dos.
- ❌ Evita ~180° (opuestas): no hay forma de poner un tablero plano visible para ambas.

```
        cámara A
          \
           \   ~80°
            \
   [ mano/lata ] ------- cámara B
```

Si por algún motivo necesitas mantenerlas opuestas, **no podrás triangular bien**: en ese
caso quédate con el método actual (palma como referencia) o añade una tercera cámara
intermedia.

---

## 4. Paso 1 — Imprimir el tablero

```bash
conda activate handpose
python generar_charuco.py          # crea docs/charuco_board.png (A4, 5x7)
```

1. Imprime `docs/charuco_board.png` **a tamaño real (100%, sin "ajustar a página")**.
2. Pégalo **plano y rígido** sobre cartón pluma o cartón grueso. Sin ondas ni brillos.
3. **Mide con regla** el lado real de un cuadro negro (en metros). Si no son 35 mm,
   edita `SQUARE_LEN` en `generar_charuco.py` y vuelve a usar ese valor en el software de
   calibración. **La escala métrica depende de esta medida.**

---

## 5. Paso 2 — Grabar el video de calibración (la "técnica del oleaje")

Vas a grabar **un solo clip** con las dos cámaras corriendo, moviendo el tablero. Ese clip
sirve para intrínsecos **y** extrínsecos.

### Las 4 reglas que hacen que funcione

1. **Despacio, con pausas.** El movimiento rápido produce *desenfoque* y arruina la
   detección de esquinas. Piensa: *"mover → parar → mover"*, unas **20–40 poses** distintas.
2. **Cubre toda la imagen, sobre todo las ESQUINAS** de cada cámara (ahí está la distorsión).
3. **Inclina el tablero** en muchos ángulos: de frente, ladeado a izquierda/derecha/
   arriba/abajo, y variando **cerca y lejos**.
4. **Visible para AMBAS cámaras** el mayor tiempo posible (esto da los extrínsecos).

### Errores que matan la calibración

- ❌ Desenfoque por movimiento (la causa #1).
- ❌ Tablero muy pequeño/lejano: que ocupe **al menos 1/3** del cuadro.
- ❌ Reflejos/brillo o sobreexposición sobre el tablero.
- ❌ **Mover o reenfocar/zoom las cámaras** después de calibrar (¡quedan fijas!).

Duración típica: **30–60 segundos** por las dos cámaras a la vez.

---

## 6. Paso 3 — Sincronizar las dos cámaras

Igual que con los videos de agarre: una **palmada** fuerte al inicio sirve de marca de audio.

```bash
python sync_audio.py CALIB_camA.mp4 CALIB_camB.mp4 --json sync_calib.json
```

Si la confianza es alta (>5) están sincronizados. (Lo ideal es disparador hardware, pero el
audio basta.)

---

## 7. Paso 4 — Calcular la calibración (elige UNA opción)

### Opción A (recomendada): **Pose2Sim** — el más fácil y completo

[Pose2Sim](https://github.com/perfanalytics/pose2sim) está hecho para 3D markerless
multicámara: sincronización, triangulación y filtrado.

```bash
pip install pose2sim
```

> ⚠️ **Importante — Pose2Sim NO detecta ChArUco.** Su propia calibración
> (`calibration_type = 'calculate'`) busca un **tablero de ajedrez**, no un ChArUco:
> en su código no hay ninguna llamada a `cv2.aruco`. Los únicos valores válidos de
> `calibration_type` son `'calculate'` y `'convert'`.
> Para usar tu tablero ChArUco tienes dos caminos:
> 1. Calcular la calibración con una herramienta que **sí** hace ChArUco
>    ([Caliscope](https://github.com/mprib/caliscope), Anipose, u OpenCV con
>    `cv2.aruco.calibrateCameraCharuco`) y **importarla** en Pose2Sim con
>    `calibration_type = 'convert'` y `convert_from = 'caliscope'`.
> 2. Usar Anipose de principio a fin (Opción B), que sí calibra con ChArUco.

Estructura de carpetas que espera (resumen):

```
Proyecto/
├── calibration/        # Calib.toml ya calculado (importado con 'convert')
├── pose/
│   ├── cam1_json/      # keypoints 2D, un JSON por fotograma (estilo OpenPose)
│   └── cam2_json/
└── Config.toml
```

y luego:

```python
from Pose2Sim import Pose2Sim
Pose2Sim.triangulation()    # produce los 3D a partir de los keypoints 2D
```

> **Integración con lo que ya tienes — ya está automatizada.**
> `export_pose2sim.py` convierte los CSV de `hand_pose.py` al JSON estilo OpenPose
> que Pose2Sim triangula, y genera el `Config.toml` y la estructura de carpetas:
>
> ```bash
> python export_pose2sim.py --grasp Cilindrico   # -> pose2sim/Cilindrico/
> ```
>
> Dos detalles que resuelve por ti:
> - **Orden de keypoints:** el esqueleto `HAND_21` de Pose2Sim (`pose_model = 'HAND'`)
>   coincide **1:1** con los 21 landmarks de MediaPipe, así que los ids pasan tal cual.
> - **Alineación temporal:** Pose2Sim empareja las cámaras **por índice** (el archivo
>   N de cam1 se supone simultáneo al N de cam2). Como las dos cámaras van libres y a
>   distinto fps, el script **remuestrea** la vista secundaria sobre los fotogramas de
>   la primaria usando el desfase de `sync_audio.py`. Por eso no hace falta el paso
>   `[synchronization]` de Pose2Sim.

### Opción B: **Anipose**

[Anipose](https://anipose.readthedocs.io) (sobre DeepLabCut) también calibra con ChArUco,
triangula y hace *bundle adjustment* y filtrado temporal. Flujo similar: carpeta
`calibration/` con los videos del tablero → `anipose calibrate` → `anipose triangulate`.

### Opción C: **OpenCV a mano** (si quieres control total)

Esqueleto del cálculo (intrínsecos por cámara + estéreo):

```python
import cv2, numpy as np
dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_100)
board = cv2.aruco.CharucoBoard((5, 7), 0.035, 0.026, dictionary)  # usa TU square_size
# 1) Por cada cámara: detectar esquinas ChArUco en muchos frames -> cv2.aruco.calibrateCameraCharuco
#    -> obtienes K (matriz intrínseca) y dist (distorsión)
# 2) Con frames donde AMBAS ven el tablero -> cv2.stereoCalibrate (puntos 3D del tablero)
#    -> obtienes R, T entre las dos cámaras
# 3) Construyes las matrices de proyección P1, P2 y triangulas:
#    pts3d = cv2.triangulatePoints(P1, P2, pts2d_camA, pts2d_camB)
```

---

## 8. Paso 5 — Triangular la mano a 3D métrico

Con la calibración lista:

1. Grabas el agarre con las **dos** cámaras (rig fijo, mismo enfoque).
2. Sincronizas (`sync_audio.py`).
3. Corres `hand_pose.py` en cada vista → keypoints 2D.
4. Triangulas con Pose2Sim/Anipose/OpenCV → **un esqueleto 3D métrico real**.

Resultado: profundidad correcta en milímetros, sin la deriva del método "palma como
referencia", y se reconstruye **cualquier punto** visible en al menos 2 cámaras.

---

## 9. Checklist rápido

- [ ] Cámaras a ~70–90°, con zona de agarre en el campo común.
- [ ] Tablero impreso a tamaño real, plano y rígido.
- [ ] Lado de cuadro **medido con regla** y puesto en la config.
- [ ] Video de calibración: lento, con pausas, cubriendo esquinas, inclinado, cerca/lejos.
- [ ] Tablero visible para **ambas** cámaras buena parte del clip.
- [ ] Palmada de sincronía al inicio.
- [ ] **No mover ni reenfocar** las cámaras después.
- [ ] Mismo rig fijo para grabar los agarres.

---

## 10. ¿Y si no quiero calibrar todavía?

Lo que ya está montado (`fuse_views.py`, palma como objeto de calibración) te da una
estimación **decente** para forma del agarre, contactos y configuración de dedos
(residual mediano ~0,75 cm sobre una mano de 9,2 cm). La calibración real solo es
necesaria si quieres **precisión métrica sub-centimétrica**.

---

*Anexo: archivos del proyecto relevantes — `generar_charuco.py` (tablero),
`sync_audio.py` (sincronía por audio), `hand_pose.py` (keypoints 2D por vista),
`export_pose2sim.py` (exporta esos keypoints al formato de Pose2Sim),
`fuse_views.py` (fusión sin calibración).*
