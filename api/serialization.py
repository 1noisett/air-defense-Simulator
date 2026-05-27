from __future__ import annotations

from battery.report import Disposition, EngagementReport
from simulation.recorder import TrajectoryRecorder

from api.schemas import EntityTrajectory, ReportSummary, Snapshot


def serialize_trajectories(
    recorder: TrajectoryRecorder,
    report: EngagementReport,
) -> list[EntityTrajectory]:
    """Convert recorder history and engagement report to a JSON-ready trajectory list.

    Args:
        recorder: Completed TrajectoryRecorder from the simulation run.
        report: EngagementReport from BatteryController.report().

    Returns:
        One EntityTrajectory per entity. Snapshots are already chronologically
        ordered by the recorder — no sort is applied.
    """
    trajectories: list[EntityTrajectory] = []

    for eid in recorder.get_all_ids():
        raw = recorder.get_trajectory(eid)
        snapshots = [Snapshot(t=s.time, x=s.position.x, y=s.position.y) for s in raw]

        if eid.startswith("threat_"):
            entity_type = "threat"
            threat_report = report.threats.get(eid)
            disposition: str | None = threat_report.disposition.value if threat_report else None
        else:
            entity_type = "interceptor"
            disposition = None

        trajectories.append(
            EntityTrajectory(
                entity_id=eid,
                entity_type=entity_type,
                snapshots=snapshots,
                disposition=disposition,
            )
        )

    return trajectories


def build_report_summary(report: EngagementReport) -> ReportSummary:
    """Aggregate per-threat dispositions into counts.

    Args:
        report: EngagementReport from BatteryController.report().

    Returns:
        ReportSummary with neutralized, leaked, safe, and in_flight counts.
    """
    neutralized = 0
    leaked = 0
    safe = 0
    in_flight = 0

    for tr in report.threats.values():
        match tr.disposition:
            case Disposition.NEUTRALIZED:
                neutralized += 1
            case Disposition.IMPACTED_PROTECTED_ZONE:
                leaked += 1
            case Disposition.IMPACTED_GROUND_SAFE:
                safe += 1
            case Disposition.IN_FLIGHT:
                in_flight += 1

    return ReportSummary(
        neutralized=neutralized,
        leaked=leaked,
        safe=safe,
        in_flight=in_flight,
    )
