from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict

app = FastAPI(
    title="Indoor Node API",
    version="1.0.0",
    description="API para recibir mediciones del nodo interior ESP32"
)

# Almacenamiento temporal en memoria solo para pruebas.
# En Render esto se pierde si el servicio se reinicia.
received_measurements = []


class MeasurementIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: int = Field(..., ge=1)

    date: str = Field(..., description="Formato YYYY-MM-DD")
    time: str = Field(..., description="Formato HH:MM:SS")

    scd41_co2_ppm: Optional[float] = None
    scd41_temp_c: Optional[float] = None
    scd41_rh_pct: Optional[float] = None

    bme688_temp_c: Optional[float] = None
    bme688_rh_pct: Optional[float] = None
    bme688_press_hpa: Optional[float] = None
    bme688_gas_kohm: Optional[float] = None

    ens160_aqi: Optional[int] = Field(None, ge=0)
    ens160_tvoc_ppb: Optional[float] = None
    ens160_eco2_ppm: Optional[float] = None

    sps30_pm1_ugm3: Optional[float] = None
    sps30_pm2_5_ugm3: Optional[float] = None
    sps30_pm4_ugm3: Optional[float] = None
    sps30_pm10_ugm3: Optional[float] = None
    sps30_typ_um: Optional[float] = None


def validate_datetime(date_str: str, time_str: str) -> datetime:
    try:
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date/time format. Use date=YYYY-MM-DD and time=HH:MM:SS"
        )


@app.get("/")
def home():
    return {
        "message": "API running",
        "service": "Indoor Node API",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/measurements")
def receive_measurement(payload: MeasurementIn):
    fecha = validate_datetime(payload.date, payload.time)

    data = payload.model_dump()
    data["datetime"] = fecha.strftime("%Y-%m-%d %H:%M:%S")

    received_measurements.append(data)

    print("JSON recibido:")
    print(data)

    return {
        "status": "ok",
        "message": "Measurement received successfully",
        "node_id": payload.node_id,
        "datetime": data["datetime"]
    }


@app.get("/api/v1/measurements/latest")
def latest_measurement():
    if not received_measurements:
        raise HTTPException(status_code=404, detail="No measurements received yet")
    return received_measurements[-1]


@app.get("/api/v1/measurements")
def list_measurements():
    return {
        "count": len(received_measurements),
        "items": received_measurements
    }
