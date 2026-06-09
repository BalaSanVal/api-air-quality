from fastapi import FastAPI, HTTPException
from schemas import MeasurementIn
from etl import run_etl
from storage import save_measurement, get_latest_measurement, get_all_measurements
from simat_etl import get_latest_simat_from_csv, get_simat_records_for_import
from simat_storage import (
    save_simat_records,
    get_latest_simat_measurement_from_db,
    get_available_simat_stations_from_db,
)
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
def latest_simat_measurement(station_code: str = "GAM", source: str = "csv"):
    """
    Consulta la última lectura SIMAT.

    source=csv -> lee desde el archivo CSV sin guardar en BD.
    source=db  -> lee desde la base de datos.
    """
    try:
        if source == "db":
            latest = get_latest_simat_measurement_from_db(station_code=station_code)

            if latest is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"No hay mediciones SIMAT guardadas para la estación {station_code}",
                )

            return latest

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

    except HTTPException:
        raise

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
            detail=f"Error processing SIMAT data: {str(e)}",
        )

@app.get("/api/v1/simat/stations")
def list_simat_stations():
    try:
        stations = get_available_simat_stations_from_db()

        return {
            "count": len(stations),
            "items": stations,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting SIMAT stations: {str(e)}",
        )

@app.post("/api/v1/simat/import")
def import_simat_measurements(station_code: str | None = None):
    """
    Importa mediciones SIMAT desde data/contaminantes_2026.csv hacia la base de datos.

    Si station_code viene vacío:
    - importa todas las estaciones del CSV que existan en estacion_oficial.

    Si station_code = GAM:
    - importa solo GAM.
    """
    try:
        records = get_simat_records_for_import(
            file_path="data/contaminantes_2026.csv",
            station_code=station_code,
        )

        result = save_simat_records(records)

        return {
            "status": "ok",
            "message": "SIMAT measurements imported successfully",
            "station_code": station_code,
            "summary": result,
        }

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
            detail=f"Error importing SIMAT measurements: {str(e)}",
        )
