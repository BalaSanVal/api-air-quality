from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


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
