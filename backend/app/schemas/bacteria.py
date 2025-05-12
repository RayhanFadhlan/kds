from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BacteriaBase(BaseModel):
    name: str
    superkingdom: Optional[str] = None
    kingdom: Optional[str] = None
    phylum: Optional[str] = None
    class_name: Optional[str] = None
    order: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None
    species: Optional[str] = None
    strain: Optional[str] = None
    gram_stain: Optional[str] = None
    shape: Optional[str] = None
    mobility: Optional[bool] = None
    flagellar_presence: Optional[bool] = None
    number_of_membranes: Optional[str] = None
    oxygen_preference: Optional[str] = None
    optimal_temperature: Optional[float] = None
    temperature_range: Optional[str] = None
    habitat: Optional[str] = None
    biotic_relationship: Optional[str] = None
    cell_arrangement: Optional[str] = None
    sporulation: Optional[bool] = None
    metabolism: Optional[str] = None
    energy_source: Optional[str] = None
    is_pathogen: Optional[bool] = False


class BacteriaCreate(BacteriaBase):
    bacteria_id: str = Field(..., description="Unique identifier for the bacteria")


class BacteriaUpdate(BacteriaBase):
    name: Optional[str] = None
    is_pathogen: Optional[bool] = None


class BacteriaResponse(BacteriaBase):
    id: int
    bacteria_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class PredictionResponse(BaseModel):
    bacteria_id: str
    name: str
    is_pathogen: bool
    confidence: float = Field(..., description="Confidence score of the prediction")
    model_version: str = Field(..., description="Version of the ML model used")
