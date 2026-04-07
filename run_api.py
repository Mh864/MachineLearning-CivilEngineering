"""
Run the FastAPI backend with the repo root on sys.path.

Use this if `uvicorn api.app:app` fails with ModuleNotFoundError: No module named 'api'
(usually because the shell cwd is not the project root).

From anywhere:
  python path/to/MachineLearning-CivilEngineering/run_api.py

Or from repo root:
  python run_api.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[ROOT],
    )
