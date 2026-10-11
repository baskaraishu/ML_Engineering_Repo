from __future__ import annotations

import os

from src.config import DEFAULT_SOURCE_TABLE, SOURCE_TABLE_ENV_VAR


"""Runtime source-table resolution helpers.

Phase 0 keeps loader interfaces explicit while centralizing local defaults.
Orchestration should pass source_table explicitly in production, but local
preflight runs can fall back to config defaults.
"""


def resolve_source_table(
    cli_source_table: str | None,
    env_source_table: str | None = None,
    config_default_source_table: str | None = DEFAULT_SOURCE_TABLE,
) -> str:
    """Resolve source_table with precedence: CLI -> env -> config default."""
    if cli_source_table and cli_source_table.strip():
        return cli_source_table.strip()

    resolved_env = env_source_table
    if resolved_env is None:
        resolved_env = os.getenv(SOURCE_TABLE_ENV_VAR)
    if resolved_env and resolved_env.strip():
        return resolved_env.strip()

    if config_default_source_table and config_default_source_table.strip():
        return config_default_source_table.strip()

    raise ValueError(
        "source_table could not be resolved. Provide CLI --source-table, set "
        f"{SOURCE_TABLE_ENV_VAR}, or configure DEFAULT_SOURCE_TABLE."
    )
