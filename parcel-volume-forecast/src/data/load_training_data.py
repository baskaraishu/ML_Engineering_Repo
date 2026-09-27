from __future__ import annotations

"""Data-loading utilities for forecast training inputs.

This module defines the canonical Phase 1 table-loading and client-filtering
behavior so notebook logic can be reused in governed training jobs.
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from src.config import DEFAULT_SOURCE_TABLE, MIN_CLIENT_MEDIAN_VOLUME


def load_training_data(
    spark: SparkSession,
    source_table: str = DEFAULT_SOURCE_TABLE,
    champion_clients_table: str | None = None,
    min_client_median_volume: int = MIN_CLIENT_MEDIAN_VOLUME,
) -> DataFrame:
    """Load and filter training data for multi-client inbound uplift forecasting.

    This function captures the notebook's initial filtering pattern:
    - Load base dataset from a feature/curated table
    - Optionally restrict to clients present in champion client list
    - Drop low-volume clients using median daily volume threshold
    """
    df = spark.table(source_table)

    if champion_clients_table:
        champion_clients = spark.table(champion_clients_table).select("client_name").distinct()
        df = df.join(champion_clients, on="client_name", how="inner")

    client_medians = (
        df.groupBy("client_name")
        .agg(F.expr("percentile_approx(actual_volume, 0.5)").alias("median_daily_volume"))
    )

    valid_clients = client_medians.filter(F.col("median_daily_volume") > F.lit(min_client_median_volume)).select("client_name")

    return df.join(valid_clients, on="client_name", how="inner")
