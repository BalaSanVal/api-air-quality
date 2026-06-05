from fastapi import FastAPI, HTTPException
from schemas import MeasurementIn
from etl import run_etl
from storage import save_measurement, get_latest_measurement, get_all_measurements
from simat_etl import get_latest_simat_from_csv
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Air Quality API",
    version="1.0.0",
    description="API para recibir mediciones de nodos ESP32 y almacenarlas en AWS RDS MariaDB"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/api/v1/simat/latest")
def latest_simat_measurement(station_code: str = "GAM"):
    try:
        latest = get_latest_simat_from_csv(
            file_path="data/contaminantes_2026.csv",
            station_code=station_code,
        )

        if latest is None:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontraron registros SIMAT para la estación {station_code}",
            )

        return latest

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing SIMAT CSV: {str(e)}",
        )
