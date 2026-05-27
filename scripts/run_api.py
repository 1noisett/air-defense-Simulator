"""Launch the Air Defense Simulation API with uvicorn.

Usage:
    python scripts/run_api.py
"""
from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
