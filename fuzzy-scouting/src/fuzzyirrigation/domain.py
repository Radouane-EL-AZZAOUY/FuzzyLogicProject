"""Domain objects of the irrigation controller."""

from __future__ import annotations

from dataclasses import dataclass

from fuzzyengine import EvaluationResult

OUTPUT = "duree_arrosage"


@dataclass(frozen=True, slots=True)
class SensorReading:
    """One set of measurements for a plot."""

    humidite_sol: float
    temperature: float
    humidite_air: float
    pluie_prevue_mm: float
    plot: str = "parcelle"

    def __post_init__(self) -> None:
        for name in ("humidite_sol", "humidite_air"):
            value = getattr(self, name)
            if not 0 <= value <= 100:
                raise ValueError(f"{name} doit être un pourcentage entre 0 et 100 (reçu {value}).")
        if self.pluie_prevue_mm < 0:
            raise ValueError("La pluie prévue ne peut pas être négative.")

    def as_inputs(self) -> dict[str, float]:
        return {
            "humidite_sol": self.humidite_sol,
            "temperature": self.temperature,
            "humidite_air": self.humidite_air,
            "pluie_prevue_mm": self.pluie_prevue_mm,
        }


@dataclass(frozen=True, slots=True)
class IrrigationDecision:
    reading: SensorReading
    result: EvaluationResult
    minimum_minutes: float = 5.0
    """Below this duration, watering is not worth starting the pump."""

    @property
    def duration_minutes(self) -> float:
        return self.result.outputs[OUTPUT]

    @property
    def label(self) -> str:
        return self.result.label(OUTPUT)

    @property
    def should_irrigate(self) -> bool:
        return self.duration_minutes >= self.minimum_minutes

    @property
    def warnings(self) -> tuple[str, ...]:
        return self.result.warnings
