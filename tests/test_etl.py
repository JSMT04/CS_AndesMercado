"""
tests/test_etl.py
=================
Suite de pruebas pytest para el módulo validar_ventas.
Cubre las cinco reglas de validación (R1–R5) con al menos 9 casos de prueba,
incluyendo el incidente real del Black Friday (28-Nov-2025).
"""

import pandas as pd
import pytest

from validar_ventas import (
    validar,
    regla_columnas,
    regla_id_venta,
    regla_canal,
    regla_monto_maximo,
    regla_anomalia_diaria,
)


# ---------------------------------------------------------------------------
# Fixture: DataFrame limpio (pasa todas las reglas)
# ---------------------------------------------------------------------------

@pytest.fixture
def df_valido() -> pd.DataFrame:
    """DataFrame de ventas sin ningún problema de calidad."""
    return pd.DataFrame(
        {
            "id_venta": [1, 2, 3, 4],
            "fecha": ["2025-11-25", "2025-11-25", "2025-11-26", "2025-11-26"],
            "canal": ["tienda", "en_linea", "tienda", "en_linea"],
            "monto": [100_000.0, 250_000.0, 150_000.0, 300_000.0],
        }
    )


# ---------------------------------------------------------------------------
# Fixture: DataFrame con datos reales del incidente (ventas.csv)
# ---------------------------------------------------------------------------

@pytest.fixture
def df_incidente() -> pd.DataFrame:
    """
    Datos reales del CSV del incidente Black Friday 2025.
    Los ids 1012, 1013, 1014 tienen montos en centavos (error de escala 100×).
    """
    return pd.DataFrame(
        {
            "id_venta": [
                1001, 1002, 1003, 1004,
                1005, 1006, 1007,
                1008, 1009, 1010,
                1011, 1012, 1013, 1014, 1015,
            ],
            "fecha": [
                "2025-11-25", "2025-11-25", "2025-11-25", "2025-11-25",
                "2025-11-26", "2025-11-26", "2025-11-26",
                "2025-11-27", "2025-11-27", "2025-11-27",
                "2025-11-28", "2025-11-28", "2025-11-28", "2025-11-28", "2025-11-28",
            ],
            "canal": [
                "tienda", "en_linea", "en_linea", "tienda",
                "en_linea", "tienda", "en_linea",
                "tienda", "en_linea", "en_linea",
                "tienda", "en_linea", "en_linea", "en_linea", "tienda",
            ],
            "monto": [
                125_000.00, 189_900.00, 89_900.50, 342_500.00,
                259_000.00, 98_000.00, 412_300.75,
                215_000.00, 149_900.00, 320_000.00,
                187_000.00, 18_990_000, 45_990_000, 8_990_050, 276_400.00,
            ],
        }
    )


# ---------------------------------------------------------------------------
# Caso 1: datos completamente válidos
# ---------------------------------------------------------------------------

def test_datos_validos(df_valido):
    """Un DataFrame limpio debe pasar todas las reglas sin errores."""
    errores = validar(df_valido)
    assert errores == [], f"Se esperaban 0 errores, se obtuvieron: {errores}"


# ---------------------------------------------------------------------------
# Casos R1 — Validación de columnas
# ---------------------------------------------------------------------------

def test_r1_columnas_faltantes():
    """R1 debe fallar cuando falta la columna 'monto'."""
    df = pd.DataFrame(
        {
            "id_venta": [1],
            "fecha": ["2025-11-25"],
            "canal": ["tienda"],
            # 'monto' está ausente
        }
    )
    errores = regla_columnas(df)
    assert any("monto" in e and "R1" in e for e in errores), (
        "Se esperaba error R1 por columna 'monto' faltante"
    )


def test_r1_columnas_extra():
    """R1 debe fallar cuando hay una columna extra 'region' no esperada."""
    df = pd.DataFrame(
        {
            "id_venta": [1],
            "fecha": ["2025-11-25"],
            "canal": ["tienda"],
            "monto": [100_000.0],
            "region": ["Bogotá"],   # columna extra
        }
    )
    errores = regla_columnas(df)
    assert any("region" in e and "R1" in e for e in errores), (
        "Se esperaba error R1 por columna 'region' inesperada"
    )


# ---------------------------------------------------------------------------
# Casos R2 — Validación de id_venta
# ---------------------------------------------------------------------------

def test_r2_id_nulos():
    """R2 debe fallar cuando id_venta contiene valores None."""
    df = pd.DataFrame(
        {
            "id_venta": [1, None, 3],
            "fecha": ["2025-11-25", "2025-11-25", "2025-11-25"],
            "canal": ["tienda", "en_linea", "tienda"],
            "monto": [100_000.0, 200_000.0, 150_000.0],
        }
    )
    errores = regla_id_venta(df)
    assert any("nulo" in e.lower() and "R2" in e for e in errores), (
        "Se esperaba error R2 por id_venta nulo"
    )


def test_r2_id_duplicados():
    """R2 debe fallar cuando id_venta tiene valores repetidos."""
    df = pd.DataFrame(
        {
            "id_venta": [1, 2, 2],   # 2 duplicado
            "fecha": ["2025-11-25", "2025-11-25", "2025-11-26"],
            "canal": ["tienda", "en_linea", "tienda"],
            "monto": [100_000.0, 200_000.0, 150_000.0],
        }
    )
    errores = regla_id_venta(df)
    assert any("duplicado" in e.lower() and "R2" in e for e in errores), (
        "Se esperaba error R2 por id_venta duplicado"
    )


# ---------------------------------------------------------------------------
# Caso R3 — Validación de canal
# ---------------------------------------------------------------------------

def test_r3_canal_invalido():
    """R3 debe fallar cuando el canal es 'web', que no está en la lista válida."""
    df = pd.DataFrame(
        {
            "id_venta": [1],
            "fecha": ["2025-11-25"],
            "canal": ["web"],   # canal inválido
            "monto": [100_000.0],
        }
    )
    errores = regla_canal(df)
    assert any("web" in e and "R3" in e for e in errores), (
        "Se esperaba error R3 por canal 'web' inválido"
    )


# ---------------------------------------------------------------------------
# Caso R4 — Validación de monto máximo
# ---------------------------------------------------------------------------

def test_r4_monto_excede_limite():
    """R4 debe fallar cuando un monto individual supera COP 5 000 000."""
    df = pd.DataFrame(
        {
            "id_venta": [1],
            "fecha": ["2025-11-25"],
            "canal": ["tienda"],
            "monto": [6_000_000.0],   # supera el límite
        }
    )
    errores = regla_monto_maximo(df)
    assert any("R4" in e for e in errores), (
        "Se esperaba error R4 por monto que excede COP 5 000 000"
    )


# ---------------------------------------------------------------------------
# Caso R5 — Validación de anomalía diaria
# ---------------------------------------------------------------------------

def test_r5_anomalia_diaria():
    """
    R5 debe fallar cuando el total de un día es más de 3× el promedio previo.
    Se simula un spike de 10× en el segundo día del canal 'en_linea'.
    """
    df = pd.DataFrame(
        {
            "id_venta": [1, 2, 3],
            "fecha": ["2025-11-25", "2025-11-25", "2025-11-26"],
            "canal": ["en_linea", "en_linea", "en_linea"],
            # Día 1: total = 200 000.  Día 2: total = 2 000 000 (10× > umbral 3×)
            "monto": [100_000.0, 100_000.0, 2_000_000.0],
        }
    )
    errores = regla_anomalia_diaria(df)
    assert any("R5" in e for e in errores), (
        "Se esperaba error R5 por anomalía de spike 10× en el día 2"
    )


# ---------------------------------------------------------------------------
# Caso 9: incidente real de noviembre (R4 Y R5 deben fallar)
# ---------------------------------------------------------------------------

def test_r4_y_r5_incidente_noviembre(df_incidente):
    """
    Con los datos reales del CSV del 28-Nov-2025 (incidente Black Friday),
    tanto R4 como R5 deben detectar el problema.

    - R4: ids 1012 ($18.99 M), 1013 ($45.99 M) y 1014 ($8.99 M) superan COP 5 M.
    - R5: en_linea el 28-Nov tiene ratio ≈ 156× el promedio de días anteriores.
    """
    errores = validar(df_incidente)

    errores_r4 = [e for e in errores if "R4" in e]
    errores_r5 = [e for e in errores if "R5" in e]

    assert errores_r4, "Se esperaba al menos un error R4 (montos > COP 5 M en el incidente)"
    assert errores_r5, "Se esperaba al menos un error R5 (anomalía diaria 156× en el incidente)"

    # Verificar que los IDs problemáticos aparecen en el mensaje R4
    mensaje_r4 = " ".join(errores_r4)
    assert "1012" in mensaje_r4 or "1013" in mensaje_r4 or "1014" in mensaje_r4, (
        "El error R4 debe mencionar alguno de los ids 1012, 1013 o 1014"
    )

    # Verificar que el canal en_linea aparece en R5
    mensaje_r5 = " ".join(errores_r5)
    assert "en_linea" in mensaje_r5, (
        "El error R5 debe mencionar el canal 'en_linea'"
    )
