"""Stable JSON and human-readable report renderers."""

from __future__ import annotations

import json
from collections.abc import Mapping


def render_json(report: Mapping[str, object]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_text(report: Mapping[str, object]) -> str:
    operation = report["operation"]
    if operation == "ingest":
        counts = report["counts"]
        assert isinstance(counts, dict)
        lines = [
            "TransitPulse ingestion",
            f"Status: {report['status']}",
            f"Source: {report['source']}",
            f"Ingestion ID: {report['ingestion_id']}",
            f"Feed timestamp: {report['feed_timestamp']}",
            f"Trip-stop events: {counts['trip_stop_events']}",
            f"Alerts: {counts['alerts']}",
        ]
        return "\n".join(lines) + "\n"

    counts = report["counts"]
    routes = report["routes"]
    alert_effects = report["alert_effects"]
    assert isinstance(counts, dict)
    assert isinstance(routes, list)
    assert isinstance(alert_effects, list)

    lines = [
        "TransitPulse summary",
        f"Ingestions: {counts['ingestions']}",
        f"Trip-stop events: {counts['trip_stop_events']}",
        f"Alerts: {counts['alerts']}",
        f"Delayed threshold: {report['delay_threshold_seconds']} seconds",
        "Routes:",
    ]
    if routes:
        for route in routes:
            lines.append(
                "  "
                f"{route['route_id']}: events={route['event_count']}, "
                f"average_delay={route['average_delay_seconds']}, "
                f"delayed={route['delayed_event_count']}"
            )
    else:
        lines.append("  none")

    lines.append("Alert effects:")
    if alert_effects:
        for effect in alert_effects:
            lines.append(f"  {effect['effect']}: {effect['alert_count']}")
    else:
        lines.append("  none")
    return "\n".join(lines) + "\n"


def render(report: Mapping[str, object], output_format: str) -> str:
    if output_format == "json":
        return render_json(report)
    if output_format == "text":
        return render_text(report)
    raise ValueError(f"unsupported output format: {output_format}")
