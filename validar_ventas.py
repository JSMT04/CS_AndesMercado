"""
validar_ventas.py
=================
Módulo de validación de calidad de datos para el pipeline ETL de AndesMercado.
Aplica cinco reglas (R1–R5) sobre un DataFrame de ventas y retorna una lista
de mensajes de error.  Si se ejecuta directamente, lee el CSV indicado en
argv[1], imprime los errores y termina con exit code 1 cuando existen fallos.
"""

import sys
from typing import List

import pandas as pd


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
COLUMNAS_ESPERADAS: set = {"id_venta", "fecha", "canal", "monto"}
CANALES_VALIDOS: set = {"tienda", "en_linea"}
LIMITE_MONTO: float = 5_000_000.0   # COP
FACTOR_ANOMALIA: float = 3.0         # múltiplo sobre el promedio de días previos


# ---------------------------------------------------------------------------
# Reglas individuales
# ---------------------------------------------------------------------------

def regla_columnas(df: pd.DataFrame) -> List[str]:
    """
    R1 — Valida que el DataFrame contenga exactamente las columnas esperadas.

    Detecta tanto columnas faltantes como columnas extra o inesperadas.
    Los nombres de columna se normalizan quitando espacios antes de comparar.

    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame a evaluar.

    Retorna
    -------
    List[str]
        Lista con un mensaje de error descriptivo si la validación falla,
        o lista vacía si pasa.
    """
    presentes = set(df.columns)
    faltantes = COLUMNAS_ESPERADAS - presentes
    extras = presentes - COLUMNAS_ESPERADAS
    errores: List[str] = []
    if faltantes:
        errores.append(f"R1 — Columnas faltantes: {sorted(faltantes)}")
    if extras:
        errores.append(f"R1 — Columnas inesperadas: {sorted(extras)}")
    return errores


def regla_id_venta(df: pd.DataFrame) -> List[str]:
    """
    R2 — Valida que la columna id_venta no tenga nulos ni valores duplicados.

    La unicidad e integridad de la clave primaria es fundamental para evitar
    conteo doble de transacciones.

    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame a evaluar. Debe contener la columna 'id_venta'.

    Retorna
    -------
    List[str]
        Lista de mensajes de error; vacía si la regla se cumple.
    """
    if "id_venta" not in df.columns:
        return []  # R1 ya reportó esto
    errores: List[str] = []
    nulos = df["id_venta"].isna().sum()
    if nulos > 0:
        errores.append(f"R2 — id_venta tiene {nulos} valor(es) nulo(s).")
    duplicados = df["id_venta"].dropna().duplicated().sum()
    if duplicados > 0:
        ids_dup = df["id_venta"][df["id_venta"].duplicated(keep=False)].unique().tolist()
        errores.append(f"R2 — id_venta tiene {duplicados} duplicado(s): {ids_dup}")
    return errores


def regla_canal(df: pd.DataFrame) -> List[str]:
    """
    R3 — Valida que todos los valores de la columna canal sean válidos.

    Canales aceptados: 'tienda' y 'en_linea'.  Cualquier otro valor —
    incluyendo variantes de escritura — se reporta como error.

    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame a evaluar. Debe contener la columna 'canal'.

    Retorna
    -------
    List[str]
        Lista de mensajes de error; vacía si la regla se cumple.
    """
    if "canal" not in df.columns:
        return []
    invalidos = df[~df["canal"].isin(CANALES_VALIDOS)]["canal"].unique().tolist()
    if invalidos:
        return [f"R3 — Canales inválidos encontrados: {invalidos}"]
    return []


def regla_monto_maximo(df: pd.DataFrame) -> List[str]:
    """
    R4 — Valida que ningún monto individual supere el límite de COP 5 000 000.

    Montos superiores al límite indican probables errores de escala (p. ej.,
    datos ingresados en centavos en lugar de pesos).

    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame a evaluar. Debe contener las columnas 'id_venta' y 'monto'.

    Retorna
    -------
    List[str]
        Lista de mensajes de error; vacía si la regla se cumple.
    """
    if "monto" not in df.columns:
        return []
    exceden = df[df["monto"] > LIMITE_MONTO]
    if exceden.empty:
        return []
    detalle = exceden[["id_venta", "monto"]].to_dict(orient="records") if "id_venta" in df.columns else exceden["monto"].tolist()
    return [
        f"R4 — {len(exceden)} venta(s) superan COP {LIMITE_MONTO:,.0f}: {detalle}"
    ]


def regla_anomalia_diaria(df: pd.DataFrame) -> List[str]:
    """
    R5 — Detecta anomalías en el total diario de ventas por canal.

    Para cada canal calcula el total de ventas por día y compara cada día
    contra el promedio de los días anteriores en ese canal.  Si el total
    de un día supera FACTOR_ANOMALIA × el promedio previo, se reporta como
    anomalía estadística.

    Se omiten los días sin historial previo (primer día de cada canal).

    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame a evaluar. Debe contener 'fecha', 'canal' y 'monto'.

    Retorna
    -------
    List[str]
        Lista de mensajes de error; vacía si la regla se cumple.
    """
    if not {"fecha", "canal", "monto"}.issubset(df.columns):
        return []

    errores: List[str] = []
    df_tmp = df.copy()
    df_tmp["fecha"] = pd.to_datetime(df_tmp["fecha"], errors="coerce")

    daily = (
        df_tmp.groupby(["canal", "fecha"])["monto"]
        .sum()
        .reset_index()
        .sort_values(["canal", "fecha"])
    )

    for canal, grupo in daily.groupby("canal"):
        grupo = grupo.reset_index(drop=True)
        for i in range(1, len(grupo)):
            promedio_previo = grupo.loc[:i - 1, "monto"].mean()
            if promedio_previo == 0:
                continue
            total_hoy = grupo.loc[i, "monto"]
            ratio = total_hoy / promedio_previo
            if ratio > FACTOR_ANOMALIA:
                fecha_str = grupo.loc[i, "fecha"].strftime("%Y-%m-%d")
                errores.append(
                    f"R5 — Anomalía en canal '{canal}' el {fecha_str}: "
                    f"total={total_hoy:,.2f}, promedio_prev={promedio_previo:,.2f}, "
                    f"ratio={ratio:.2f}x (umbral={FACTOR_ANOMALIA}x)"
                )
    return errores


# ---------------------------------------------------------------------------
# Función principal de validación
# ---------------------------------------------------------------------------

def validar(df: pd.DataFrame) -> List[str]:
    """
    Ejecuta todas las reglas de validación (R1–R5) sobre el DataFrame dado.

    Normaliza los nombres de columna quitando espacios en blanco antes de
    aplicar las reglas.

    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame con los datos de ventas a validar.

    Retorna
    -------
    List[str]
        Lista acumulada de mensajes de error de todas las reglas.
        Lista vacía indica que el DataFrame superó todas las validaciones.
    """
    # Normalizar nombres de columna
    df = df.copy()
    df.columns = df.columns.str.strip()

    errores: List[str] = []
    errores.extend(regla_columnas(df))
    errores.extend(regla_id_venta(df))
    errores.extend(regla_canal(df))
    errores.extend(regla_monto_maximo(df))
    errores.extend(regla_anomalia_diaria(df))
    return errores


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python validar_ventas.py <ruta_al_csv>")
        sys.exit(2)

    ruta_csv = sys.argv[1]
    try:
        df_ventas = pd.read_csv(ruta_csv)
    except FileNotFoundError:
        print(f"ERROR: No se encontró el archivo '{ruta_csv}'.")
        sys.exit(2)
    except Exception as exc:
        print(f"ERROR al leer el CSV: {exc}")
        sys.exit(2)

    errores_encontrados = validar(df_ventas)

    if errores_encontrados:
        print(f"\n{'='*60}")
        print("VALIDACIÓN FALLIDA — se encontraron los siguientes errores:")
        print(f"{'='*60}")
        for err in errores_encontrados:
            print(f"  ✖ {err}")
        print(f"{'='*60}")
        print(f"Total de errores: {len(errores_encontrados)}")
        print("Carga bloqueada. Corrija los datos antes de reintentar.")
        sys.exit(1)
    else:
        print("✔ Validación exitosa — todos los datos cumplen las reglas.")
        sys.exit(0)
