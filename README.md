# Air Defense Simulation

An educational backend simulation of anti-aircraft defense systems. This project focuses on pedagogical clarity, prioritising mathematical understanding over raw performance.

> **Note:** This project was developed entirely by **Claude Code** (Anthropic) as a demonstration of autonomous software engineering, physical simulation, and full-stack integration.

## Key Features

- **Handwritten Physics Engine:** Built from first principles using only the Python standard library. No `numpy` or `scipy` used in the core logic.
- **Numerical Integration:** Supports both explicit Euler and 4th-order Runge-Kutta (RK4) integrators with time-dependent state handling.
- **Guidance Systems:** Implements classical **Proportional Navigation (PN)** for interceptor missiles.
- **Sensor Simulation:** Includes a range-limited Radar model and a persistent `ThreatTracker` with data association, coasting, and track pruning logic.
- **Multi-Front-End:**
    - **Interactive GUI:** Built with Matplotlib widgets for real-time parameter tuning.
    - **Web API:** A FastAPI-based backend that serves simulation results.
    - **Modern Web UI:** A Vanilla JS frontend to visualise trajectories and engagement reports.

## Tech Stack

- **Backend:** Python 3.10+ (FastAPI, Pydantic, Pytest)
- **Visualisation:** Matplotlib
- **Frontend:** HTML5, CSS3, Vanilla JavaScript

## Project Structure

- `physics/`: Pure math and domain entities (missiles, threats, vectors).
- `sensors/`: Radar detection and tracking algorithms.
- `battery/`: Command and control logic (assessment and assignment).
- `simulation/`: Orchestration runner and event recording.
- `api/`: REST endpoints for web integration.
- `web/`: Frontend assets and visualization logic.

## How to Run

### 1. Requirements
Ensure you have Python 3.10+ installed. It is recommended to use a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Interactive Simulator (Desktop)
To launch the Matplotlib-based interactive tool:
```bash
python3 scripts/run_interactive.py
```

### 3. Web Application
To run the API and the web interface:
```bash
python3 scripts/run_api.py
```
Then visit `http://localhost:8000` in your browser.

## Engineering Standards

This project adheres to strict architectural rules defined in `CLAUDE.md`, including:
- Total decoupling of the physics layer.
- Full type-hinting across the entire codebase.
- Comprehensive unit testing suite (pytest).
- Google-style documentation with SI unit specifications.

---
*Created with 🤖 Claude Code.*
