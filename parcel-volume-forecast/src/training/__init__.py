"""Training package for the parcel volume forecast repository.

This package exposes training entrypoints and supports reuse by training
jobs and experimentation notebooks.
"""

from src.training.notebook_poc import run_notebook_launcher_poc

__all__ = ["run_notebook_launcher_poc"]
