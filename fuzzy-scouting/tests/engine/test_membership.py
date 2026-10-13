import math

import pytest

from fuzzyengine import (
    DefinitionError,
    Gaussian,
    RampDown,
    RampUp,
    Singleton,
    Trapezoidal,
    Triangular,
    Universe,
    membership_from_spec,
)
from fuzzyengine.membership import MEMBERSHIP_REGISTRY


@pytest.mark.parametrize(
    ("x", "expected"),
    [(-1, 0.0), (0, 0.0), (2.5, 0.5), (5, 1.0), (7.5, 0.5), (10, 0.0), (11, 0.0)],
)
def test_triangular_values(x: float, expected: float) -> None:
    assert Triangular(0, 5, 10)(x) == pytest.approx(expected)


def test_triangular_with_vertical_edges() -> None:
    left = Triangular(0, 0, 10)  # peak at the left foot
    right = Triangular(0, 10, 10)  # peak at the right foot
    assert left(0) == 1.0 and left(5) == 0.5 and left(10) == 0.0
    assert right(10) == 1.0 and right(5) == 0.5 and right(0) == 0.0


@pytest.mark.parametrize(
    ("x", "expected"),
    [(0, 0.0), (1, 0.5), (2, 1.0), (3, 1.0), (4, 1.0), (5, 0.5), (6, 0.0)],
)
def test_trapezoidal_values(x: float, expected: float) -> None:
    assert Trapezoidal(0, 2, 4, 6)(x) == pytest.approx(expected)


def test_ramps_are_shoulders() -> None:
    up, down = RampUp(10, 20), RampDown(10, 20)
    assert up(0) == 0.0 and up(15) == 0.5 and up(100) == 1.0
    assert down(0) == 1.0 and down(15) == 0.5 and down(100) == 0.0
    for x in (0, 5, 10, 15, 20, 30):
        assert up(x) + down(x) == pytest.approx(1.0)


def test_gaussian_and_singleton() -> None:
    g = Gaussian(mean=50, sigma=10)
    assert g(50) == 1.0
    assert g(60) == pytest.approx(math.exp(-0.5))
    s = Singleton(3.0)
    assert s(3.0) == 1.0 and s(3.0001) == 0.0


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Triangular(5, 2, 10),
        lambda: Triangular(1, 1, 1),
        lambda: Trapezoidal(0, 3, 2, 6),
        lambda: Trapezoidal(2, 2, 2, 2),
        lambda: RampUp(5, 5),
        lambda: RampDown(6, 5),
        lambda: Gaussian(0, 0),
        lambda: Universe(10, 10),
    ],
)
def test_invalid_definitions_raise(factory) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(DefinitionError):
        factory()


def test_factory_builds_from_registry_names() -> None:
    assert set(MEMBERSHIP_REGISTRY) == {
        "triangle",
        "trapezoid",
        "ramp_up",
        "ramp_down",
        "gaussian",
        "singleton",
    }
    mf = membership_from_spec("TRIANGLE", [0, 5, 10])
    assert isinstance(mf, Triangular) and mf(5) == 1.0
    assert str(mf) == "triangle(0, 5, 10)"


def test_factory_rejects_unknown_shape_and_bad_arity() -> None:
    with pytest.raises(DefinitionError, match="inconnue"):
        membership_from_spec("hexagon", [1, 2])
    with pytest.raises(DefinitionError, match="paramètres"):
        membership_from_spec("triangle", [1, 2])


def test_universe_helpers() -> None:
    u = Universe(0, 10)
    assert u.width == 10 and u.midpoint == 5
    assert u.clamp(-3) == 0 and u.clamp(42) == 10 and u.clamp(4) == 4
    grid = u.grid(11)
    assert grid[0] == 0 and grid[-1] == 10 and len(grid) == 11
    with pytest.raises(DefinitionError):
        u.grid(1)
