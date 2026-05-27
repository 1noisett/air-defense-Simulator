import math

import pytest
from dataclasses import FrozenInstanceError

from physics.vector import Vector2D


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def v_3_4() -> Vector2D:
    return Vector2D(3.0, 4.0)


@pytest.fixture
def v_1_2() -> Vector2D:
    return Vector2D(1.0, 2.0)


@pytest.fixture
def v_neg() -> Vector2D:
    return Vector2D(-2.0, 5.0)


# ---------------------------------------------------------------------------
# Addition
# ---------------------------------------------------------------------------

def test_add_returns_new_instance(v_1_2: Vector2D, v_neg: Vector2D) -> None:
    result = v_1_2 + v_neg
    assert result is not v_1_2
    assert result is not v_neg


def test_add_components(v_1_2: Vector2D, v_neg: Vector2D) -> None:
    # (1, 2) + (-2, 5) = (-1, 7)
    result = v_1_2 + v_neg
    assert result == Vector2D(-1.0, 7.0)


def test_add_identity(v_1_2: Vector2D) -> None:
    zero = Vector2D(0.0, 0.0)
    assert v_1_2 + zero == v_1_2


def test_add_commutativity(v_1_2: Vector2D, v_neg: Vector2D) -> None:
    assert v_1_2 + v_neg == v_neg + v_1_2


# ---------------------------------------------------------------------------
# Subtraction
# ---------------------------------------------------------------------------

def test_sub_components(v_1_2: Vector2D, v_neg: Vector2D) -> None:
    # (1, 2) - (-2, 5) = (3, -3)
    result = v_1_2 - v_neg
    assert result == Vector2D(3.0, -3.0)


def test_sub_self_gives_zero(v_1_2: Vector2D) -> None:
    result = v_1_2 - v_1_2
    assert result == Vector2D(0.0, 0.0)


def test_sub_returns_new_instance(v_1_2: Vector2D, v_neg: Vector2D) -> None:
    result = v_1_2 - v_neg
    assert result is not v_1_2


# ---------------------------------------------------------------------------
# Scalar multiplication
# ---------------------------------------------------------------------------

def test_mul_scales_components(v_1_2: Vector2D) -> None:
    # (1, 2) * 3 = (3, 6)
    result = v_1_2 * 3.0
    assert result == Vector2D(3.0, 6.0)


def test_rmul_commutative(v_1_2: Vector2D) -> None:
    # 3 * v should equal v * 3
    assert 3.0 * v_1_2 == v_1_2 * 3.0


def test_mul_by_zero(v_1_2: Vector2D) -> None:
    assert v_1_2 * 0.0 == Vector2D(0.0, 0.0)


def test_mul_by_one(v_1_2: Vector2D) -> None:
    assert v_1_2 * 1.0 == v_1_2


def test_mul_by_negative(v_1_2: Vector2D) -> None:
    result = v_1_2 * -1.0
    assert result == Vector2D(-1.0, -2.0)


def test_mul_returns_new_instance(v_1_2: Vector2D) -> None:
    result = v_1_2 * 2.0
    assert result is not v_1_2


# ---------------------------------------------------------------------------
# Dot product
# ---------------------------------------------------------------------------

def test_dot_analytical(v_1_2: Vector2D, v_neg: Vector2D) -> None:
    # (1)(−2) + (2)(5) = −2 + 10 = 8
    assert v_1_2.dot(v_neg) == pytest.approx(8.0)


def test_dot_perpendicular_vectors_is_zero() -> None:
    # (1, 0) ⊥ (0, 1) — canonical orthogonal pair
    horizontal = Vector2D(1.0, 0.0)
    vertical = Vector2D(0.0, 1.0)
    assert horizontal.dot(vertical) == pytest.approx(0.0, abs=1e-15)


def test_dot_with_self_equals_norm_squared(v_3_4: Vector2D) -> None:
    # v · v = |v|²  →  (3,4) · (3,4) = 25
    assert v_3_4.dot(v_3_4) == pytest.approx(25.0)


def test_dot_commutative(v_1_2: Vector2D, v_neg: Vector2D) -> None:
    assert v_1_2.dot(v_neg) == pytest.approx(v_neg.dot(v_1_2))


# ---------------------------------------------------------------------------
# Norm
# ---------------------------------------------------------------------------

def test_norm_3_4_is_exactly_5(v_3_4: Vector2D) -> None:
    # Pythagorean triple: sqrt(3² + 4²) = sqrt(25) = 5 — exact in IEEE 754
    assert v_3_4.norm() == 5.0


def test_norm_unit_vector() -> None:
    assert Vector2D(1.0, 0.0).norm() == pytest.approx(1.0)


def test_norm_zero_vector() -> None:
    assert Vector2D(0.0, 0.0).norm() == 0.0


def test_norm_negative_components() -> None:
    # sqrt((-3)² + (-4)²) = 5
    assert Vector2D(-3.0, -4.0).norm() == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def test_normalize_produces_unit_vector(v_3_4: Vector2D) -> None:
    unit = v_3_4.normalize()
    assert math.isclose(unit.norm(), 1.0, rel_tol=1e-9)


def test_normalize_preserves_direction(v_3_4: Vector2D) -> None:
    unit = v_3_4.normalize()
    # unit = (3/5, 4/5)
    assert unit.x == pytest.approx(3.0 / 5.0)
    assert unit.y == pytest.approx(4.0 / 5.0)


def test_normalize_axis_aligned() -> None:
    v = Vector2D(7.0, 0.0)
    unit = v.normalize()
    assert unit == pytest.approx(Vector2D(1.0, 0.0))


def test_normalize_zero_vector_raises() -> None:
    with pytest.raises(ValueError, match="zero vector"):
        Vector2D(0.0, 0.0).normalize()


def test_normalize_returns_new_instance(v_3_4: Vector2D) -> None:
    assert v_3_4.normalize() is not v_3_4


# ---------------------------------------------------------------------------
# Angle
# ---------------------------------------------------------------------------

def test_angle_positive_x_axis() -> None:
    # (1, 0) → 0 rad
    assert Vector2D(1.0, 0.0).angle() == pytest.approx(0.0)


def test_angle_positive_y_axis() -> None:
    # (0, 1) → π/2 rad
    assert Vector2D(0.0, 1.0).angle() == pytest.approx(math.pi / 2)


def test_angle_negative_x_axis() -> None:
    # (-1, 0) → π rad
    assert Vector2D(-1.0, 0.0).angle() == pytest.approx(math.pi)


def test_angle_negative_y_axis() -> None:
    # (0, -1) → -π/2 rad (atan2 convention)
    assert Vector2D(0.0, -1.0).angle() == pytest.approx(-math.pi / 2)


def test_angle_45_degrees() -> None:
    # (1, 1) → π/4 rad
    assert Vector2D(1.0, 1.0).angle() == pytest.approx(math.pi / 4)


def test_angle_zero_vector_raises() -> None:
    with pytest.raises(ValueError, match="zero vector"):
        Vector2D(0.0, 0.0).angle()


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

def test_frozen_x_raises(v_3_4: Vector2D) -> None:
    with pytest.raises(FrozenInstanceError):
        v_3_4.x = 99.0  # type: ignore[misc]


def test_frozen_y_raises(v_3_4: Vector2D) -> None:
    with pytest.raises(FrozenInstanceError):
        v_3_4.y = 99.0  # type: ignore[misc]


def test_operations_do_not_mutate_original(v_1_2: Vector2D) -> None:
    original_x, original_y = v_1_2.x, v_1_2.y
    _ = v_1_2 + Vector2D(10.0, 10.0)
    _ = v_1_2 * 100.0
    assert v_1_2.x == original_x
    assert v_1_2.y == original_y


# ---------------------------------------------------------------------------
# Perpendicular
# ---------------------------------------------------------------------------

def test_perpendicular_unit_x() -> None:
    # (1, 0) rotated 90° CCW → (0, 1)
    assert Vector2D(1.0, 0.0).perpendicular() == Vector2D(0.0, 1.0)


def test_perpendicular_unit_y() -> None:
    # (0, 1) rotated 90° CCW → (-1, 0)
    assert Vector2D(0.0, 1.0).perpendicular() == Vector2D(-1.0, 0.0)


def test_perpendicular_preserves_magnitude(v_3_4: Vector2D) -> None:
    assert math.isclose(v_3_4.perpendicular().norm(), v_3_4.norm(), rel_tol=1e-12)


def test_perpendicular_is_orthogonal(v_1_2: Vector2D) -> None:
    # v · perp(v) must be zero
    assert v_1_2.dot(v_1_2.perpendicular()) == pytest.approx(0.0, abs=1e-15)


def test_perpendicular_twice_is_negation(v_1_2: Vector2D) -> None:
    # Two 90° CCW rotations = 180° = negation
    assert v_1_2.perpendicular().perpendicular() == -v_1_2


def test_perpendicular_returns_new_instance(v_1_2: Vector2D) -> None:
    assert v_1_2.perpendicular() is not v_1_2


# ---------------------------------------------------------------------------
# Cross product
# ---------------------------------------------------------------------------

def test_cross_orthogonal_ccw_is_positive() -> None:
    # (1, 0) × (0, 1) = 1·1 − 0·0 = 1 > 0 (other is CCW from self)
    assert Vector2D(1.0, 0.0).cross(Vector2D(0.0, 1.0)) == pytest.approx(1.0)


def test_cross_orthogonal_cw_is_negative() -> None:
    # (0, 1) × (1, 0) = 0·0 − 1·1 = -1 < 0 (other is CW from self)
    assert Vector2D(0.0, 1.0).cross(Vector2D(1.0, 0.0)) == pytest.approx(-1.0)


def test_cross_parallel_vectors_is_zero() -> None:
    # (1, 0) × (1, 0) = 1·0 − 0·1 = 0
    assert Vector2D(1.0, 0.0).cross(Vector2D(1.0, 0.0)) == pytest.approx(0.0, abs=1e-15)


def test_cross_antiparallel_is_zero() -> None:
    # (1, 0) × (-1, 0) = 0
    assert Vector2D(1.0, 0.0).cross(Vector2D(-1.0, 0.0)) == pytest.approx(0.0, abs=1e-15)


def test_cross_antisymmetric(v_1_2: Vector2D, v_neg: Vector2D) -> None:
    # a × b = -(b × a)
    assert v_1_2.cross(v_neg) == pytest.approx(-v_neg.cross(v_1_2))


def test_cross_analytical(v_1_2: Vector2D, v_neg: Vector2D) -> None:
    # (1)(5) − (2)(−2) = 5 + 4 = 9
    assert v_1_2.cross(v_neg) == pytest.approx(9.0)
