from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "sample_output"
PROCESS_INCIDENT = REPO_ROOT / "data" / "synthetic" / "packaging_line_process_incident.csv"
CONFIG_PATH = REPO_ROOT / "config" / "lab.example.json"
MODEL_METRICS_PATH = OUTPUT_DIR / "model_metrics.json"

TRIGGER_ORDER = [
    "new_source",
    "scan_like",
    "ml_anomaly",
    "suricata_alert",
    "programming_activity",
    "plc_artifact_change",
]

TRIGGER_LABELS = {
    "new_source": "Unseen source endpoint",
    "scan_like": "Scan behavior pattern",
    "ml_anomaly": "Anomaly model threshold breach",
    "suricata_alert": "IDS detection alert",
    "programming_activity": "PLC programming activity",
    "plc_artifact_change": "Controller artifact change",
    "network_anomaly": "Anomaly model threshold breach",
}

TRIGGER_SHORT_LABELS = {
    "new_source": "New source",
    "scan_like": "Scan pattern",
    "ml_anomaly": "Model anomaly",
    "suricata_alert": "IDS alert",
    "programming_activity": "PLC programming",
    "plc_artifact_change": "Artifact change",
    "network_anomaly": "Model anomaly",
}

MITRE_CUES = {
    "new_source": "Discovery cue",
    "scan_like": "Discovery: network enumeration cue",
    "suricata_alert": "Detection alert cue",
    "programming_activity": "Lateral movement cue: program download",
    "plc_artifact_change": "Execution cue: controller logic change",
    "network_anomaly": "Behavioral anomaly cue",
}

SEVERITY_COLORS = {
    "CRITICAL": "#b91c1c",
    "HIGH": "#ea580c",
    "MEDIUM": "#ca8a04",
    "LOW": "#16a34a",
}

SIGNAL_COLORS = {
    "Speed (%)": "#38bdf8",
    "Motor current (A)": "#f59e0b",
    "Vibration (mm/s)": "#ef4444",
}

PLOTLY_CHART_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "responsive": True,
}


@st.cache_data
def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def require_outputs() -> None:
    required = [
        OUTPUT_DIR / "incident_summary.json",
        OUTPUT_DIR / "events.csv",
        OUTPUT_DIR / "scored_incident_windows.csv",
        OUTPUT_DIR / "plc_forensics_event.json",
        PROCESS_INCIDENT,
    ]
    missing = [path.name for path in required if not path.exists()]
    if missing:
        st.error("Missing generated files: " + ", ".join(missing))
        st.code("python scripts/run_demo.py", language="powershell")
        st.stop()


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --app-bg: #0f1724;
            --panel-bg: #131d2b;
            --panel-border: #233348;
            --panel-border-strong: #3a5d82;
            --text-primary: #e2e8f0;
            --text-secondary: #9ab0c8;
            --accent: #5aa0e6;
            --critical: #f87171;
            --high: #fb923c;
            --medium: #fbbf24;
            --low: #4ade80;
            --shadow-soft: 0 1px 2px rgba(2, 6, 23, 0.35);
        }
        .stApp {
            background: var(--app-bg);
        }
        section[data-testid="stSidebar"] {
            width: 260px !important;
        }
        section[data-testid="stSidebar"] > div {
            width: 260px !important;
        }
        .block-container {
            padding-top: 3rem;
            padding-bottom: 2rem;
            max-width: 1360px;
        }
        .page-title {
            color: var(--text-primary);
            font-size: 1.9rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            margin-bottom: 0.2rem;
        }
        .page-subtitle {
            color: var(--text-secondary);
            font-size: 0.95rem;
            margin-bottom: 0.9rem;
        }
        .section-title {
            color: var(--text-primary);
            font-size: 1rem;
            font-weight: 700;
            margin-top: 0.6rem;
            margin-bottom: 0.45rem;
        }
        .section-anchor {
            scroll-margin-top: 4rem;
        }
        .sidebar-card {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            border-radius: 10px;
            padding: 0.75rem;
            margin-bottom: 0.6rem;
            box-shadow: var(--shadow-soft);
        }
        .sidebar-title {
            color: var(--text-primary);
            font-size: 0.85rem;
            font-weight: 700;
            margin-bottom: 0.4rem;
            letter-spacing: 0.01em;
        }
        .sidebar-meta {
            color: var(--text-secondary);
            font-size: 0.8rem;
            line-height: 1.35;
            margin-bottom: 0.2rem;
        }
        .nav-note {
            color: var(--text-secondary);
            font-size: 0.76rem;
            margin-top: 0.2rem;
            margin-bottom: 0.25rem;
        }
        .nav-link {
            display: block;
            color: var(--text-secondary);
            text-decoration: none;
            border-left: 3px solid transparent;
            padding: 0.18rem 0.2rem 0.18rem 0.45rem;
            margin-bottom: 0.18rem;
            font-size: 0.8rem;
            border-radius: 4px;
        }
        .nav-link:hover {
            color: var(--accent);
            border-left-color: var(--accent);
            background: rgba(90, 160, 230, 0.08);
        }
        [data-testid="stMetric"] {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            border-radius: 10px;
            padding: 0.75rem 0.85rem;
            box-shadow: var(--shadow-soft);
        }
        [data-testid="stMetricLabel"] {
            color: var(--text-secondary) !important;
            font-weight: 600;
            letter-spacing: 0.01em;
        }
        [data-testid="stMetricLabel"] > div {
            font-size: 0.86rem !important;
        }
        [data-testid="stMetricValue"] {
            color: var(--text-primary) !important;
        }
        [data-testid="stMetricValue"] > div {
            font-size: 1.56rem !important;
            line-height: 1.1 !important;
        }
        [data-testid="stMetricDelta"] {
            color: #fca5a5 !important;
        }
        [data-testid="stTabs"] button[data-baseweb="tab"] {
            font-weight: 700;
            letter-spacing: 0.1px;
        }
        [data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--accent);
            border-bottom: 3px solid var(--accent);
        }
        .status-card {
            border-radius: 10px;
            border: 1px solid var(--panel-border);
            background: var(--panel-bg);
            padding: 0.72rem 0.8rem;
            box-shadow: var(--shadow-soft);
            height: 100%;
        }
        .status-label {
            color: var(--text-secondary);
            font-size: 0.82rem;
            font-weight: 600;
            margin-bottom: 0.22rem;
        }
        .status-value {
            color: var(--text-primary);
            font-size: 1.26rem;
            font-weight: 700;
            line-height: 1.15;
            margin-bottom: 0.12rem;
            white-space: nowrap;
        }
        .status-value-critical {
            color: var(--critical);
        }
        .status-value-high {
            color: var(--high);
        }
        .status-value-medium {
            color: var(--medium);
        }
        .status-value-low {
            color: var(--low);
        }
        .status-foot {
            color: var(--text-secondary);
            font-size: 0.76rem;
        }
        .verdict-card {
            margin-top: 0.3rem;
            margin-bottom: 0.8rem;
            border-radius: 10px;
            padding: 0.8rem 1rem;
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            box-shadow: var(--shadow-soft);
        }
        .verdict-title {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--text-secondary);
            margin-bottom: 0.25rem;
            font-weight: 700;
        }
        .verdict-body {
            font-size: 1rem;
            color: var(--text-primary);
            font-weight: 650;
            margin-bottom: 0.35rem;
        }
        .verdict-foot {
            font-size: 0.84rem;
            color: var(--text-secondary);
        }
        .trigger-card {
            border-radius: 10px;
            border: 1px solid var(--panel-border);
            background: var(--panel-bg);
            padding: 0.65rem 0.6rem;
            min-height: 96px;
            box-shadow: var(--shadow-soft);
        }
        .trigger-active {
            border-color: var(--panel-border-strong);
            box-shadow: 0 0 0 1px rgba(47, 111, 179, 0.18);
        }
        .trigger-off {
            border-color: var(--panel-border);
        }
        .trigger-name {
            font-size: 0.84rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.3rem;
            line-height: 1.25;
        }
        .trigger-state {
            font-size: 0.82rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        .trigger-state-on {
            color: #7dd3fc;
        }
        .trigger-state-off {
            color: #94a3b8;
        }
        .trigger-points {
            font-size: 0.78rem;
            color: #93a4b8;
        }
        .minor-note {
            color: #93a4b8;
            font-size: 0.86rem;
        }
        .incident-window-badge {
            display: inline-block;
            margin-top: 0.08rem;
            margin-bottom: 0.55rem;
            padding: 0.32rem 0.62rem;
            border-radius: 999px;
            border: 1px solid var(--panel-border-strong);
            background: rgba(23, 38, 56, 0.72);
            color: #dbeafe;
            font-size: 0.8rem;
            font-weight: 650;
            letter-spacing: 0.01em;
        }
        .timeline-card {
            border-radius: 10px;
            border: 1px solid var(--panel-border);
            background: var(--panel-bg);
            padding: 0.68rem 0.8rem;
            box-shadow: var(--shadow-soft);
            height: 100%;
        }
        .timeline-title {
            color: var(--text-secondary);
            font-size: 0.82rem;
            font-weight: 700;
            margin-bottom: 0.28rem;
        }
        .timeline-row {
            display: block;
            padding-top: 0.14rem;
            padding-bottom: 0.14rem;
            border-bottom: 1px dashed rgba(148, 163, 184, 0.2);
        }
        .timeline-row:last-child {
            border-bottom: none;
            padding-bottom: 0;
        }
        .timeline-key {
            color: var(--text-secondary);
            font-size: 0.76rem;
            line-height: 1.3;
            display: block;
        }
        .timeline-value {
            color: var(--text-primary);
            font-size: 0.8rem;
            font-weight: 650;
            white-space: nowrap;
            display: block;
            margin-top: 0.02rem;
        }
        .flow-panel {
            display: flex;
            align-items: stretch;
            gap: 0.5rem;
            overflow-x: auto;
            padding-bottom: 0.25rem;
            margin-bottom: 0.3rem;
        }
        .flow-node {
            flex: 1 0 220px;
            min-width: 220px;
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            border-radius: 10px;
            padding: 0.7rem;
            box-shadow: var(--shadow-soft);
        }
        .flow-node-title {
            color: var(--text-primary);
            font-size: 0.84rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
            line-height: 1.25;
        }
        .flow-node-script {
            color: #7dd3fc;
            font-family: Consolas, "Courier New", monospace;
            font-size: 0.76rem;
            margin-bottom: 0.3rem;
            word-break: break-word;
        }
        .flow-node-artifact {
            color: var(--text-secondary);
            font-size: 0.76rem;
            line-height: 1.3;
        }
        .flow-arrow {
            align-self: center;
            color: #64748b;
            font-size: 1.05rem;
            font-weight: 700;
            padding: 0 0.1rem;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid var(--panel-border);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: var(--shadow-soft);
        }
        [data-testid="stExpander"] details {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            border-radius: 10px;
        }
        [data-testid="stExpander"] summary p {
            color: var(--text-primary);
            font-weight: 650;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def trigger_label(name: str) -> str:
    return TRIGGER_LABELS.get(name, name.replace("_", " ").title())


def trigger_short_label(name: str) -> str:
    return TRIGGER_SHORT_LABELS.get(name, trigger_label(name))


def render_section_title(section_id: str, title: str) -> None:
    st.markdown(
        f"<h3 id='{section_id}' class='section-title section-anchor'>{title}</h3>",
        unsafe_allow_html=True,
    )


def render_verdict_card(verdict: str, reasons: list[str], severity: str) -> None:
    severity_color = SEVERITY_COLORS.get(severity, "#334155")
    reason_line = " | ".join(trigger_label(reason) for reason in reasons) if reasons else "No evidence reason listed"
    st.markdown(
        f"""
        <div class="verdict-card" style="border-left: 5px solid {severity_color};">
            <div class="verdict-title">Correlated verdict</div>
            <div class="verdict-body">{verdict}</div>
            <div class="verdict-foot">Active evidence families: {reason_line}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_card(severity: str, risk_score: float, threshold: float) -> None:
    severity_name = str(severity).upper()
    severity_class = severity_name.lower()
    threshold_state = "Above model threshold" if risk_score >= threshold else "Below model threshold"
    st.markdown(
        f"""
        <div class="status-card">
            <div class="status-label">Incident severity</div>
            <div class="status-value status-value-{severity_class}">{severity_name}</div>
            <div class="status-foot">{threshold_state} ({threshold:.0f})</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def to_utc_timestamp(value: object) -> pd.Timestamp | None:
    stamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(stamp):
        return None
    return pd.Timestamp(stamp)


def format_utc_time(value: pd.Timestamp | None, include_seconds: bool = True) -> str:
    if value is None:
        return "N/A"
    pattern = "%H:%M:%S UTC" if include_seconds else "%H:%M UTC"
    return value.tz_convert("UTC").strftime(pattern)


def format_utc_clock(value: pd.Timestamp | None) -> str:
    if value is None:
        return "N/A"
    return value.tz_convert("UTC").strftime("%H:%M")


def first_timestamp(
    frame: pd.DataFrame,
    time_column: str,
    mask: pd.Series | None = None,
) -> pd.Timestamp | None:
    if frame.empty or time_column not in frame.columns:
        return None
    scoped = frame.loc[mask, time_column] if mask is not None else frame[time_column]
    stamps = pd.to_datetime(scoped, utc=True, errors="coerce").dropna()
    if stamps.empty:
        return None
    return pd.Timestamp(stamps.min())


def build_incident_timeline(
    display_events: pd.DataFrame,
    process: pd.DataFrame,
    windows: pd.DataFrame,
) -> dict[str, pd.Timestamp | None]:
    first_suspicious = first_timestamp(display_events, "timestamp")
    if first_suspicious is None:
        first_suspicious = first_timestamp(windows, "window_start")

    controller_tampered = None
    if "event_type" in display_events.columns:
        controller_tampered = first_timestamp(
            display_events,
            "timestamp",
            display_events["event_type"].eq("plc_artifact_change"),
        )
        if controller_tampered is None:
            controller_tampered = first_timestamp(
                display_events,
                "timestamp",
                display_events["event_type"].eq("programming_activity"),
            )

    process_disrupted = None
    if "ground_truth_label" in process.columns:
        process_disrupted = first_timestamp(
            process,
            "timestamp",
            process["ground_truth_label"].eq("PROCESS_IMPACT"),
        )
    # Use the midpoint of the first impact minute as the disruption callout.
    if process_disrupted is not None:
        process_disrupted = process_disrupted.floor("min") + pd.Timedelta(seconds=30)

    window_start = first_suspicious
    window_end = (window_start + pd.Timedelta(minutes=20)) if window_start is not None else None
    return {
        "first_suspicious": first_suspicious,
        "controller_tampered": controller_tampered,
        "process_disrupted": process_disrupted,
        "window_start": window_start,
        "window_end": window_end,
    }


def render_incident_timeline_card(
    first_suspicious: pd.Timestamp | None,
    controller_tampered: pd.Timestamp | None,
    process_disrupted: pd.Timestamp | None,
) -> None:
    st.markdown(
        f"""
        <div class="timeline-card">
            <div class="timeline-title">Incident milestones</div>
            <div class="timeline-row">
                <span class="timeline-key">First suspicious activity</span>
                <span class="timeline-value">{format_utc_time(first_suspicious)}</span>
            </div>
            <div class="timeline-row">
                <span class="timeline-key">Controller tampered</span>
                <span class="timeline-value">{format_utc_time(controller_tampered)}</span>
            </div>
            <div class="timeline-row">
                <span class="timeline-key">Process disrupted</span>
                <span class="timeline-value">{format_utc_time(process_disrupted)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def incident_window_badge(window_start: pd.Timestamp | None, window_end: pd.Timestamp | None) -> str:
    if window_start is None or window_end is None:
        return ""
    duration_minutes = int(max((window_end - window_start).total_seconds() // 60, 0))
    return (
        f"Incident Window: {format_utc_clock(window_start)} - "
        f"{format_utc_clock(window_end)} UTC ({duration_minutes} mins)"
    )


def render_sidebar(summary: dict, anomaly_threshold: float, active_evidence: int) -> None:
    st.sidebar.markdown(
        """
        <div class="sidebar-card">
            <div class="sidebar-title">Dashboard navigation</div>
            <a class="nav-link" href="#operations-overview">Operations overview</a>
            <a class="nav-link" href="#behavior-analytics">Behavior analytics</a>
            <a class="nav-link" href="#evidence-trigger-matrix">Trigger matrix</a>
            <a class="nav-link" href="#synthetic-pipeline-data-flow">Pipeline data flow</a>
            <a class="nav-link" href="#evidence-and-audit-tables">Audit evidence</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<div class='nav-note'>Click a navigation link to scroll directly to that section.</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"""
        <div class="sidebar-card">
            <div class="sidebar-title">Current run profile</div>
            <div class="sidebar-meta">Environment: Synthetic packaging line</div>
            <div class="sidebar-meta">Severity: {str(summary.get("severity", "UNKNOWN")).title()}</div>
            <div class="sidebar-meta">Risk score: {summary.get("risk_score", 0)} / 100</div>
            <div class="sidebar-meta">Active triggers: {active_evidence} / {len(TRIGGER_ORDER)}</div>
            <div class="sidebar-meta">Anomaly threshold: {anomaly_threshold:.0f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_trigger_cards(evidence_flags: dict, risk_points: dict) -> None:
    trigger_cols = st.columns(len(TRIGGER_ORDER))
    for index, trigger_name in enumerate(TRIGGER_ORDER):
        is_active = bool(evidence_flags.get(trigger_name, False))
        state_text = "DETECTED" if is_active else "NOT DETECTED"
        state_class = "trigger-state-on" if is_active else "trigger-state-off"
        card_class = "trigger-active" if is_active else "trigger-off"
        trigger_cols[index].markdown(
            f"""
            <div class="trigger-card {card_class}">
                <div class="trigger-name">{trigger_short_label(trigger_name)}</div>
                <div class="trigger-state {state_class}">{state_text}</div>
                <div class="trigger-points">{risk_points.get(trigger_name, 0)} pts</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_data_flow_panel() -> None:
    stages = [
        (
            "1. Generate synthetic OT data",
            "scripts/generate_sample_data.py",
            "Out: process, network, artifacts",
        ),
        (
            "2. Build feature windows",
            "scripts/build_features.py",
            "Out: 60-second feature windows",
        ),
        (
            "3. Score anomaly windows",
            "model/train_isolation_forest.py",
            "Out: anomaly scores and metrics",
        ),
        (
            "4. Detect PLC artifact deltas",
            "scripts/icspector_manifest.py",
            "Out: artifact delta event",
        ),
        (
            "5. Correlate evidence and classify incident",
            "scripts/correlate_events.py",
            "Out: events.csv and incident_summary.json",
        ),
    ]

    panel_html = ['<div class="flow-panel">']
    for index, (title, script_name, artifact) in enumerate(stages):
        panel_html.append(
            f"""
            <div class="flow-node">
                <div class="flow-node-title">{title}</div>
                <div class="flow-node-script">{script_name}</div>
                <div class="flow-node-artifact">{artifact}</div>
            </div>
            """
        )
        if index < len(stages) - 1:
            panel_html.append('<div class="flow-arrow">&rarr;</div>')
    panel_html.append("</div>")

    st.markdown("".join(panel_html), unsafe_allow_html=True)
    st.caption("Orchestration: scripts/run_demo.py")


def risk_color(score: float) -> str:
    if score >= 80:
        return "#b91c1c"
    if score >= 60:
        return "#ea580c"
    if score >= 30:
        return "#ca8a04"
    return "#16a34a"


def build_risk_gauge(score: float, threshold: float) -> go.Figure:
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": " / 100", "font": {"color": "#e2e8f0"}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": risk_color(score)},
                "steps": [
                    {"range": [0, 30], "color": "#1f3a2d"},
                    {"range": [30, 60], "color": "#3f3a1f"},
                    {"range": [60, 80], "color": "#4d321f"},
                    {"range": [80, 100], "color": "#4a1f1f"},
                ],
                "threshold": {
                    "line": {"color": "#e2e8f0", "width": 3},
                    "thickness": 0.8,
                    "value": threshold,
                },
            },
        )
    )
    figure.update_layout(
        margin=dict(l=10, r=10, t=20, b=10),
        height=220,
        plot_bgcolor="#101722",
        paper_bgcolor="#101722",
        font={"color": "#e2e8f0"},
    )
    return figure


def build_network_chart(
    windows: pd.DataFrame,
    threshold: float,
    compromise_time: pd.Timestamp | None,
) -> go.Figure:
    figure = px.line(
        windows.sort_values("window_start"),
        x="window_start",
        y="anomaly_score",
        color="src_ip",
        color_discrete_sequence=["#38bdf8", "#22d3ee", "#60a5fa", "#818cf8", "#2dd4bf", "#06b6d4"],
        markers=True,
        labels={
            "window_start": "Window (UTC)",
            "anomaly_score": "Anomaly score",
            "src_ip": "Source endpoint",
        },
        title="Network anomaly by source",
    )
    figure.add_hline(y=threshold, line_dash="dash", line_color="#f59e0b")
    if compromise_time is not None:
        marker_label = f"Compromise Occurred ({format_utc_time(compromise_time, include_seconds=False)})"
        figure.add_vline(x=compromise_time, line_dash="dash", line_color="#ef4444", line_width=2)
        figure.add_annotation(
            x=compromise_time,
            y=0.98,
            xref="x",
            yref="paper",
            text=marker_label,
            showarrow=False,
            xanchor="left",
            align="left",
            font={"size": 11, "color": "#fca5a5"},
            bgcolor="rgba(15, 23, 36, 0.86)",
            bordercolor="#ef4444",
            borderwidth=1,
        )
    figure.update_traces(line={"width": 2.4}, marker={"size": 6})
    figure.update_layout(
        title={"x": 0.0, "xanchor": "left"},
        margin=dict(l=10, r=10, t=62, b=112),
        legend_title_text="",
        legend={"orientation": "h", "yanchor": "top", "y": -0.27, "x": 0.0, "font": {"size": 11}},
        template="plotly_dark",
        plot_bgcolor="#101722",
        paper_bgcolor="#101722",
        font={"color": "#e2e8f0"},
        height=355,
    )
    figure.update_xaxes(title_text="", showgrid=True, gridcolor="#273347")
    figure.update_yaxes(showgrid=True, gridcolor="#273347")
    return figure


def build_asset_flow(windows: pd.DataFrame, plc_ip: str, known_sources: set[str]) -> go.Figure:
    sources = (
        windows.groupby("src_ip", as_index=False)["conn_count"]
        .sum()
        .sort_values("conn_count", ascending=False)
        .head(6)
    )
    if sources.empty:
        figure = go.Figure()
        figure.add_annotation(text="No source flow data available.", showarrow=False)
        figure.update_layout(height=350, margin=dict(l=10, r=10, t=30, b=10), template="plotly_dark")
        return figure

    labels = sources["src_ip"].tolist() + [plc_ip]
    target_index = len(labels) - 1
    flow_colors = [
        "rgba(56, 189, 248, 0.52)" if source in known_sources else "rgba(239, 68, 68, 0.66)"
        for source in sources["src_ip"].tolist()
    ]
    figure = go.Figure(
        go.Sankey(
            node={
                "label": labels,
                "pad": 15,
                "thickness": 18,
                "color": ["#1e293b"] * len(sources) + ["#334155"],
            },
            link={
                "source": list(range(len(sources))),
                "target": [target_index] * len(sources),
                "value": sources["conn_count"].tolist(),
                "color": flow_colors,
            },
        )
    )
    figure.update_layout(
        title="Observed source-to-PLC communication volume",
        margin=dict(l=10, r=10, t=40, b=10),
        height=350,
        template="plotly_dark",
        plot_bgcolor="#101722",
        paper_bgcolor="#101722",
        font={"color": "#e2e8f0"},
    )
    return figure


def build_process_chart(process: pd.DataFrame, compromise_time: pd.Timestamp | None) -> go.Figure:
    focus = process.copy()
    if "ground_truth_label" in focus.columns:
        scoped = focus.loc[
            focus["ground_truth_label"].isin(["POST_CHANGE", "PROCESS_IMPACT", "RECOVERY"])
        ]
        if not scoped.empty:
            focus = scoped

    long_frame = focus.melt(
        id_vars="timestamp",
        value_vars=["actual_speed_pct", "motor_current_a", "vibration_mm_s"],
        var_name="signal",
        value_name="value",
    )
    signal_labels = {
        "actual_speed_pct": "Speed (%)",
        "motor_current_a": "Motor current (A)",
        "vibration_mm_s": "Vibration (mm/s)",
    }
    long_frame["signal"] = long_frame["signal"].map(signal_labels)
    long_frame["signal"] = pd.Categorical(
        long_frame["signal"],
        categories=["Speed (%)", "Motor current (A)", "Vibration (mm/s)"],
        ordered=True,
    )

    figure = px.line(
        long_frame.sort_values("timestamp"),
        x="timestamp",
        y="value",
        facet_row="signal",
        color="signal",
        color_discrete_map=SIGNAL_COLORS,
        height=480,
        labels={"timestamp": "Incident time (UTC)", "value": "Value", "signal": "Signal"},
        title="Process telemetry (impact window)",
    )
    figure.for_each_annotation(lambda annotation: annotation.update(text=annotation.text.split("=")[-1]))
    if compromise_time is not None:
        marker_label = f"Compromise Occurred ({format_utc_time(compromise_time, include_seconds=False)})"
        figure.add_vline(
            x=compromise_time,
            line_dash="dash",
            line_color="#ef4444",
            line_width=2,
            row="all",
            col=1,
        )
        figure.add_annotation(
            x=compromise_time,
            y=0.985,
            xref="x",
            yref="paper",
            text=marker_label,
            showarrow=False,
            xanchor="left",
            align="left",
            font={"size": 11, "color": "#fca5a5"},
            bgcolor="rgba(15, 23, 36, 0.86)",
            bordercolor="#ef4444",
            borderwidth=1,
        )
    figure.update_yaxes(matches=None, showticklabels=True)
    figure.update_traces(line={"width": 2.2})
    figure.update_layout(
        title={"x": 0.0, "xanchor": "left"},
        showlegend=False,
        margin=dict(l=10, r=10, t=62, b=10),
        template="plotly_dark",
        plot_bgcolor="#101722",
        paper_bgcolor="#101722",
        font={"color": "#e2e8f0"},
        height=470,
    )
    figure.update_xaxes(showgrid=True, gridcolor="#273347")
    figure.update_yaxes(showgrid=True, gridcolor="#273347")
    return figure


def prepare_events(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events
    display = events.copy()
    display["timestamp"] = pd.to_datetime(display["timestamp"], utc=True, errors="coerce")
    display = display.dropna(subset=["timestamp"]).sort_values("timestamp")
    display["event_label"] = display["event_type"].map(trigger_label).fillna(display["event_type"])
    display["event_label_short"] = (
        display["event_type"].map(trigger_short_label).fillna(display["event_type"])
    )
    display["mitre_cue"] = display["event_type"].map(MITRE_CUES).fillna("Behavioral cue")
    return display


def build_timeline_chart(display: pd.DataFrame) -> go.Figure | None:
    if display.empty:
        return None
    figure = px.scatter(
        display,
        x="timestamp",
        y="event_label_short",
        color="severity",
        category_orders={
            "event_label_short": [trigger_short_label(name) for name in reversed(TRIGGER_ORDER)]
        },
        color_discrete_map=SEVERITY_COLORS,
        hover_data={
            "source": True,
            "score": ":.1f",
            "mitre_cue": True,
            "summary": True,
            "event_label": False,
            "event_label_short": False,
        },
        title="Correlated event timeline",
    )
    figure.update_traces(marker={"size": 10, "line": {"width": 0.8, "color": "#0b1220"}})
    figure.update_layout(
        title={"x": 0.0, "xanchor": "left"},
        margin=dict(l=10, r=10, t=70, b=90),
        xaxis_title="UTC",
        yaxis_title="",
        template="plotly_dark",
        plot_bgcolor="#101722",
        paper_bgcolor="#101722",
        font={"color": "#e2e8f0"},
        legend_title_text="",
        legend={"orientation": "h", "yanchor": "top", "y": -0.22, "x": 0.0},
        height=355,
    )
    figure.update_yaxes(automargin=True, tickfont={"size": 11})
    figure.update_xaxes(showgrid=True, gridcolor="#273347")
    figure.update_yaxes(showgrid=True, gridcolor="#273347")
    return figure


def build_source_volume_chart(top_sources: pd.DataFrame) -> go.Figure:
    if top_sources.empty:
        figure = go.Figure()
        figure.add_annotation(text="No source activity available.", showarrow=False)
        figure.update_layout(template="plotly_dark", height=355)
        return figure

    display = top_sources.head(8).sort_values("Connections")
    figure = px.bar(
        display,
        x="Connections",
        y="Source IP",
        orientation="h",
        text="Connections",
        labels={"Source IP": "Source endpoint", "Connections": "Connections"},
        title="Source volume",
    )
    figure.update_traces(marker_color="#5aa0e6", textposition="outside", cliponaxis=False)
    figure.update_layout(
        title={"x": 0.0, "xanchor": "left"},
        template="plotly_dark",
        plot_bgcolor="#101722",
        paper_bgcolor="#101722",
        font={"color": "#e2e8f0"},
        margin=dict(l=10, r=30, t=62, b=10),
        height=355,
    )
    figure.update_xaxes(showgrid=True, gridcolor="#273347")
    figure.update_yaxes(showgrid=False)
    return figure


def build_evidence_weight_chart(evidence_flags: dict, risk_points: dict) -> go.Figure:
    rows = [
        {
            "Trigger": trigger_short_label(name),
            "Weight": float(risk_points.get(name, 0)),
            "Status": "Detected" if evidence_flags.get(name, False) else "Not detected",
        }
        for name in TRIGGER_ORDER
    ]
    frame = pd.DataFrame(rows).sort_values("Weight")
    figure = px.bar(
        frame,
        x="Weight",
        y="Trigger",
        orientation="h",
        color="Status",
        color_discrete_map={"Detected": "#f59e0b", "Not detected": "#334155"},
        text="Weight",
        title="Trigger weights",
        labels={"Weight": "Points", "Trigger": ""},
    )
    figure.update_traces(texttemplate="%{x:.0f} pts", textposition="outside", cliponaxis=False)
    max_weight = max(float(frame["Weight"].max()), 1.0)
    figure.update_layout(
        title={"x": 0.0, "xanchor": "left"},
        template="plotly_dark",
        plot_bgcolor="#101722",
        paper_bgcolor="#101722",
        font={"color": "#e2e8f0"},
        margin=dict(l=10, r=22, t=62, b=10),
        height=355,
        showlegend=False,
    )
    figure.update_xaxes(showgrid=True, gridcolor="#273347", range=[0, max_weight * 1.28])
    figure.update_yaxes(showgrid=False, automargin=True)
    return figure


def build_event_severity_chart(display: pd.DataFrame) -> go.Figure:
    if display.empty:
        figure = go.Figure()
        figure.add_annotation(text="No events available.", showarrow=False)
        figure.update_layout(template="plotly_dark", height=300)
        return figure

    counts = (
        display["severity"].value_counts().rename_axis("Severity").reset_index(name="Events")
    )
    figure = px.pie(
        counts,
        names="Severity",
        values="Events",
        hole=0.6,
        color="Severity",
        color_discrete_map=SEVERITY_COLORS,
        title="Event severity mix",
    )
    figure.update_traces(textinfo="value")
    figure.update_layout(
        title={"x": 0.0, "xanchor": "left"},
        template="plotly_dark",
        plot_bgcolor="#101722",
        paper_bgcolor="#101722",
        font={"color": "#e2e8f0"},
        margin=dict(l=10, r=10, t=62, b=85),
        height=300,
        legend_title_text="",
        legend={"orientation": "h", "yanchor": "top", "y": -0.2, "x": 0.0},
    )
    return figure


def build_process_delta_chart(impact_kpis: dict[str, float]) -> go.Figure:
    delta_frame = pd.DataFrame(
        {
            "Signal": ["Speed (%)", "Motor current (A)", "Vibration (mm/s)"],
            "Delta": [
                impact_kpis["speed_delta"],
                impact_kpis["current_delta"],
                impact_kpis["vibration_delta"],
            ],
        }
    )
    figure = px.bar(
        delta_frame,
        x="Signal",
        y="Delta",
        color="Signal",
        color_discrete_map=SIGNAL_COLORS,
        text="Delta",
        title="Process delta vs baseline",
        labels={"Delta": "Delta (%)"},
    )
    figure.add_hline(y=0, line_dash="dash", line_color="#64748b")
    figure.update_traces(texttemplate="%{y:+.1f}%", textposition="outside")
    figure.update_layout(
        title={"x": 0.0, "xanchor": "left"},
        showlegend=False,
        template="plotly_dark",
        plot_bgcolor="#101722",
        paper_bgcolor="#101722",
        font={"color": "#e2e8f0"},
        margin=dict(l=10, r=10, t=62, b=10),
        height=300,
    )
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(showgrid=True, gridcolor="#273347")
    return figure


def pct_change(new_value: float, baseline_value: float) -> float:
    if baseline_value == 0:
        return 0.0
    return 100.0 * (new_value - baseline_value) / baseline_value


def process_summary_kpis(process: pd.DataFrame) -> dict[str, float]:
    baseline = process.loc[
        process["timestamp"] <= (process["timestamp"].min() + pd.Timedelta(8, unit="m"))
    ]
    impact = process.loc[process.get("ground_truth_label", "") == "PROCESS_IMPACT"]
    if impact.empty:
        impact = process.loc[
            process["timestamp"].between(
                process["timestamp"].min() + pd.Timedelta(15, unit="m"),
                process["timestamp"].min() + pd.Timedelta(18, unit="m"),
            )
        ]

    baseline_speed = float(baseline["actual_speed_pct"].mean())
    baseline_current = float(baseline["motor_current_a"].mean())
    baseline_vibration = float(baseline["vibration_mm_s"].mean())

    impact_speed = float(impact["actual_speed_pct"].mean())
    impact_current = float(impact["motor_current_a"].mean())
    impact_vibration = float(impact["vibration_mm_s"].mean())

    return {
        "speed_now": impact_speed,
        "speed_delta": pct_change(impact_speed, baseline_speed),
        "current_now": impact_current,
        "current_delta": pct_change(impact_current, baseline_current),
        "vibration_now": impact_vibration,
        "vibration_delta": pct_change(impact_vibration, baseline_vibration),
    }


st.set_page_config(page_title="OT Sentinel Lite", page_icon="O", layout="wide")
require_outputs()
apply_theme()

summary = load_json(OUTPUT_DIR / "incident_summary.json")
events = load_csv(OUTPUT_DIR / "events.csv")
windows = load_csv(OUTPUT_DIR / "scored_incident_windows.csv")
plc_event = load_json(OUTPUT_DIR / "plc_forensics_event.json")
process = load_csv(PROCESS_INCIDENT)
config = load_json(CONFIG_PATH)
metrics = load_json(MODEL_METRICS_PATH) if MODEL_METRICS_PATH.exists() else {}
windows["window_start"] = pd.to_datetime(windows["window_start"], utc=True)
process["timestamp"] = pd.to_datetime(process["timestamp"], utc=True)

anomaly_threshold = float(config.get("anomaly_threshold", 75))
risk_points = config.get("risk_points", {})
display_events = prepare_events(events)

asset_frame = pd.DataFrame(summary.get("assets", []))
top_sources = (
    windows.groupby("src_ip", as_index=False)["conn_count"]
    .sum()
    .sort_values("conn_count", ascending=False)
    .rename(columns={"src_ip": "Source IP", "conn_count": "Connections"})
)

diff_rows: list[dict[str, str]] = []
for change_type in ("added", "removed", "modified"):
    diff_rows.extend(
        {"Change": change_type.title(), "Artifact": path}
        for path in plc_event.get(change_type, [])
    )
diff_frame = pd.DataFrame(diff_rows, columns=["Change", "Artifact"])

evidence_flags = summary.get("evidence_flags", {})
active_evidence = int(sum(bool(value) for value in evidence_flags.values()))
known_sources = set(config.get("baseline_sources", []))
plc_ip = str(summary.get("assets", [{"ip": config.get("plc_ip", "PLC")}])[0].get("ip", "PLC"))
incident_timeline = build_incident_timeline(display_events, process, windows)
compromise_time = to_utc_timestamp(incident_timeline.get("controller_tampered"))

timeline_figure = build_timeline_chart(display_events)
network_figure = build_network_chart(windows, anomaly_threshold, compromise_time)
flow_figure = build_asset_flow(windows, plc_ip, known_sources)
source_volume_figure = build_source_volume_chart(top_sources)
evidence_weight_figure = build_evidence_weight_chart(evidence_flags, risk_points)
process_figure = build_process_chart(process, compromise_time)
impact_kpis = process_summary_kpis(process)
process_delta_figure = build_process_delta_chart(impact_kpis)
severity_mix_figure = build_event_severity_chart(display_events)

event_count = int(summary.get("event_count", len(display_events)))
new_sources_count = int(
    windows.loc[windows.get("new_source", 0) == 1, "src_ip"].astype(str).nunique()
    if "new_source" in windows.columns
    else 0
)
active_weight = float(
    sum(float(risk_points.get(name, 0)) for name in TRIGGER_ORDER if evidence_flags.get(name, False))
)

render_sidebar(summary, anomaly_threshold, active_evidence)

st.markdown("<div class='page-title'>OT Visibility and Risk</div>", unsafe_allow_html=True)

render_section_title("operations-overview", "Operations Overview")
window_badge_text = incident_window_badge(
    to_utc_timestamp(incident_timeline.get("window_start")),
    to_utc_timestamp(incident_timeline.get("window_end")),
)
if window_badge_text:
    st.markdown(f"<div class='incident-window-badge'>{window_badge_text}</div>", unsafe_allow_html=True)

kpi_asset_col, kpi_external_col, kpi_event_col, kpi_trigger_col = st.columns(4)
kpi_asset_col.metric("Assets", f"{len(asset_frame)}")
kpi_external_col.metric("New sources", f"{new_sources_count}")
kpi_event_col.metric("Events", f"{event_count}")
kpi_trigger_col.metric("Triggers", f"{active_evidence} / {len(TRIGGER_ORDER)}")

status_col, risk_col, timeline_col = st.columns([1.35, 1.9, 2.25])
with status_col:
    render_status_card(
        str(summary.get("severity", "UNKNOWN")),
        float(summary.get("risk_score", 0)),
        anomaly_threshold,
    )

risk_col.plotly_chart(
    build_risk_gauge(float(summary.get("risk_score", 0)), anomaly_threshold),
    width="stretch",
    config=PLOTLY_CHART_CONFIG,
)
with timeline_col:
    render_incident_timeline_card(
        to_utc_timestamp(incident_timeline.get("first_suspicious")),
        to_utc_timestamp(incident_timeline.get("controller_tampered")),
        to_utc_timestamp(incident_timeline.get("process_disrupted")),
    )

render_verdict_card(
    summary.get("verdict", "No verdict generated."),
    summary.get("reasons", []),
    summary.get("severity", "LOW"),
)

st.markdown("<div class='section-title'>Asset and Evidence Distribution</div>", unsafe_allow_html=True)
st.plotly_chart(source_volume_figure, width="stretch", config=PLOTLY_CHART_CONFIG)
st.plotly_chart(evidence_weight_figure, width="stretch", config=PLOTLY_CHART_CONFIG)

render_section_title("behavior-analytics", "Behavior Analytics")
st.plotly_chart(network_figure, width="stretch", config=PLOTLY_CHART_CONFIG)
if timeline_figure is None:
    st.info("No correlated events were produced.")
else:
    st.plotly_chart(timeline_figure, width="stretch", config=PLOTLY_CHART_CONFIG)

st.markdown("<div class='section-title'>Process and Event Impact</div>", unsafe_allow_html=True)
process_left, process_right = st.columns([3, 2])
process_left.plotly_chart(process_figure, width="stretch", config=PLOTLY_CHART_CONFIG)
process_right.plotly_chart(process_delta_figure, width="stretch", config=PLOTLY_CHART_CONFIG)
process_right.plotly_chart(severity_mix_figure, width="stretch", config=PLOTLY_CHART_CONFIG)
st.caption("Process deltas compare PROCESS_IMPACT windows against an early-incident baseline.")

render_section_title("trigger-matrix", "Evidence Trigger Matrix")
st.caption(f"Active weighted contribution: {active_weight:.0f} points")
render_trigger_cards(evidence_flags, risk_points)

render_section_title("pipeline-data-flow", "Synthetic Pipeline Data Flow")
render_data_flow_panel()

render_section_title("audit-evidence", "Evidence and Audit Tables")
audit_asset_col, audit_source_col = st.columns([1, 1])
audit_asset_col.dataframe(asset_frame, width="stretch", hide_index=True)
audit_source_col.dataframe(top_sources.head(10), width="stretch", hide_index=True)

audit_tab_1, audit_tab_2, audit_tab_3, audit_tab_4 = st.tabs(
    [
        "Controller artifact delta",
        "Correlated event log",
        "Model metrics",
        "Network flow map",
    ]
)

with audit_tab_1:
    if diff_frame.empty:
        st.info("No artifact deltas found.")
    else:
        st.dataframe(diff_frame, width="stretch", hide_index=True)
    st.caption(plc_event.get("change_summary", "No artifact summary available."))

with audit_tab_2:
    if display_events.empty:
        st.info("No correlated events were produced.")
    else:
        timeline_table = display_events[[
            "timestamp",
            "event_label",
            "severity",
            "score",
            "source",
            "mitre_cue",
            "summary",
        ]].rename(columns={"event_label": "event"})
        st.dataframe(
            timeline_table,
            width="stretch",
            hide_index=True,
            column_config={"score": st.column_config.NumberColumn(format="%.1f")},
        )

with audit_tab_3:
    if metrics:
        st.json(metrics)
    else:
        st.info("model_metrics.json is not available in sample_output.")

with audit_tab_4:
    st.plotly_chart(flow_figure, width="stretch", config=PLOTLY_CHART_CONFIG)
