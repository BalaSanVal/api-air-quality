import csv
from datetime import datetime
from pathlib import Path
from typing import Optional


SIMAT_PARAMETERS = {
    "CO": "co",
    "NO": "no",
    "NO2": "no2",
    "NOX": "nox",
    "O3": "o3",
    "PM10": "pm10",
    "PM2.5": "pm2_5",
    "PMCO": "pmco",
    "SO2": "so2",
}

SIMAT_MEASUREMENT_FIELDS = [
    "co",
    "no",
    "no2",
    "nox",
    "o3",
    "pm10",
    "pm2_5",
    "pmco",
    "so2",
]


def parse_simat_datetime(value: str) -> datetime:
    """
    Convierte fechas del archivo SIMAT a datetime.

    Formato detectado en contaminantes_2026.csv:
    2026-01-01 00:00:00

    También se dejan formatos alternativos por si SIMAT cambia la descarga.
    """
    cleaned = value.strip().replace('"', "")

    possible_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    ]

    for date_format in possible_formats:
        try:
            return datetime.strptime(cleaned, date_format)
        except ValueError:
            continue

    raise ValueError(f"Formato de fecha SIMAT no reconocido: {value}")


def parse_float(value: str) -> Optional[float]:
    """
    Convierte valores numéricos del CSV.

    Reglas:
    - vacío => None
    - texto inválido => None
    - -99 => None, porque SIMAT lo usa como valor inválido/no disponible
    """
    if value is None:
        return None

    cleaned = str(value).strip().replace('"', "")

    if cleaned == "":
        return None

    try:
        number = float(cleaned)
    except ValueError:
        return None

    if number == -99:
        return None

    return number


def has_at_least_one_valid_value(measurements: dict) -> bool:
    """
    Regresa True si al menos uno de los 9 campos SIMAT tiene valor numérico.

    Si los 9 valores son None, el registro no debe insertarse.
    """
    return any(measurements.get(field) is not None for field in SIMAT_MEASUREMENT_FIELDS)


def detect_header_and_delimiter(lines: list[str]) -> tuple[int, str]:
    """
    Detecta en qué fila empieza el encabezado real del CSV y qué separador usa.

    Encabezado esperado:
    date,id_station,id_parameter,valor,unit
    """
    possible_delimiters = [",", ";", "\t", "|"]
    required_columns = {"date", "id_station", "id_parameter", "valor", "unit"}

    for index, line in enumerate(lines):
        normalized = line.strip().lower()

        for delimiter in possible_delimiters:
            columns = [
                column.strip().lower().replace('"', "")
                for column in normalized.split(delimiter)
            ]

            if required_columns.issubset(set(columns)):
                return index, delimiter

    preview = "\n".join(lines[:15])
    raise ValueError(
        "No se encontró el encabezado del CSV SIMAT. "
        "Se esperaba una fila con las columnas: "
        "date, id_station, id_parameter, valor, unit. "
        f"Primeras líneas detectadas:\n{preview}"
    )


def read_simat_long_csv(file_path: str, station_code: str | None = None) -> list[dict]:
    """
    Lee el CSV general del SIMAT con estructura larga:

    date,id_station,id_parameter,valor,unit

    Devuelve una lista agrupada por:
    fecha_hora + estación

    Cada elemento queda listo para insertarse en:
    medicion + medicion_simat.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo SIMAT: {file_path}")

    records_by_key: dict[tuple[datetime, str], dict] = {}

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        lines = file.readlines()

    header_index, delimiter = detect_header_and_delimiter(lines)

    data_lines = lines[header_index:]
    reader = csv.DictReader(data_lines, delimiter=delimiter)

    for row in reader:
        row_station = (row.get("id_station") or "").strip().upper()
        parameter = (row.get("id_parameter") or "").strip().upper()
        date_raw = row.get("date")
        value_raw = row.get("valor")

        if not row_station or not date_raw:
            continue

        if station_code and row_station != station_code.upper():
            continue

        if parameter not in SIMAT_PARAMETERS:
            continue

        try:
            dt = parse_simat_datetime(date_raw)
        except ValueError:
            continue

        value = parse_float(value_raw)

        key = (dt, row_station)

        if key not in records_by_key:
            records_by_key[key] = {
                "station_code": row_station,
                "datetime": dt,
                "source": "SIMAT",
                "calidad_dato": 1,
                "measurements": {
                    "co": None,
                    "no": None,
                    "no2": None,
                    "nox": None,
                    "o3": None,
                    "pm10": None,
                    "pm2_5": None,
                    "pmco": None,
                    "so2": None,
                },
            }

        db_field = SIMAT_PARAMETERS[parameter]
        records_by_key[key]["measurements"][db_field] = value

    records = list(records_by_key.values())

    valid_records = [
        record
        for record in records
        if has_at_least_one_valid_value(record["measurements"])
    ]

    return sorted(
        valid_records,
        key=lambda item: (item["datetime"], item["station_code"]),
    )


def get_latest_simat_from_csv(file_path: str, station_code: str = "GAM") -> Optional[dict]:
    """
    Regresa la última lectura disponible para una estación SIMAT.
    No guarda nada en base de datos.
    """
    records = read_simat_long_csv(
        file_path=file_path,
        station_code=station_code,
    )

    if not records:
        return None

    latest = records[-1]

    return {
        "station_code": latest["station_code"],
        "source": "SIMAT",
        "last_datetime": latest["datetime"].strftime("%Y-%m-%d %H:%M:%S"),
        "measurements": latest["measurements"],
        "saved_to_database": False,
    }


def get_simat_records_for_import(file_path: str, station_code: str | None = None) -> list[dict]:
    """
    Regresa registros SIMAT limpios, agrupados y listos para guardar en BD.

    Si station_code es None, procesa todas las estaciones del archivo.
    """
    return read_simat_long_csv(
        file_path=file_path,
        station_code=station_code,
    )
