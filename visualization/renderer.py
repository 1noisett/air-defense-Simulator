from __future__ import annotations

from simulation.recorder import Snapshot, TrajectoryRecorder

_WRITERS = {".gif": "pillow", ".mp4": "ffmpeg"}

ZoneBounds = tuple[float, float, float, float]
"""(x_min, x_max, y_min, y_max) of a rectangular region to overlay (m)."""


def _draw_zone(ax: object, zone_bounds: ZoneBounds) -> None:
    """Shade a rectangular protected zone behind the trajectories.

    Args:
        ax: A matplotlib Axes to draw on.
        zone_bounds: (x_min, x_max, y_min, y_max) of the zone (m).

    Note:
        Plain bounds are accepted (not a battery.ProtectedZone) so the renderer
        stays independent of the battery layer.
    """
    from matplotlib.patches import Rectangle

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

# Colour cycle for up to N entities; falls back to matplotlib's default beyond that.
_COLOURS = [
    "#e6194b",  # red    — threat
    "#3cb44b",  # green  — interceptor
    "#4363d8",  # blue
    "#f58231",  # orange
    "#911eb4",  # purple
    "#42d4f4",  # cyan
    "#f032e6",  # magenta
    "#bfef45",  # lime
]


class TrajectoryPlotter:
    """Produces static plots and animations from a completed TrajectoryRecorder.

    Operates entirely on Snapshot data — it never touches live Entity objects.
    This is the only layer in the project that imports matplotlib; all other
    modules remain independent of any visualisation library.

    Matplotlib is imported lazily inside each method so that the class can be
    imported in headless environments without error, as long as neither
    plot_static nor animate is called.

    Args:
        recorder: A populated TrajectoryRecorder. Assumed complete (simulation
            already ran). Mutating the recorder after construction yields
            undefined plot results.
    """

    def __init__(self, recorder: TrajectoryRecorder) -> None:
        """Bind the plotter to a completed trajectory recorder.

        Args:
            recorder: Source of snapshot data. Must have at least one entity
                with at least one snapshot; otherwise plot_static raises ValueError.
        """
        self._recorder = recorder

    def plot_static(
        self,
        title: str = "Trajectory Plot",
        filepath: str | None = None,
        zone_bounds: ZoneBounds | None = None,
    ) -> None:
        """Render all trajectories as a 2-D position plot.

        Draws one polyline per entity labelled with its entity_id. Start and
        end positions are marked with distinct symbols. Axes are in meters with
        equal aspect ratio so trajectories are geometrically correct.

        Args:
            title: Text displayed as the figure title.
            filepath: Destination path for the saved image (e.g. "out/plot.png").
                Any format supported by matplotlib.savefig is accepted (.png,
                .pdf, .svg, …). If None, calls plt.show() — opens an interactive
                window.
            zone_bounds: Optional (x_min, x_max, y_min, y_max) of a protected zone
                to shade behind the trajectories (m). None draws no zone.

        Raises:
            ValueError: If the recorder contains no entities.

        Note:
            Reads only .position from each snapshot. Velocity data is ignored.
            O(N) where N is the total number of snapshots across all entities.
        """
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend; safe when filepath is given
        import matplotlib.pyplot as plt

        ids = self._recorder.get_all_ids()
        if not ids:
            raise ValueError("TrajectoryRecorder contains no recorded entities.")

        fig, ax = plt.subplots(figsize=(10, 6))

        if zone_bounds is not None:
            _draw_zone(ax, zone_bounds)

        for idx, entity_id in enumerate(ids):
            trajectory: list[Snapshot] = self._recorder.get_trajectory(entity_id)
            if not trajectory:
                continue

            colour = _COLOURS[idx % len(_COLOURS)]
            xs = [snap.position.x for snap in trajectory]
            ys = [snap.position.y for snap in trajectory]

            # Full trajectory line
            ax.plot(xs, ys, color=colour, linewidth=1.5, label=entity_id)

            # Start marker: filled circle
            ax.plot(xs[0], ys[0], marker="o", color=colour, markersize=8,
                    zorder=5, linestyle="None")

            # End marker: X
            ax.plot(xs[-1], ys[-1], marker="x", color=colour, markersize=10,
                    markeredgewidth=2.5, zorder=5, linestyle="None")

        # Ground line
        ax.axhline(0, color="gray", linewidth=0.5)

        ax.set_aspect("equal")
        ax.set_xlabel("Horizontal position (m)")
        ax.set_ylabel("Altitude (m)")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, linewidth=0.4, alpha=0.6)

        fig.tight_layout()

        if filepath is None:
            plt.show()
        else:
            fig.savefig(filepath, dpi=150)

        plt.close(fig)

    def animate(
        self,
        interval_ms: int = 50,
        filepath: str | None = None,
        zone_bounds: ZoneBounds | None = None,
    ) -> None:
        """Produce a frame-by-frame animation of all entity trajectories.

        Each animation frame corresponds to one recorded snapshot. Entities
        are drawn as moving filled-circle markers; a trailing polyline shows
        the path flown so far. The figure title displays the real simulation
        time taken from the snapshot's .time field — no assumption is made
        about uniform dt between snapshots.

        Axis limits are computed from the full trajectory before animation
        starts, so the view never pans or zooms during playback.

        Args:
            interval_ms: Delay between frames in milliseconds (ms).
                Controls playback speed only; does not affect physics fidelity.
                Defaults to 50 ms (≈ 20 fps).
            filepath: Destination path for the saved animation.
                ".gif" → writer='pillow' (Pillow must be installed).
                ".mp4" → writer='ffmpeg' (ffmpeg binary must be on PATH);
                    raises RuntimeError with a clear message if ffmpeg is absent.
                None → opens an interactive window via plt.show().
            zone_bounds: Optional (x_min, x_max, y_min, y_max) of a protected zone
                to shade behind the trajectories (m). None draws no zone.

        Raises:
            ValueError: If the recorder contains no entities.
            RuntimeError: If filepath ends in ".mp4" and ffmpeg is unavailable.

        Note:
            Frame count equals the length of the longest recorded trajectory.
            Entities with fewer snapshots are held at their last position once
            their trajectory is exhausted.
            O(N·F) where N = number of entities, F = total frames.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.animation as mpl_anim

        ids = self._recorder.get_all_ids()
        if not ids:
            raise ValueError("TrajectoryRecorder contains no recorded entities.")

        trajectories: dict[str, list[Snapshot]] = {
            eid: self._recorder.get_trajectory(eid) for eid in ids
        }
        max_frames = max(len(t) for t in trajectories.values())

        # Pre-compute global axis bounds so the view is stable during playback
        all_x = [snap.position.x for traj in trajectories.values() for snap in traj]
        all_y = [snap.position.y for traj in trajectories.values() for snap in traj]
        x_range = max(all_x) - min(all_x) or 1.0
        y_range = max(all_y) - min(all_y) or 1.0
        x_pad = x_range * 0.05
        y_pad = y_range * 0.05
        x_lim = (min(all_x) - x_pad, max(all_x) + x_pad)
        y_lim = (min(all_y) - y_pad, max(all_y) + y_pad)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_xlim(*x_lim)
        ax.set_ylim(*y_lim)
        ax.set_aspect("equal")
        ax.set_xlabel("Horizontal position (m)")
        ax.set_ylabel("Altitude (m)")
        ax.grid(True, linewidth=0.4, alpha=0.6)
        ax.axhline(0, color="gray", linewidth=0.5)

        if zone_bounds is not None:
            _draw_zone(ax, zone_bounds)

        # Initialise one trail line and one position marker per entity
        trails: dict[str, object] = {}
        markers: dict[str, object] = {}
        for idx, entity_id in enumerate(ids):
            colour = _COLOURS[idx % len(_COLOURS)]
            (trail,) = ax.plot([], [], color=colour, linewidth=1.5, label=entity_id)
            (marker,) = ax.plot(
                [], [], marker="o", color=colour, markersize=8,
                linestyle="None", zorder=5,
            )
            trails[entity_id] = trail
            markers[entity_id] = marker

        ax.legend(loc="upper right")
        time_label = ax.set_title("t = 0.00 s")

        # Reference trajectory for the time axis (longest one)
        ref_traj = max(trajectories.values(), key=len)

        def _update(frame: int) -> None:
            t = ref_traj[min(frame, len(ref_traj) - 1)].time
            ax.set_title(f"t = {t:.2f} s")

            for entity_id in ids:
                traj = trajectories[entity_id]
                i = min(frame, len(traj) - 1)

                xs = [snap.position.x for snap in traj[: i + 1]]
                ys = [snap.position.y for snap in traj[: i + 1]]
                trails[entity_id].set_data(xs, ys)  # type: ignore[union-attr]
                markers[entity_id].set_data(        # type: ignore[union-attr]
                    [traj[i].position.x], [traj[i].position.y]
                )

        ani = mpl_anim.FuncAnimation(
            fig, _update, frames=max_frames, interval=interval_ms, blit=False
        )

        if filepath is None:
            plt.show()
        else:
            ext = "." + filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
            if ext == ".gif":
                ani.save(filepath, writer="pillow")
            elif ext == ".mp4":
                try:
                    ani.save(filepath, writer="ffmpeg")
                except Exception as exc:
                    raise RuntimeError(
                        f"Could not save .mp4 — is ffmpeg installed and on PATH?\n"
                        f"Original error: {exc}"
                    ) from exc
            else:
                ani.save(filepath)

        plt.close(fig)
