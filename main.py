from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()

class MeasurementIn(BaseModel):
    node_id: int = Field(..., ge=1)
    date: str
    time: str
    pm1_ugm3: Optional[float] = None
    pm2_5_ugm3: Optional[float] = None
    pm10_ugm3: Optional[float] = None
    tvoc_ppb: Optional[float] = None
    co2_ppm: Optional[float] = None
    temperature_c: Optional[float] = None


def validate_datetime(date_str, time_str):
    try:
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
    except:
        raise HTTPException(status_code=400, detail="Invalid date format")


@app.get("/")
def home():
    return {"message": "API running"}


@app.post("/api/v1/measurements")
def receive_measurement(payload: MeasurementIn):

    fecha = validate_datetime(payload.date, payload.time)

    print("JSON recibido")
    print(payload.model_dump())

    return {
        "status": "ok",
        "node_id": payload.node_id,
        "datetime": fecha.strftime("%Y-%m-%d %H:%M:%S")
    }
