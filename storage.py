from typing import List, Dict, Any

received_measurements: List[Dict[str, Any]] = []


def save_measurement(measurement: dict) -> dict:
    received_measurements.append(measurement)
    return measurement


def get_latest_measurement() -> dict | None:
    if not received_measurements:
        return None
    return received_measurements[-1]


def get_all_measurements() -> list[dict]:
    return received_measurements
