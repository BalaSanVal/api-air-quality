from fastapi import FastAPI, HTTPException
from schemas import MeasurementIn
from etl import run_etl
from storage import save_measurement, get_latest_measurement, get_all_measurements

app = FastAPI(
    title="Air Quality API",
    version="1.0.0",
    description="API para recibir mediciones de nodos ESP32 y almacenarlas en AWS RDS MariaDB"
)


@app.get("/")
def home():
    return {
        "message": "API running",
        "service": "Air Quality API",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/measurements")
def receive_measurement(payload: MeasurementIn):
    try:
        processed = run_etl(payload)
        saved = save_measurement(processed)

        return {
            "status": "ok",
            "message": "Measurement processed and saved successfully",
            "id_medicion": saved["id_medicion"],
            "node_id": saved["node_id"],
            "datetime": saved["datetime"],
            "is_valid_record": saved["is_valid_record"]
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving measurement: {str(e)}"
        )


@app.get("/api/v1/measurements/latest")
def latest_measurement():
    latest = get_latest_measurement()

    if latest is None:
        raise HTTPException(
            status_code=404,
            detail="No measurements received yet"
        )

    return latest


@app.get("/api/v1/measurements")
def list_measurements():
    items = get_all_measurements()

    return {
        "count": len(items),
        "items": items
    }
