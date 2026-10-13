"""Pydantic schemas of the HTTP API (request validation + OpenAPI documentation).

Request models reject ``NaN``/``inf`` and blank names so that every client mistake is
answered with a 422 carrying a precise message instead of reaching the domain.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

M = TypeVar("M", bound=BaseModel)

STRICT_INPUT = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)


class PositionOut(BaseModel):
    code: str
    libelle: str
    description: str
    etapes: list[str]


class PlayerOut(BaseModel):
    id: str
    nom: str
    club: str
    nationalite: str
    poste: str
    attributs: dict[str, float]


class EvaluationRequest(BaseModel):
    model_config = STRICT_INPUT

    position: str = Field(..., min_length=1, description="Code du poste, ex. `attaquant`.")
    player_id: str = Field(
        ..., min_length=1, description="Identifiant du joueur dans le référentiel."
    )
    trace: bool = Field(False, description="Inclure le détail des règles déclenchées.")


class AdHocEvaluationRequest(BaseModel):
    model_config = ConfigDict(
        allow_inf_nan=False,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "position": "attaquant",
                "name": "Candidat test",
                "attributes": {
                    "buts_p90": 0.62,
                    "xg_p90": 0.55,
                    "tirs_cadres_pct": 49,
                    "passes_cles_p90": 1.4,
                    "vitesse_max_kmh": 34.6,
                    "distance_km_p90": 10.4,
                    "duels_aeriens_pct": 52,
                    "taille_cm": 184,
                    "age": 24,
                    "minutes_jouees": 2600,
                    "blessures_jours": 10,
                },
            }
        },
    )

    position: str = Field(..., min_length=1)
    attributes: dict[str, float] = Field(
        ..., description="Statistiques du candidat (noms des variables linguistiques)."
    )
    name: str = Field("Candidat ad hoc", min_length=1)
    trace: bool = False


class RankingRequestIn(BaseModel):
    model_config = STRICT_INPUT

    position: str = Field(..., min_length=1)
    limit: int | None = Field(None, ge=1)
    max_age: float | None = None
    max_market_value: float | None = None
    min_minutes: float | None = None
    natural_position_only: bool = False
    nationality: str | None = None
    trace: bool = False


class AtomOut(BaseModel):
    atome: str
    degre: float


class FiredRuleOut(BaseModel):
    id: str
    force: float
    verite_antecedent: float
    regle: str
    description: str
    atomes: list[AtomOut]


class StageOut(BaseModel):
    systeme: str
    entrees: dict[str, float]
    entrees_floues: dict[str, dict[str, float]]
    regles_declenchees: list[FiredRuleOut]
    nb_regles_declenchees: int
    nb_regles: int
    sorties: dict[str, float]
    sorties_floues: dict[str, dict[str, float]]
    avertissements: list[str]


class EvaluationOut(BaseModel):
    joueur: PlayerOut
    poste: str
    aptitude: float
    aptitude_label: str
    scores: dict[str, float]
    labels: dict[str, str]
    avertissements: list[str]
    etapes: list[StageOut] | None = None


class RankingEntryOut(EvaluationOut):
    rang: int


class SkippedOut(BaseModel):
    id: str
    nom: str
    raison: str


class RankingOut(BaseModel):
    poste: PositionOut
    filtres: list[str]
    candidats: int
    classes: int
    classement: list[RankingEntryOut]
    exclus: list[SkippedOut]


class KnowledgeStageOut(BaseModel):
    nom: str
    entrees: list[str]
    sorties: list[str]
    regles: int


class KnowledgeOut(BaseModel):
    poste: str
    entrees_requises: list[str]
    nb_regles: int
    etapes: list[KnowledgeStageOut]


class ErrorOut(BaseModel):
    detail: str


def as_model(model: type[M], data: dict[str, Any]) -> M:
    """Validate a presenter dictionary against a response schema."""
    return model.model_validate(data)
