from datetime import datetime
from schemas import MeasurementIn


def build_datetime(date_str, time_str):

    return datetime.strptime(
        f"{date_str} {time_str}",
        "%Y-%m-%d %H:%M:%S"
    )


def classify_environment(node_id):

    indoor_nodes = {10}

    if node_id in indoor_nodes:
        return "indoor"

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

    if value < min_val:
        return False

    if value > max_val:
        return False

    return True


def run_etl(payload: MeasurementIn):

    dt = build_datetime(
        payload.date,
        payload.time
    )

    temperature_final = compute_average_temperature(
        payload.scd41_temp_c,
        payload.bme688_temp_c
    )

    humidity_final = payload.scd41_rh_pct

    validations = {

        "co2_valid":
        validate_range(
            payload.scd41_co2_ppm,
            0,
            10000
        ),

        "temp_valid":
        validate_range(
            temperature_final,
            -20,
            80
        ),

        "pm25_valid":
        validate_range(
            payload.sps30_pm2_5_ugm3,
            0,
            2000
        )
    }

    is_valid_record = all(
        validations.values()
    )

    transformed = {

        "node_id": payload.node_id,

        "datetime":
        dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "environment":
        classify_environment(
            payload.node_id
        ),

        "co2_ppm":
        payload.scd41_co2_ppm,

        "tvoc_ppb":
        payload.ens160_tvoc_ppb,

        "eco2_ppm":
        payload.ens160_eco2_ppm,

        "aqi":
        payload.ens160_aqi,

        "pm1":
        payload.sps30_pm1_ugm3,

        "pm25":
        payload.sps30_pm2_5_ugm3,

        "pm4":
        payload.sps30_pm4_ugm3,

        "pm10":
        payload.sps30_pm10_ugm3,

        "temperature":
        temperature_final,

        "humidity":
        humidity_final,

        "pressure_hpa":
        payload.bme688_press_hpa,

        "gas_kohm":
        payload.bme688_gas_kohm,

        "is_valid_record":
        is_valid_record,

        "validations":
        validations
}

    return transformed
