"""Interactive matplotlib-widgets front-end for the air-defense simulator.

A 'configure and fire' window: the user sets scenario parameters with sliders,
clicks Run, the simulation executes headless, and the recorded trajectories are
animated in the main axis. Parameters can be changed and re-run without closing
the window.

This module is the only interactive (GUI) layer. It imports from the engine but
the engine knows nothing about it (zero coupling). It deliberately does NOT call
TrajectoryPlotter.plot_static / .animate: those force the non-interactive 'Agg'
backend, which would break the live window. Instead it runs its own
FuncAnimation on its own axis and relies on the default GUI backend (never calls
matplotlib.use).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Rectangle
from matplotlib.widgets import Button, Slider

from battery.assessment import ThreatAssessment
from battery.assignment import GreedyAssignment
from battery.controller import BatteryController
from battery.report import Disposition, EngagementReport
from battery.zone import RectangularZone
from physics.integrator import EulerIntegrator
from physics.threat import Threat
from physics.vector import Vector2D
from sensors.radar import Radar
from sensors.tracker import ThreatTracker
from simulation.conditions import all_threats_resolved_stop
from simulation.recorder import Snapshot, TrajectoryRecorder
from simulation.runner import SimulationRunner
from visualization.renderer import ZoneBounds  # public type alias — safe to reuse

# --- Simulation constants ---------------------------------------------------
DT: float = 0.01
MAX_TIME: float = 35.0
GRAVITY: float = 9.81
THREAT_SPEED: float = 100.0      # m/s — fixed launch speed for all threats
THREAT_SPACING: float = 300.0    # m — horizontal gap between threat launch points
BATTERY_OFFSET: float = 200.0    # m — battery sits this far right of the zone centre
RADAR_RANGE: float = 6000.0      # m — large enough to see the whole field
FRAME_STEP: int = 5              # keep every Nth snapshot for the animation

# --- Interceptor / battery constants ---------------------------------------
LAUNCH_SPEED: float = 400.0
KILL_RADIUS: float = 8.0         # 8 m absorbs the one-frame lag in kill detection
INTERCEPTOR_MAX_ACCEL: float = 400.0
ASSOCIATION_RADIUS: float = 10.0

# --- Slider defaults --------------------------------------------------------
DEFAULT_N_THREATS: int = 3
DEFAULT_INVENTORY: int = 2
DEFAULT_ANGLE: float = 45.0
DEFAULT_PN_N: float = 4.0
DEFAULT_ZONE_WIDTH: float = 350.0

# Geometric honesty: parabolic symmetry and PN curvature must read true, so the
# main axis defaults to equal scaling (consistent with Blocks 3 and 4). For
# scenarios where the vertical extent looks badly compressed, change this single
# constant to "auto" — no logic depends on the value.
MAIN_AXIS_ASPECT: str = "equal"

# Colour cycle. Duplicated from visualization.renderer._COLOURS (a private name);
# duplicating the short literal keeps this module independent of renderer
# internals rather than importing an underscore-prefixed symbol.
_COLOURS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231",
    "#911eb4", "#42d4f4", "#f032e6", "#bfef45",
]


def _draw_zone(ax: object, zone_bounds: ZoneBounds) -> None:
    """Shade a rectangular protected zone behind the trajectories.

    Duplicated from visualization.renderer._draw_zone (private). Minimal copy so
    this GUI module does not depend on a renderer internal.

    Args:
        ax: Matplotlib Axes to draw on.
        zone_bounds: (x_min, x_max, y_min, y_max) of the zone (m).
    """
    x_min, x_max, y_min, y_max = zone_bounds
    ax.add_patch(  # type: ignore[attr-defined]
        Rectangle(
            (x_min, y_min),
            x_max - x_min,
            y_max - y_min,
            facecolor="#d62728",
            edgecolor="#d62728",
            alpha=0.18,
            zorder=0,
            label="protected zone",
        )
    )


def _subsample(trajectory: list[Snapshot], step: int) -> list[Snapshot]:
    """Return every `step`-th snapshot, always including the last."""
    if not trajectory:
        return []
    indices = list(range(0, len(trajectory), step))
    if indices[-1] != len(trajectory) - 1:
        indices.append(len(trajectory) - 1)
    return [trajectory[i] for i in indices]


@dataclass(frozen=True)
class _Params:
    """Typed snapshot of the slider values at one instant."""

    n_threats: int
    inventory: int
    angle_deg: float
    pn_n: float
    zone_width: float


class InteractiveSimulator:
    """A 'configure and fire' matplotlib window for defense scenarios.

    Builds the figure, axes and widgets in __init__ (runs nothing). Each Run
    click reads the sliders, constructs a fresh scenario, simulates it headless,
    animates the result in the main axis and updates the status panel — all
    without closing the window.
    """

    def __init__(self) -> None:
        """Construct the figure, main axis, sliders, buttons and status panel.

        Connects callbacks. Does not run any simulation.
        """
        self.fig = plt.figure(figsize=(13, 9))
        manager = self.fig.canvas.manager
        if manager is not None:
            manager.set_window_title("Air Defense - Interactive Simulator")

        self.ax_main = self.fig.add_axes((0.07, 0.34, 0.90, 0.60))

        # --- Sliders (left-centre column) --------------------------------
        self.s_threats = Slider(
            self.fig.add_axes((0.26, 0.255, 0.46, 0.02)),
            "Threats (1-5)", 1, 5, valinit=DEFAULT_N_THREATS, valstep=1,
        )
        self.s_inventory = Slider(
            self.fig.add_axes((0.26, 0.210, 0.46, 0.02)),
            "Interceptors (0-5)", 0, 5, valinit=DEFAULT_INVENTORY, valstep=1,
        )
        self.s_angle = Slider(
            self.fig.add_axes((0.26, 0.165, 0.46, 0.02)),
            "Launch angle (deg)", 15, 75, valinit=DEFAULT_ANGLE, valstep=1,
        )
        self.s_pn = Slider(
            self.fig.add_axes((0.26, 0.120, 0.46, 0.02)),
            "PN constant N", 2.0, 6.0, valinit=DEFAULT_PN_N,
        )
        self.s_zone = Slider(
            self.fig.add_axes((0.26, 0.075, 0.46, 0.02)),
            "Zone width (m)", 100, 1000, valinit=DEFAULT_ZONE_WIDTH, valstep=10,
        )

        # --- Buttons ------------------------------------------------------
        self.b_run = Button(self.fig.add_axes((0.80, 0.255, 0.085, 0.045)), "Run simulation")
        self.b_reset = Button(self.fig.add_axes((0.895, 0.255, 0.085, 0.045)), "Reset")
        self.b_run.on_clicked(self._on_run_clicked)
        self.b_reset.on_clicked(self._on_reset_clicked)

        # --- Status panel -------------------------------------------------
        self.ax_status = self.fig.add_axes((0.79, 0.05, 0.20, 0.17))
        self.ax_status.axis("off")
        self._status_artist = self.ax_status.text(
            0.0, 1.0, "", va="top", ha="left", fontsize=9, family="monospace",
            transform=self.ax_status.transAxes,
        )

        self._anim: FuncAnimation | None = None
        self._run_count: int = 0

        self._decorate_axis(None)

    # ----------------------------------------------------------------- lifecycle

    def show(self) -> None:
        """Launch the interactive window (blocks until the user closes it)."""
        plt.show(block=True)

    # ------------------------------------------------------------------ callbacks

    def _on_run_clicked(self, event: object) -> None:
        """Read sliders, build + run a scenario headless, report, then animate."""
        params = self._read_params()
        self._set_status("Running...")

        threats, controller, zone_bounds = self._build_scenario(params)
        recorder = TrajectoryRecorder()
        entities: dict = dict(threats)
        result = SimulationRunner(
            entities=entities,
            dt=DT,
            max_time=MAX_TIME,
            recorder=recorder,
            controller=controller,
            stop_condition=all_threats_resolved_stop(controller),
        ).run()
        report = controller.report()

        self._run_count += 1
        self._set_status(
            self._format_report(report, result.outcome.value, result.final_time)
        )
        self._animate_result(recorder, zone_bounds)

    def _on_reset_clicked(self, event: object) -> None:
        """Stop any animation, clear the axis, restore sliders, blank the panel."""
        self._stop_animation()
        self.ax_main.cla()
        self._decorate_axis(None)
        for slider in (self.s_threats, self.s_inventory, self.s_angle,
                       self.s_pn, self.s_zone):
            slider.reset()
        self._set_status("")
        self.fig.canvas.draw_idle()

    # -------------------------------------------------------------------- helpers

    def _read_params(self) -> _Params:
        """Read the sliders, casting the integer-valued ones to int."""
        return _Params(
            n_threats=int(round(self.s_threats.val)),
            inventory=int(round(self.s_inventory.val)),
            angle_deg=float(self.s_angle.val),
            pn_n=float(self.s_pn.val),
            zone_width=float(self.s_zone.val),
        )

    def _build_scenario(
        self, params: _Params
    ) -> tuple[dict[str, Threat], BatteryController, ZoneBounds]:
        """Build fresh threats + subsystems + controller from params.

        Every object is newly constructed, so no state leaks between runs.

        Args:
            params: Current slider values.

        Returns:
            (threats by id, configured BatteryController, protected-zone bounds).

        Note:
            Threats are equispaced in x at THREAT_SPACING, all launched at
            THREAT_SPEED and the given angle, so they share range
            R = v²·sin(2θ)/g. The zone is centred on the impact centroid
            x_center = R + THREAT_SPACING·(n-1)/2; the battery sits BATTERY_OFFSET
            to its right.
        """
        integrator = EulerIntegrator()
        angle_rad = math.radians(params.angle_deg)
        vx = THREAT_SPEED * math.cos(angle_rad)
        vy = THREAT_SPEED * math.sin(angle_rad)
        rng = THREAT_SPEED ** 2 * math.sin(2.0 * angle_rad) / GRAVITY

        threats: dict[str, Threat] = {}
        for i in range(params.n_threats):
            tid = f"threat_{i + 1:03d}"
            threats[tid] = Threat(
                Vector2D(i * THREAT_SPACING, 0.0), Vector2D(vx, vy), integrator
            )

        x_center = rng + THREAT_SPACING * (params.n_threats - 1) / 2.0
        half = params.zone_width / 2.0
        zone = RectangularZone(x_center - half, x_center + half, 0.0, 30.0)
        launch_site = Vector2D(x_center + BATTERY_OFFSET, 0.0)

        controller = BatteryController(
            threats=threats,
            radar=Radar(launch_site, RADAR_RANGE),
            tracker=ThreatTracker(association_radius=ASSOCIATION_RADIUS),
            assessment=ThreatAssessment(zone),
            assignment=GreedyAssignment(),
            zone=zone,
            integrator=integrator,
            launch_site=launch_site,
            inventory=params.inventory,
            launch_speed=LAUNCH_SPEED,
            kill_radius=KILL_RADIUS,
            interceptor_N=params.pn_n,
            interceptor_max_accel=INTERCEPTOR_MAX_ACCEL,
        )
        zone_bounds: ZoneBounds = (zone.x_min, zone.x_max, zone.y_min, zone.y_max)
        return threats, controller, zone_bounds

    def _animate_result(
        self, recorder: TrajectoryRecorder, zone_bounds: ZoneBounds
    ) -> None:
        """Animate the recorded trajectories on the main axis.

        Stops and discards any previous animation first, then rebuilds artists on
        a cleared axis. The new FuncAnimation is kept on self._anim (a live
        reference is mandatory or it is garbage-collected and never plays).
        """
        self._stop_animation()
        ax = self.ax_main
        ax.cla()

        ids = recorder.get_all_ids()
        trajectories: dict[str, list[Snapshot]] = {
            eid: _subsample(recorder.get_trajectory(eid), FRAME_STEP) for eid in ids
        }

        all_x = [s.position.x for tr in trajectories.values() for s in tr]
        all_y = [s.position.y for tr in trajectories.values() for s in tr]
        if all_x:
            x_pad = (max(all_x) - min(all_x)) * 0.05 or 50.0
            y_pad = (max(all_y) - min(all_y)) * 0.05 or 50.0
            x_lim = (min(all_x) - x_pad, max(all_x) + x_pad)
            y_lim = (min(min(all_y) - y_pad, -10.0), max(all_y) + y_pad)
        else:
            x_lim, y_lim = None, None

        self._decorate_axis(zone_bounds, x_lim, y_lim)

        trails: dict[str, object] = {}
        markers: dict[str, object] = {}
        for idx, eid in enumerate(ids):
            colour = _COLOURS[idx % len(_COLOURS)]
            (trail,) = ax.plot([], [], color=colour, linewidth=1.5, label=eid)
            (marker,) = ax.plot(
                [], [], marker="o", color=colour, markersize=7,
                linestyle="None", zorder=5,
            )
            trails[eid] = trail
            markers[eid] = marker
        ax.legend(loc="upper right", fontsize=8)

        max_frames = max((len(t) for t in trajectories.values()), default=1)
        ref = max(trajectories.values(), key=len) if trajectories else []

        def _update(frame: int) -> tuple:
            if ref:
                ax.set_title(f"t = {ref[min(frame, len(ref) - 1)].time:.2f} s")
            for eid in ids:
                tr = trajectories[eid]
                i = min(frame, len(tr) - 1)
                trails[eid].set_data(  # type: ignore[union-attr]
                    [s.position.x for s in tr[: i + 1]],
                    [s.position.y for s in tr[: i + 1]],
                )
                markers[eid].set_data(  # type: ignore[union-attr]
                    [tr[i].position.x], [tr[i].position.y]
                )
            return ()

        self._anim = FuncAnimation(
            self.fig, _update, frames=max_frames, interval=50,
            blit=False, repeat=False,
        )
        self.fig.canvas.draw_idle()

    def _decorate_axis(
        self,
        zone_bounds: ZoneBounds | None,
        x_lim: tuple[float, float] | None = None,
        y_lim: tuple[float, float] | None = None,
    ) -> None:
        """Re-apply labels, grid, ground line, limits and zone after an ax.cla()."""
        ax = self.ax_main
        if zone_bounds is not None:
            _draw_zone(ax, zone_bounds)
        ax.axhline(0, color="gray", linewidth=0.5)
        ax.set_xlabel("Horizontal position (m)")
        ax.set_ylabel("Altitude (m)")
        ax.grid(True, linewidth=0.4, alpha=0.6)
        ax.set_xlim(*(x_lim if x_lim is not None else (0.0, 2200.0)))
        ax.set_ylim(*(y_lim if y_lim is not None else (-10.0, 600.0)))
        ax.set_aspect(MAIN_AXIS_ASPECT)
        if zone_bounds is None:
            ax.set_title("Set parameters and press Run")

    def _format_report(
        self, report: EngagementReport, outcome: str, final_time: float
    ) -> str:
        """Build the multi-line status text from the engagement report."""
        counts = Counter(tr.disposition for tr in report.threats.values())
        return (
            f"Run #{self._run_count}\n"
            f"Outcome: {outcome}\n"
            f"Sim time: {final_time:.2f} s\n"
            f"\n"
            f"Neutralized:   {counts[Disposition.NEUTRALIZED]}\n"
            f"Leaked (zone): {counts[Disposition.IMPACTED_PROTECTED_ZONE]}\n"
            f"Safe (outside):{counts[Disposition.IMPACTED_GROUND_SAFE]}\n"
            f"In-flight:     {counts[Disposition.IN_FLIGHT]}\n"
            f"\n"
            f"Inventory left:{report.inventory_remaining}"
        )

    def _set_status(self, text: str) -> None:
        """Write text into the status panel and request a redraw."""
        self._status_artist.set_text(text)
        self.fig.canvas.draw_idle()

    def _stop_animation(self) -> None:
        """Stop and drop the current FuncAnimation, if any."""
        if self._anim is not None:
            self._anim.event_source.stop()
            self._anim = None
