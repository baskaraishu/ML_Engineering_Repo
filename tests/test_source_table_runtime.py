import pytest

from src.training.source_table_runtime import resolve_source_table


def test_resolve_source_table_cli_wins_over_env_and_config():
    resolved = resolve_source_table(
        cli_source_table="catalog.schema.cli_table",
        env_source_table="catalog.schema.env_table",
        config_default_source_table="catalog.schema.config_table",
    )

    assert resolved == "catalog.schema.cli_table"


def test_resolve_source_table_uses_env_when_cli_missing():
    resolved = resolve_source_table(
        cli_source_table=None,
        env_source_table="catalog.schema.env_table",
        config_default_source_table="catalog.schema.config_table",
    )

    assert resolved == "catalog.schema.env_table"


def test_resolve_source_table_uses_config_when_cli_and_env_missing():
    resolved = resolve_source_table(
        cli_source_table=None,
        env_source_table=None,
        config_default_source_table="catalog.schema.config_table",
    )

    assert resolved == "catalog.schema.config_table"


def test_resolve_source_table_raises_when_all_sources_missing():
    with pytest.raises(ValueError, match="source_table could not be resolved"):
        resolve_source_table(
            cli_source_table=None,
            env_source_table="",
            config_default_source_table="",
        )
