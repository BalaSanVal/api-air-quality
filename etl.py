from datetime import datetime
from fastapi import HTTPException

from schemas import MeasurementIn


def validate_datetime(date_str: str, time_str: str) -> datetime:
    try:
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date/time format. Use date=YYYY-MM-DD and time=HH:MM:SS"
        )


def is_optional_float_valid(value: float | None, min_value: float | None = None, max_value: float | None = None) -> bool:
    if value is None:
        return True
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def transform_measurement(payload: MeasurementIn) -> dict:
    dt = validate_datetime(payload.date, payload.time)

    data = payload.model_dump()

    data["datetime"] = dt.strftime("%Y-%m-%d %H:%M:%S")
    data["datetime_iso"] = dt.isoformat()

    # Clasificación simple por nodo
    if payload.node_id in {1, 2, 10}:
        data["environment"] = "indoor"
    elif payload.node_id in {3}:
        data["environment"] = "outdoor"
    else:
        data["environment"] = "unknown"

    # Validaciones básicas de rango
    validations = {
        "scd41_co2_ppm_valid": is_optional_float_valid(payload.scd41_co2_ppm, 0, 10000),
        "scd41_temp_c_valid": is_optional_float_valid(payload.scd41_temp_c, -20, 80),
        "scd41_rh_pct_valid": is_optional_float_valid(payload.scd41_rh_pct, 0, 100),
        "bme688_temp_c_valid": is_optional_float_valid(payload.bme688_temp_c, -20, 80),
        "bme688_rh_pct_valid": is_optional_float_valid(payload.bme688_rh_pct, 0, 100),
        "bme688_press_hpa_valid": is_optional_float_valid(payload.bme688_press_hpa, 300, 1100),
        "bme688_gas_kohm_valid": is_optional_float_valid(payload.bme688_gas_kohm, 0, 100000),
        "ens160_tvoc_ppb_valid": is_optional_float_valid(payload.ens160_tvoc_ppb, 0, 100000),
        "ens160_eco2_ppm_valid": is_optional_float_valid(payload.ens160_eco2_ppm, 0, 10000),
        "sps30_pm1_ugm3_valid": is_optional_float_valid(payload.sps30_pm1_ugm3, 0, 2000),
        "sps30_pm2_5_ugm3_valid": is_optional_float_valid(payload.sps30_pm2_5_ugm3, 0, 2000),
        "sps30_pm4_ugm3_valid": is_optional_float_valid(payload.sps30_pm4_ugm3, 0, 2000),
        "sps30_pm10_ugm3_valid": is_optional_float_valid(payload.sps30_pm10_ugm3, 0, 2000),
        "sps30_typ_um_valid": is_optional_float_valid(payload.sps30_typ_um, 0, 20),
    }

    data["validations"] = validations
    data["is_valid_record"] = all(validations.values())

    return data
