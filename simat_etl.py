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


def parse_simat_datetime(value: str) -> datetime:
    """
    Convierte fechas del SIMAT a datetime.

    El archivo general contaminantes_2026.csv puede venir como:
    2026-01-01 00:00:00

    Otros archivos pueden venir como:
    01/01/2026 00:00
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
    Si viene vacío o inválido, regresa None.
    """
    if value is None:
        return None

    cleaned = str(value).strip()

    if cleaned == "":
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def read_simat_long_csv(file_path: str, station_code: str = "GAM") -> list[dict]:
    """
    Lee el CSV general del SIMAT con estructura:

    date,id_station,id_parameter,valor,unit

    El archivo trae metadatos al inicio, por eso se busca automáticamente
    la fila donde empieza el encabezado real.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo SIMAT: {file_path}")

    records_by_datetime: dict[datetime, dict] = {}

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        lines = file.readlines()

        header_index = None
    delimiter = ","

    for index, line in enumerate(lines):
        normalized = line.strip().lower()

        possible_delimiters = [",", ";", "\t", "|"]

        for candidate_delimiter in possible_delimiters:
            columns = [
                column.strip().lower().replace('"', "")
                for column in normalized.split(candidate_delimiter)
            ]

            required_columns = {"date", "id_station", "id_parameter", "valor", "unit"}

            if required_columns.issubset(set(columns)):
                header_index = index
                delimiter = candidate_delimiter
                break

        if header_index is not None:
            break

    if header_index is None:
        preview = "\n".join(lines[:15])
        raise ValueError(
            "No se encontró el encabezado del CSV SIMAT. "
            "Se esperaba una fila con las columnas: "
            "date, id_station, id_parameter, valor, unit. "
            f"Primeras líneas detectadas:\n{preview}"
        )

    data_lines = lines[header_index:]
    reader = csv.DictReader(data_lines, delimiter=delimiter)

    for row in reader:
        row_station = (row.get("id_station") or "").strip().upper()
        parameter = (row.get("id_parameter") or "").strip().upper()

        if row_station != station_code.upper():
            continue

        if parameter not in SIMAT_PARAMETERS:
            continue

        date_raw = row.get("date")
        value_raw = row.get("valor")

        if not date_raw:
            continue

        try:
            dt = parse_simat_datetime(date_raw)
        except ValueError:
            continue

        value = parse_float(value_raw)

        if dt not in records_by_datetime:
            records_by_datetime[dt] = {
                "station_code": row_station,
                "datetime": dt,
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
                "units": {},
            }

        db_field = SIMAT_PARAMETERS[parameter]
        records_by_datetime[dt]["measurements"][db_field] = value
        records_by_datetime[dt]["units"][db_field] = row.get("unit")

    return sorted(records_by_datetime.values(), key=lambda item: item["datetime"])


def get_latest_simat_from_csv(file_path: str, station_code: str = "GAM") -> Optional[dict]:
    """
    Regresa la última lectura disponible para una estación SIMAT.
    No guarda nada en base de datos.
    """
    records = read_simat_long_csv(file_path=file_path, station_code=station_code)

    if not records:
        return None

    latest = records[-1]

    return {
        "station_code": latest["station_code"],
        "source": "SIMAT",
        "last_datetime": latest["datetime"].strftime("%Y-%m-%d %H:%M:%S"),
        "measurements": latest["measurements"],
        "units": latest["units"],
        "saved_to_database": False,
    }
