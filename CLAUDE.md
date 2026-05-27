# Air Defense Simulation — Project Guide

Educational backend simulation of anti-aircraft defense systems. The goal is pedagogical clarity:
every design decision prioritizes understanding over performance. The physics engine is handwritten
from first principles using only the Python standard library.

---

## Directory Layout

```
physics/        # Pure math and domain entities — no I/O, no side effects
simulation/     # Simulation loop and event system (future)
tests/          # pytest test suite, mirrors physics/ structure
```

**Layer rules:**
- `physics/` must not import from `simulation/`.
- `tests/` imports from both but never runs production side effects.
- No file outside `physics/` may be imported by `physics/`.

---

## Language & Typing

- **Python 3.10+** required. Use `match`/`case`, `X | Y` union syntax, and `TypeAlias` where appropriate.
- **Every** function and method must carry full type hints: all parameters and the return type.
  `-> None` is explicit, not omitted. `Any` is forbidden unless wrapping an external boundary.
- Use `Final`, `ClassVar`, and `Literal` from `typing` where they add precision.
- Prefer `tuple[float, float]` over bare `tuple` for fixed-length pairs.

```python
# Correct
def kinetic_energy(mass: float, speed: float) -> float: ...

# Wrong — missing return type
def kinetic_energy(mass, speed): ...
```

---

## OOP Conventions

| Concept | Pattern |
|---|---|
| Geometric / physical vector | `@dataclass(frozen=True)` — immutable value object |
| Domain entity (missile, interceptor, radar) | Mutable class with explicit `__init__` |
| Abstract interface (Integrator, Sensor) | `abc.ABC` + `@abstractmethod` |

**Vectors** must be immutable. Arithmetic operations return new instances, never mutate in place.

```python
@dataclass(frozen=True)
class Vector2D:
    x: float  # meters
    y: float  # meters

    def __add__(self, other: "Vector2D") -> "Vector2D":
        return Vector2D(self.x + other.x, self.y + other.y)
```

---

## Standard Library Constraint

The `physics/` layer uses **only**:

```
math, dataclasses, typing, abc, functools, itertools
```

`numpy`, `scipy`, and any third-party package are **forbidden inside `physics/`**.
They may appear in `tests/` solely to compute reference values for analytical comparisons.

---

## Docstring Format

Use **Google style**. Every public class, method, and function must have a docstring that:

1. States what it computes (one line).
2. Lists `Args:` with name, type hint restatement, **SI unit**, and meaning.
3. Lists `Returns:` with type, SI unit, and meaning.
4. Adds a `Note:` block when the math is non-trivial: cite the formula, its assumptions, and O() complexity.

**SI units in use:** meters (m), seconds (s), meters per second (m/s), meters per second squared (m/s²), radians (rad), kilograms (kg), Newtons (N).

```python
def compute_range(v0: float, angle: float, g: float = 9.81) -> float:
    """Compute projectile horizontal range assuming flat terrain and no drag.

    Args:
        v0: Initial speed (m/s). Must be non-negative.
        angle: Launch angle above horizontal (rad). Domain: [0, π/2].
        g: Gravitational acceleration (m/s²). Defaults to 9.81.

    Returns:
        Horizontal distance at impact (m).

    Note:
        R = v0² · sin(2θ) / g  — valid only for vacuum, flat Earth.
        O(1) time and space.
    """
    return (v0 ** 2) * math.sin(2 * angle) / g
```

---

## Numerical Integration

Integration is **decoupled** from entities via the `Integrator` protocol.
Entities never call `self.position += velocity * dt` directly.

```python
from abc import ABC, abstractmethod

class Integrator(ABC):
    @abstractmethod
    def step(
        self,
        state: "State",
        derivative_fn: "DerivativeFn",
        dt: float,
    ) -> "State":
        """Advance state by one time step dt (s)."""
```

- **Start with `EulerIntegrator`** (explicit Euler, O(dt) error).
- The interface is intentionally compatible with `RK4Integrator` — adding it later requires zero
  changes to entity code.
- Entities receive an `Integrator` at construction time (constructor injection).

---

## Dimensionality

The simulation is **2D** (x horizontal, y vertical) for pedagogical simplicity.
This is a conscious, explicit tradeoff — not an oversight.

**Interface rule:** only use `Vector2D` concretely where 2D is a fundamental assumption.
Abstract interfaces (`Integrator`, `Sensor`) must not name 2D in their signatures so that
a 3D extension requires only new concrete types, not interface changes.

---

## Test-Driven Development

- Every module in `physics/` ships with a corresponding test file in `tests/`.
- Tests must validate against a **known analytical solution**, not just assert "no crash".
- Tolerance for floating-point comparisons: use `pytest.approx` with `abs` or `rel` tolerances
  justified by the expected numerical error of the integrator (e.g., O(dt) for Euler).
- No code in `physics/` is considered done until its analytical test passes.

```
# Naming convention
physics/kinematics.py  →  tests/test_kinematics.py
physics/ballistics.py  →  tests/test_ballistics.py
```

**Canonical test pattern:**

```python
def test_projectile_range_matches_analytical():
    # Analytical: R = v0² · sin(2θ) / g
    v0, angle = 100.0, math.pi / 4
    expected = (v0 ** 2) * math.sin(2 * angle) / 9.81
    assert compute_range(v0, angle) == pytest.approx(expected, rel=1e-9)
```

---

## Out of Scope (this stage)

- Visualization or rendering of any kind.
- File I/O, serialization, or persistence.
- Networking or real-time communication.
- 3D geometry (deferred, not abandoned).
- External dependencies in `physics/` (numpy, scipy, etc.).
