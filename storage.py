from sqlalchemy import text
from database import SessionLocal


def save_measurement(measurement: dict) -> dict:
    db = SessionLocal()

    try:
        result = db.execute(
            text("""
                INSERT INTO medicion (fecha_hora, fuente, calidad_dato, id_estacion)
                VALUES (:fecha_hora, :fuente, :calidad_dato, NULL)
            """),
            {
                "fecha_hora": measurement["datetime"],
                "fuente": "nodo_local",
                "calidad_dato": measurement["is_valid_record"]
            }
        )

        id_medicion = result.lastrowid

        db.execute(
            text("""
                INSERT INTO nodo_medicion (id_nodo, id_medicion)
                VALUES (:id_nodo, :id_medicion)
            """),
            {
                "id_nodo": measurement["node_id"],
                "id_medicion": id_medicion
            }
        )

        scd41 = measurement["scd41"]
        db.execute(
            text("""
                INSERT INTO medicion_scd41
                (co2, temperatura, humedad_relativa, id_medicion)
                VALUES (:co2, :temperatura, :humedad_relativa, :id_medicion)
            """),
            {
                "co2": scd41["co2"],
                "temperatura": scd41["temperatura"],
                "humedad_relativa": scd41["humedad_relativa"],
                "id_medicion": id_medicion
            }
        )

        bme688 = measurement["bme688"]
        db.execute(
            text("""
                INSERT INTO medicion_bme688
                (temperatura, humedad_relativa, presion_atmosferica, resistencia_gas, id_medicion)
                VALUES (:temperatura, :humedad_relativa, :presion_atmosferica, :resistencia_gas, :id_medicion)
            """),
            {
                "temperatura": bme688["temperatura"],
                "humedad_relativa": bme688["humedad_relativa"],
                "presion_atmosferica": bme688["presion_atmosferica"],
                "resistencia_gas": bme688["resistencia_gas"],
                "id_medicion": id_medicion
            }
        )

        ens160 = measurement["ens160"]
        db.execute(
            text("""
                INSERT INTO medicion_ens160
                (aqi, tvoc, eco2, id_medicion)
                VALUES (:aqi, :tvoc, :eco2, :id_medicion)
            """),
            {
                "aqi": ens160["aqi"],
                "tvoc": ens160["tvoc"],
                "eco2": ens160["eco2"],
                "id_medicion": id_medicion
            }
        )

        sps30 = measurement["sps30"]
        db.execute(
            text("""
                INSERT INTO medicion_sps30
                (pm1_0, pm2_5, pm4_0, pm10, tamano_promedio_particula, id_medicion)
                VALUES (:pm1_0, :pm2_5, :pm4_0, :pm10, :tamano_promedio_particula, :id_medicion)
            """),
            {
                "pm1_0": sps30["pm1_0"],
                "pm2_5": sps30["pm2_5"],
                "pm4_0": sps30["pm4_0"],
                "pm10": sps30["pm10"],
                "tamano_promedio_particula": sps30["tamano_promedio_particula"],
                "id_medicion": id_medicion
            }
        )

        db.commit()

        measurement["id_medicion"] = id_medicion
        return measurement

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def get_latest_measurement() -> dict | None:
    db = SessionLocal()

    try:
        result = db.execute(
            text("""
                SELECT 
                    m.id_medicion,
                    nm.id_nodo AS node_id,
                    n.nombre AS nodo,
                    n.tipo AS tipo_nodo,
                    n.ubicacion,
                    m.fecha_hora,
                    m.fuente,
                    m.calidad_dato,
                    scd.co2,
                    scd.temperatura AS scd41_temperatura,
                    scd.humedad_relativa AS scd41_humedad,
                    bme.temperatura AS bme688_temperatura,
                    bme.humedad_relativa AS bme688_humedad,
                    bme.presion_atmosferica,
                    bme.resistencia_gas,
                    ens.aqi,
                    ens.tvoc,
                    ens.eco2,
                    sps.pm1_0,
                    sps.pm2_5,
                    sps.pm4_0,
                    sps.pm10,
                    sps.tamano_promedio_particula
                FROM medicion m
                JOIN nodo_medicion nm ON m.id_medicion = nm.id_medicion
                JOIN nodo n ON nm.id_nodo = n.id_nodo
                LEFT JOIN medicion_scd41 scd ON m.id_medicion = scd.id_medicion
                LEFT JOIN medicion_bme688 bme ON m.id_medicion = bme.id_medicion
                LEFT JOIN medicion_ens160 ens ON m.id_medicion = ens.id_medicion
                LEFT JOIN medicion_sps30 sps ON m.id_medicion = sps.id_medicion
                WHERE m.fuente = 'nodo_local'
                ORDER BY m.fecha_hora DESC, m.id_medicion DESC
                LIMIT 1
            """)
        ).mappings().first()

        return dict(result) if result else None

    finally:
        db.close()


def get_all_measurements() -> list[dict]:
    db = SessionLocal()

    try:
        result = db.execute(
            text("""
                SELECT 
                    m.id_medicion,
                    nm.id_nodo AS node_id,
                    n.nombre AS nodo,
                    n.tipo AS tipo_nodo,
                    n.ubicacion,
                    m.fecha_hora,
                    m.fuente,
                    m.calidad_dato,
                    scd.co2,
                    ens.tvoc,
                    ens.eco2,
                    sps.pm2_5,
                    sps.pm10
                FROM medicion m
                JOIN nodo_medicion nm ON m.id_medicion = nm.id_medicion
                JOIN nodo n ON nm.id_nodo = n.id_nodo
                LEFT JOIN medicion_scd41 scd ON m.id_medicion = scd.id_medicion
                LEFT JOIN medicion_ens160 ens ON m.id_medicion = ens.id_medicion
                LEFT JOIN medicion_sps30 sps ON m.id_medicion = sps.id_medicion
                WHERE m.fuente = 'nodo_local'
                ORDER BY m.fecha_hora DESC, m.id_medicion DESC
                LIMIT 100
            """)
        ).mappings().all()

        return [dict(row) for row in result]

    finally:
        db.close()
