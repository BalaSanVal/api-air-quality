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


def has_at_least_one_valid_value(measurements: dict) -> bool:
    """
    Si los 9 campos son NULL, no se guarda.
    """
    return any(measurements.get(field) is not None for field in SIMAT_MEASUREMENT_FIELDS)


def load_station_catalog(db) -> dict:
    """
    Carga una sola vez el catálogo de estaciones oficiales.

    Retorna:
    {
        "GAM": 1,
        "BJU": 6,
        ...
    }

    Esto funciona porque el campo nombre está guardado como:
    GAM - Gustavo A. Madero
    """
    rows = db.execute(
        text("""
            SELECT id_estacion, nombre
            FROM estacion_oficial
        """)
    ).mappings().all()

    catalog = {}

    for row in rows:
        name = row["nombre"] or ""

        if " - " not in name:
            continue

        station_code = name.split(" - ", 1)[0].strip().upper()

        if station_code:
            catalog[station_code] = row["id_estacion"]

    return catalog


def load_existing_simat_keys(db, station_ids: set[int] | None = None) -> set[tuple]:
    """
    Carga una sola vez las mediciones SIMAT ya existentes.

    Retorna un set con:
    (fecha_hora, id_estacion)

    Esto permite evitar duplicados sin hacer SELECT por cada registro.
    """
    if station_ids:
        rows = db.execute(
            text("""
                SELECT fecha_hora, id_estacion
                FROM medicion
                WHERE fuente = 'SIMAT'
                  AND id_estacion IN :station_ids
            """),
            {
                "station_ids": tuple(station_ids)
            }
        ).mappings().all()
    else:
        rows = db.execute(
            text("""
                SELECT fecha_hora, id_estacion
                FROM medicion
                WHERE fuente = 'SIMAT'
                  AND id_estacion IS NOT NULL
            """)
        ).mappings().all()

    return {
        (row["fecha_hora"], row["id_estacion"])
        for row in rows
    }


def save_simat_records(records: list[dict], batch_size: int = 500) -> dict:
    """
    Guarda registros SIMAT en las tablas existentes:

    1. medicion
    2. medicion_simat

    Mejoras:
    - Carga catálogo de estaciones una sola vez.
    - Carga duplicados existentes una sola vez.
    - No guarda registros con los 9 valores nulos.
    - Inserta solo lo faltante.
    - Hace commit por bloques.
    """
    db = SessionLocal()

    inserted = 0
    skipped_duplicates = 0
    skipped_no_station = 0
    skipped_empty = 0

    try:
        station_catalog = load_station_catalog(db)

        station_ids_in_file = {
            station_catalog[record["station_code"]]
            for record in records
            if record["station_code"] in station_catalog
        }

        existing_keys = load_existing_simat_keys(
            db,
            station_ids=station_ids_in_file if station_ids_in_file else None,
        )

        pending_commit = 0

        for record in records:
            station_code = record["station_code"]
            fecha_hora = record["datetime"]
            measurements = record["measurements"]

            if not has_at_least_one_valid_value(measurements):
                skipped_empty += 1
                continue

            id_estacion = station_catalog.get(station_code)

            if id_estacion is None:
                skipped_no_station += 1
                continue

            unique_key = (fecha_hora, id_estacion)

            if unique_key in existing_keys:
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

            existing_keys.add(unique_key)
            inserted += 1
            pending_commit += 1

            if pending_commit >= batch_size:
                db.commit()
                pending_commit = 0

        if pending_commit > 0:
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
