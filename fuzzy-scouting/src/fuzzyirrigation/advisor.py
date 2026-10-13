"""Application service of the irrigation controller."""

from __future__ import annotations

from collections.abc import Iterable
from importlib import resources
from pathlib import Path

from fuzzyengine import FuzzySystem, load_system
from fuzzyirrigation.domain import IrrigationDecision, SensorReading


def default_knowledge_base() -> Path:
    return Path(str(resources.files("fuzzyirrigation"))) / "knowledge" / "irrigation.toml"


class IrrigationAdvisor:
    def __init__(self, system: FuzzySystem, minimum_minutes: float = 5.0) -> None:
        self._system = system
        self._minimum = minimum_minutes

    @classmethod
    def from_file(
        cls, path: str | Path | None = None, minimum_minutes: float = 5.0
    ) -> IrrigationAdvisor:
        return cls(load_system(path or default_knowledge_base()), minimum_minutes)

    @property
    def system(self) -> FuzzySystem:
        return self._system

    def decide(self, reading: SensorReading) -> IrrigationDecision:
        result = self._system.evaluate(reading.as_inputs())
        return IrrigationDecision(reading, result, self._minimum)

    def decide_many(self, readings: Iterable[SensorReading]) -> list[IrrigationDecision]:
        return [self.decide(reading) for reading in readings]
