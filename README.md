# AndesMercado — Pipeline de Validación de Datos DevOps

![CI](https://github.com/JSMT04/CS_AndesMercado/actions/workflows/ci.yml/badge.svg)

## Descripción

Pipeline de **validación de calidad de datos** que aplica cinco reglas automatizadas
sobre el archivo `ventas.csv` antes de permitir su carga al Data Warehouse.
El sistema bloquea automáticamente archivos con errores de escala, canales inválidos,
identificadores duplicados o anomalías estadísticas — exactamente el tipo de fallo
que causó el incidente del Black Friday 2025 en AndesMercado.

> Proyecto académico — Estudio de caso DevOps en la arquitectura de datos.  
> Universidad EAN.

---

## Estructura del Proyecto

```
Case_Study_AndesMercado/
├── .github/
│   └── workflows/
│       └── ci.yml              # Pipeline CI/CD (GitHub Actions)
├── data/
│   └── ventas.csv              # Datos de ventas (incluye incidente 28-Nov-2025)
├── tests/
│   ├── __init__.py
│   └── test_etl.py             # Suite de pruebas pytest (9 casos)
├── validar_ventas.py           # Módulo principal de validación (R1–R5)
├── requirements.txt
├── .gitignore
├── INFORME.md                  # Informe técnico del caso
└── README.md
```

---

## Requisitos

- **Python 3.10+**
- **pip**

---

## Instalación

```bash
pip install -r requirements.txt
```

---

## Ejecución de Validaciones

```bash
python validar_ventas.py data/ventas.csv
```

El script termina con **exit code 1** si detecta errores (carga bloqueada) o
**exit code 0** si los datos son válidos.

---

## Ejecución de Pruebas

```bash
python -m pytest tests/ -v
```

---

## Reglas de Validación

| Regla | Nombre | Descripción | Qué detecta |
|-------|--------|-------------|-------------|
| **R1** | Columnas esperadas | Verifica que el CSV tenga exactamente `{id_venta, fecha, canal, monto}` | Esquemas cambiados, columnas faltantes o extras |
| **R2** | Integridad de ID | `id_venta` sin nulos y sin duplicados | Registros repetidos o corruptos |
| **R3** | Canal válido | `canal` ∈ `{tienda, en_linea}` | Fuentes de datos desconocidas |
| **R4** | Monto máximo | Ningún monto individual supera **COP 5 000 000** | Errores de escala (centavos en lugar de pesos) |
| **R5** | Anomalía diaria | Total diario por canal no supera **3×** el promedio de días previos | Picos estadísticos por error de ingesta o fraude |

---

## Resultados sobre el Incidente Black Friday

El 28 de noviembre de 2025, el equipo de e-commerce cambió la columna `monto`
a **centavos** sin notificar al equipo de datos.  El script nocturno cargó los
valores 100× inflados al Data Warehouse, lo que llevó a la gerencia a aprobar
una compra de inventario por **COP 850 millones**.

**Las reglas R4 y R5 habrían bloqueado la carga antes de llegar al tablero:**

- **R4 falla**: los ids `1012` ($18.99 M), `1013` ($45.99 M) y `1014` ($8.99 M)
  superan el límite de COP 5 000 000.
- **R5 falla**: el total de `en_linea` el 28-Nov fue de $73 970 050 versus un
  promedio previo de $473 667 — un **ratio de 156.16×** (umbral: 3×).

> **El error NO habría llegado al tablero de Power BI.**

---

## CI/CD

GitHub Actions ejecuta el pipeline en cada `push` o `pull request`:

1. **Pruebas unitarias** (`python -m pytest tests/ -v`) — deben pasar en verde.
2. **Validación del CSV** (`python validar_ventas.py data/ventas.csv`) — detecta
   el incidente y registra el error en el log del step (configurado con
   `continue-on-error: true` para que el CI general siga verde y la evidencia
   quede visible en el log).

Consulta el workflow en [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
