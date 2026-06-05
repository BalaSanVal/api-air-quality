from sqlalchemy import text
from database import SessionLocal


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


def get_station_id_by_code(db, station_code: str) -> int | None:
    """
    Busca la estación oficial usando el prefijo del campo nombre.

    Ejemplo:
    station_code = GAM
    nombre = GAM - Gustavo A. Madero
    """
    result = db.execute(
        text("""
            SELECT id_estacion
            FROM estacion_oficial
            WHERE nombre LIKE :station_pattern
            LIMIT 1
        """),
        {
            "station_pattern": f"{station_code.upper()} -%"
        }
    ).mappings().first()

    if result is None:
        return None

    return result["id_estacion"]


def simat_measurement_exists(db, fecha_hora, id_estacion: int) -> bool:
    """
    Evita duplicados.

    Una medición SIMAT se considera repetida si ya existe:
    - misma fecha_hora
    - fuente = SIMAT
    - mismo id_estacion
    """
    result = db.execute(
        text("""
            SELECT id_medicion
            FROM medicion
            WHERE fecha_hora = :fecha_hora
              AND fuente = 'SIMAT'
              AND id_estacion = :id_estacion
            LIMIT 1
        """),
        {
            "fecha_hora": fecha_hora,
            "id_estacion": id_estacion,
        }
    ).mappings().first()

    return result is not None


def has_at_least_one_valid_value(measurements: dict) -> bool:
    """
    Si los 9 campos son NULL, no se guarda.
    """
    return any(measurements.get(field) is not None for field in SIMAT_MEASUREMENT_FIELDS)


def save_simat_records(records: list[dict]) -> dict:
    """
    Guarda registros SIMAT en las tablas existentes:

    1. medicion
    2. medicion_simat

    No modifica la estructura de la base de datos.
    No guarda registros con los 9 valores nulos.
    No duplica registros ya existentes por fecha_hora + estación.
    """
    db = SessionLocal()

    inserted = 0
    skipped_duplicates = 0
    skipped_no_station = 0
    skipped_empty = 0

    try:
        for record in records:
            station_code = record["station_code"]
            fecha_hora = record["datetime"]
            measurements = record["measurements"]

            if not has_at_least_one_valid_value(measurements):
                skipped_empty += 1
                continue

            id_estacion = get_station_id_by_code(db, station_code)

            if id_estacion is None:
                skipped_no_station += 1
                continue

            if simat_measurement_exists(db, fecha_hora, id_estacion):
                skipped_duplicates += 1
                continue

            result = db.execute(
                text("""
                    INSERT INTO medicion (
                        fecha_hora,
                        fuente,
                        calidad_dato,
                        id_estacion
                    )
                    VALUES (
                        :fecha_hora,
                        'SIMAT',
                        1,
                        :id_estacion
                    )
                """),
                {
                    "fecha_hora": fecha_hora,
                    "id_estacion": id_estacion,
                }
            )

            id_medicion = result.lastrowid

            db.execute(
                text("""
                    INSERT INTO medicion_simat (
                        co,
                        no,
                        no2,
                        nox,
                        o3,
                        pm10,
                        pm2_5,
                        pmco,
                        so2,
                        id_medicion
                    )
                    VALUES (
                        :co,
                        :no,
                        :no2,
                        :nox,
                        :o3,
                        :pm10,
                        :pm2_5,
                        :pmco,
                        :so2,
                        :id_medicion
                    )
                """),
                {
                    "co": measurements.get("co"),
                    "no": measurements.get("no"),
                    "no2": measurements.get("no2"),
                    "nox": measurements.get("nox"),
                    "o3": measurements.get("o3"),
                    "pm10": measurements.get("pm10"),
                    "pm2_5": measurements.get("pm2_5"),
                    "pmco": measurements.get("pmco"),
                    "so2": measurements.get("so2"),
                    "id_medicion": id_medicion,
                }
            )

            inserted += 1

        db.commit()

        return {
            "inserted": inserted,
            "skipped_duplicates": skipped_duplicates,
            "skipped_no_station": skipped_no_station,
            "skipped_empty": skipped_empty,
            "total_received": len(records),
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def get_latest_simat_measurement_from_db(station_code: str = "GAM") -> dict | None:
    """
    Consulta la última medición SIMAT guardada en la base de datos.
    """
    db = SessionLocal()

    try:
        result = db.execute(
            text("""
                SELECT
                    m.id_medicion,
                    DATE_FORMAT(m.fecha_hora, '%Y-%m-%d %H:%i:%s') AS fecha_hora,
                    m.fuente,
                    m.calidad_dato,
                    eo.id_estacion,
                    eo.nombre AS estacion,
                    eo.alcaldia,
                    eo.longitud,
                    eo.latitud,
                    ms.co,
                    ms.no,
                    ms.no2,
                    ms.nox,
                    ms.o3,
                    ms.pm10,
                    ms.pm2_5,
                    ms.pmco,
                    ms.so2
                FROM medicion m
                JOIN estacion_oficial eo
                    ON m.id_estacion = eo.id_estacion
                JOIN medicion_simat ms
                    ON m.id_medicion = ms.id_medicion
                WHERE m.fuente = 'SIMAT'
                  AND eo.nombre LIKE :station_pattern
                ORDER BY m.fecha_hora DESC
                LIMIT 1
            """),
            {
                "station_pattern": f"{station_code.upper()} -%"
            }
        ).mappings().first()

        return dict(result) if result else None

    finally:
        db.close()
