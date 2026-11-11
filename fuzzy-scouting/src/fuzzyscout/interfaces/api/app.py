"""FastAPI application factory.

Run locally with ``fuzzyscout serve`` or
``uvicorn fuzzyscout.interfaces.api.app:create_app --factory``.

Design notes:

* handlers are plain ``def`` functions: FastAPI runs them in a thread pool, so the
  CPU-bound inference never blocks the event loop;
* the service is warmed up at start-up (knowledge bases validated, players loaded):
  a broken deployment fails immediately instead of on the first request, and the
  lazy caches are populated before any concurrent access.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from fuzzyengine import EvaluationError, FuzzyEngineError, parse_observation
from fuzzyscout import __version__
from fuzzyscout.application.rank_players import RankingRequest
from fuzzyscout.application.scout_command import ScoutCommand
from fuzzyscout.application.scouting_service import ScoutingService
from fuzzyscout.bootstrap import build_service
from fuzzyscout.config import Settings
from fuzzyscout.domain.errors import (
    DataSourceError,
    MissingAttributesError,
    PlayerNotFoundError,
    PositionNotFoundError,
    ScoutingError,
)
from fuzzyscout.domain.filters import RankingFilters
from fuzzyscout.interfaces import presenters
from fuzzyscout.interfaces.api import schemas

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
"""Static single-page web interface (served at ``/``, assets under ``/ui``)."""


def get_service(request: Request) -> ScoutingService:
    service: ScoutingService = request.app.state.service
    return service


Service = Annotated[ScoutingService, Depends(get_service)]


class CommandUnavailableError(ScoutingError):
    def __init__(self) -> None:
        super().__init__(
            "Le système de commande Scout n'est pas disponible : le répertoire des bases de "
            "connaissances ne contient pas de dossier « commande »."
        )


def get_command(svc: Service) -> ScoutCommand:
    if svc.command is None:
        raise CommandUnavailableError
    return svc.command


Command = Annotated[ScoutCommand, Depends(get_command)]


def _status_for(exc: ScoutingError) -> int:
    if isinstance(exc, PlayerNotFoundError | PositionNotFoundError | CommandUnavailableError):
        return 404
    if isinstance(exc, MissingAttributesError):
        return 422
    if isinstance(exc, DataSourceError):
        return 500  # server-side data problem, not the client's fault
    return 400


def create_app(
    service: ScoutingService | None = None,
    settings: Settings | None = None,
    warm_up: bool = True,
) -> FastAPI:
    app = FastAPI(
        title="Fuzzy Scouting API",
        version=__version__,
        description=(
            "Évaluation et classement de joueurs par logique floue. "
            "Chaque réponse peut inclure la trace des règles déclenchées (`trace=true`)."
        ),
    )
    app.state.service = service or build_service(settings)
    if warm_up:
        app.state.service.validate_knowledge()
        app.state.service.players()
        if app.state.service.command is not None:
            _ = app.state.service.command.pipeline

    @app.exception_handler(ScoutingError)
    def scouting_error_handler(_: Request, exc: ScoutingError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
        # Domain invariants (blank name, non-finite attribute...) are client errors.
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(EvaluationError)
    def evaluation_error_handler(_: Request, exc: EvaluationError) -> JSONResponse:
        # Unusable input (unknown category, inverted interval, non-numeric value...).
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(FuzzyEngineError)
    def engine_error_handler(_: Request, exc: FuzzyEngineError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": f"Erreur du moteur flou : {exc}"})

    @app.get("/health", tags=["système"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/positions", response_model=list[schemas.PositionOut], tags=["référentiel"])
    def positions(svc: Service) -> list[schemas.PositionOut]:
        return [
            schemas.as_model(schemas.PositionOut, presenters.position_to_dict(p))
            for p in svc.positions()
        ]

    @app.get("/players", response_model=list[schemas.PlayerOut], tags=["référentiel"])
    def players(svc: Service) -> list[schemas.PlayerOut]:
        return [
            schemas.as_model(schemas.PlayerOut, presenters.player_to_dict(p)) for p in svc.players()
        ]

    @app.get(
        "/players/{player_id}",
        response_model=schemas.PlayerOut,
        responses={404: {"model": schemas.ErrorOut}},
        tags=["référentiel"],
    )
    def player(player_id: str, svc: Service) -> schemas.PlayerOut:
        return schemas.as_model(schemas.PlayerOut, presenters.player_to_dict(svc.player(player_id)))

    @app.get("/knowledge", response_model=list[schemas.KnowledgeOut], tags=["système"])
    def knowledge(svc: Service) -> list[schemas.KnowledgeOut]:
        return [
            schemas.as_model(schemas.KnowledgeOut, item)
            for item in presenters.knowledge_to_dict(svc.validate_knowledge())
        ]

    @app.get(
        "/knowledge/{position}",
        response_model=schemas.KnowledgeDetailOut,
        responses={404: {"model": schemas.ErrorOut}},
        tags=["système"],
    )
    def knowledge_detail(position: str, svc: Service) -> schemas.KnowledgeDetailOut:
        return schemas.as_model(
            schemas.KnowledgeDetailOut, presenters.pipeline_to_dict(*svc.pipeline(position))
        )

    @app.get("/variables", response_model=list[schemas.VariableOut], tags=["référentiel"])
    def variables(svc: Service) -> list[schemas.VariableOut]:
        return [
            schemas.as_model(schemas.VariableOut, presenters.variable_to_dict(v))
            for v in svc.variables()
        ]

    @app.get("/", include_in_schema=False)
    def web_index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    app.mount("/ui", StaticFiles(directory=WEB_DIR), name="ui")

    @app.post(
        "/evaluations",
        response_model=schemas.EvaluationOut,
        responses={404: {"model": schemas.ErrorOut}, 422: {"model": schemas.ErrorOut}},
        tags=["évaluation"],
    )
    def evaluate(body: schemas.EvaluationRequest, svc: Service) -> schemas.EvaluationOut:
        evaluation = svc.evaluate(body.position, body.player_id)
        return schemas.as_model(
            schemas.EvaluationOut,
            presenters.evaluation_to_dict(evaluation, include_trace=body.trace),
        )

    @app.post(
        "/evaluations/ad-hoc",
        response_model=schemas.EvaluationOut,
        responses={404: {"model": schemas.ErrorOut}, 422: {"model": schemas.ErrorOut}},
        tags=["évaluation"],
    )
    def evaluate_ad_hoc(
        body: schemas.AdHocEvaluationRequest, svc: Service
    ) -> schemas.EvaluationOut:
        evaluation = svc.evaluate_attributes(body.position, body.attributes, body.name)
        return schemas.as_model(
            schemas.EvaluationOut,
            presenters.evaluation_to_dict(evaluation, include_trace=body.trace),
        )

    @app.post(
        "/rankings",
        response_model=schemas.RankingOut,
        responses={404: {"model": schemas.ErrorOut}},
        tags=["évaluation"],
    )
    def rank(body: schemas.RankingRequestIn, svc: Service) -> schemas.RankingOut:
        request = RankingRequest(
            position_code=body.position,
            filters=RankingFilters(
                max_age=body.max_age,
                max_market_value=body.max_market_value,
                min_minutes=body.min_minutes,
                natural_position_only=body.natural_position_only,
                nationality=body.nationality,
            ),
            limit=body.limit,
        )
        report = svc.rank(request)
        return schemas.as_model(
            schemas.RankingOut, presenters.ranking_to_dict(report, include_trace=body.trace)
        )

    @app.get(
        "/commande",
        response_model=schemas.CommandOut,
        responses={404: {"model": schemas.ErrorOut}},
        tags=["commande Scout"],
    )
    def command_system(command: Command) -> schemas.CommandOut:
        """Le système : étapes de déduction, règles lisibles et variables linguistiques."""
        return schemas.as_model(schemas.CommandOut, presenters.command_to_dict(command.pipeline))

    @app.post(
        "/commande/evaluations",
        response_model=schemas.CommandEvaluationOut,
        responses={404: {"model": schemas.ErrorOut}, 422: {"model": schemas.ErrorOut}},
        tags=["commande Scout"],
    )
    def command_evaluate(
        body: schemas.CommandEvaluationRequest, command: Command
    ) -> schemas.CommandEvaluationOut:
        """Cas 1 : un seul joueur, décrit par des observations précises ou floues."""
        observations = {name: parse_observation(raw) for name, raw in body.observations.items()}
        evaluation = command.evaluate_observations(observations, body.name)
        return schemas.as_model(
            schemas.CommandEvaluationOut,
            presenters.command_evaluation_to_dict(evaluation, include_trace=body.trace),
        )

    @app.get(
        "/commande/joueurs/{player_id}",
        response_model=schemas.CommandEvaluationOut,
        responses={404: {"model": schemas.ErrorOut}, 422: {"model": schemas.ErrorOut}},
        tags=["commande Scout"],
    )
    def command_player(player_id: str, command: Command) -> schemas.CommandEvaluationOut:
        """Cas 1 : un joueur du jeu de données, avec le détail du raisonnement."""
        return schemas.as_model(
            schemas.CommandEvaluationOut,
            presenters.command_evaluation_to_dict(
                command.evaluate_player(player_id), include_trace=True
            ),
        )

    @app.post(
        "/commande/classements",
        response_model=schemas.CommandRankingOut,
        responses={404: {"model": schemas.ErrorOut}},
        tags=["commande Scout"],
    )
    def command_rank(
        body: schemas.CommandRankingRequest, command: Command
    ) -> schemas.CommandRankingOut:
        """Cas 2 : les joueurs d'un même poste, classés par niveau."""
        report = command.rank(body.position or None, body.limit)
        return schemas.as_model(
            schemas.CommandRankingOut, presenters.command_ranking_to_dict(report)
        )

    return app
