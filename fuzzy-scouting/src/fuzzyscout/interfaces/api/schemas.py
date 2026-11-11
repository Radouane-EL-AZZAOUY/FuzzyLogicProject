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


class ObservationOut(BaseModel):
    """What was observed for one input: a value, an interval, a category or degrees."""

    type: str
    texte: str
    valeur: float | None = None
    min: float | None = None
    max: float | None = None
    terme: str | None = None
    degres: dict[str, float] | None = None


class StageOut(BaseModel):
    systeme: str
    entrees: dict[str, float]
    observations: dict[str, ObservationOut] = {}
    conclusions: dict[str, dict[str, float]] = {}
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


class TermOut(BaseModel):
    label: str
    forme: str
    points: list[tuple[float, float]]


class VariableOut(BaseModel):
    nom: str
    description: str
    unite: str
    univers: tuple[float, float]
    termes: list[TermOut]


class RuleOut(BaseModel):
    id: str
    regle: str
    description: str
    poids: float


class KnowledgeStageDetailOut(BaseModel):
    nom: str
    description: str
    entrees: list[str]
    sorties: list[str]
    regles: list[RuleOut]


class KnowledgeDetailOut(BaseModel):
    poste: PositionOut
    entrees_requises: list[str]
    etapes: list[KnowledgeStageDetailOut]


ObservationIn = float | str | tuple[float, float] | dict[str, float]
"""A number, a category or a textual interval (``"4.0..4.3"``), a ``[min, max]`` pair,
or ``{"min": .., "max": ..}`` / explicit degrees ``{"fort": 0.7, "moyenne": 0.3}``."""


class CommandEvaluationRequest(BaseModel):
    model_config = ConfigDict(
        allow_inf_nan=False,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "name": "Joueur observé",
                "observations": {
                    "vitesse_max_kmh": 34.6,
                    "temps_30m_s": "4.0..4.3",
                    "sprints_p90": "eleve",
                    "vitesse_changement_ms2": [4.5, 5.5],
                    "distance_deplacement_m": 10.8,
                    "temps_reaction_s": "court",
                    "tacles_p90": 2.9,
                    "tacles_reussis_pct": {"min": 68, "max": 76},
                    "fautes_p90": 1.1,
                },
            }
        },
    )

    observations: dict[str, ObservationIn] = Field(
        ..., description="Une observation par mesure : valeur précise, intervalle ou catégorie."
    )
    name: str = Field("Joueur observé", min_length=1)
    trace: bool = True


class CommandRankingRequest(BaseModel):
    model_config = STRICT_INPUT

    position: str | None = Field(
        None, description="Code du poste : seuls ses joueurs sont comparés (vide = tous)."
    )
    limit: int | None = Field(None, ge=1)


class DeducedVariableOut(BaseModel):
    valeur: float
    label: str
    degres: dict[str, float]


class CommandPlayerOut(BaseModel):
    id: str
    nom: str
    club: str
    nationalite: str
    poste: str


class CommandEvaluationOut(BaseModel):
    joueur: CommandPlayerOut
    niveau: int
    niveau_valeur: float
    variables: dict[str, DeducedVariableOut]
    degres_niveau: dict[str, float]
    observations: dict[str, ObservationOut]
    avertissements: list[str]
    etapes: list[StageOut] | None = None


class CommandRankingEntryOut(CommandEvaluationOut):
    rang: int


class CommandRankingOut(BaseModel):
    poste: PositionOut | None
    candidats: int
    classes: int
    classement: list[CommandRankingEntryOut]
    exclus: list[SkippedOut]


class CommandOut(BaseModel):
    code: str
    libelle: str
    chainage: str
    niveaux: int
    sortie: str
    variables_deduites: list[str]
    entrees_requises: list[str]
    etapes: list[KnowledgeStageDetailOut]
    variables: list[VariableOut]


class ErrorOut(BaseModel):
    detail: str


def as_model(model: type[M], data: dict[str, Any]) -> M:
    """Validate a presenter dictionary against a response schema."""
    return model.model_validate(data)
