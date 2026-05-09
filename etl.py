from datetime import datetime
from schemas import MeasurementIn


def build_datetime(date_str, time_str):
    return datetime.strptime(
        f"{date_str} {time_str}",
        "%Y-%m-%d %H:%M:%S"
    )


def classify_environment(node_id):
    indoor_nodes = {1, 2}
    outdoor_nodes = {3}

    if node_id in indoor_nodes:
        return "indoor"
    if node_id in outdoor_nodes:
        return "outdoor"
    return "unknown"


def compute_average_temperature(scd_temp, bme_temp):
    values = []

    if scd_temp is not None:
        values.append(scd_temp)

    if bme_temp is not None:
        values.append(bme_temp)

    if not values:
        return None

    return sum(values) / len(values)


def validate_range(value, min_val, max_val):
    if value is None:
        return True

    return min_val <= value <= max_val


def run_etl(payload: MeasurementIn):
    dt = build_datetime(payload.date, payload.time)

    temperature_final = compute_average_temperature(
        payload.scd41_temp_c,
        payload.bme688_temp_c
    )

    validations = {
        "node_valid": payload.node_id in {1, 2, 3},
        "co2_valid": validate_range(payload.scd41_co2_ppm, 0, 10000),
        "scd41_temp_valid": validate_range(payload.scd41_temp_c, -20, 80),
        "bme688_temp_valid": validate_range(payload.bme688_temp_c, -20, 80),
        "scd41_humidity_valid": validate_range(payload.scd41_rh_pct, 0, 100),
        "bme688_humidity_valid": validate_range(payload.bme688_rh_pct, 0, 100),
        "pressure_valid": validate_range(payload.bme688_press_hpa, 300, 1100),
        "pm25_valid": validate_range(payload.sps30_pm2_5_ugm3, 0, 2000),
        "pm10_valid": validate_range(payload.sps30_pm10_ugm3, 0, 3000),
        "tvoc_valid": validate_range(payload.ens160_tvoc_ppb, 0, 65000),
        "eco2_valid": validate_range(payload.ens160_eco2_ppm, 0, 65000)
    }

    is_valid_record = all(validations.values())

    return {
        "node_id": payload.node_id,
        "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "environment": classify_environment(payload.node_id),
        "temperature_average": temperature_final,
        "is_valid_record": is_valid_record,
        "validations": validations,

        "scd41": {
            "co2": payload.scd41_co2_ppm,
            "temperatura": payload.scd41_temp_c,
            "humedad_relativa": payload.scd41_rh_pct
        },

        "bme688": {
            "temperatura": payload.bme688_temp_c,
            "humedad_relativa": payload.bme688_rh_pct,
            "presion_atmosferica": payload.bme688_press_hpa,
            "resistencia_gas": payload.bme688_gas_kohm
        },

        "ens160": {
            "aqi": payload.ens160_aqi,
            "tvoc": payload.ens160_tvoc_ppb,
            "eco2": payload.ens160_eco2_ppm
        },

        "sps30": {
            "pm1_0": payload.sps30_pm1_ugm3,
            "pm2_5": payload.sps30_pm2_5_ugm3,
            "pm4_0": payload.sps30_pm4_ugm3,
            "pm10": payload.sps30_pm10_ugm3,
            "tamano_promedio_particula": payload.sps30_typ_um
        }
    }
