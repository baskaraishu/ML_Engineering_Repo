-- Serving view for latest parcel forecast outputs.
-- Consumer intent: downstream planners and reporting layers read one latest
-- prediction per (client_name, event_date) without handling run deduplication.
-- Refresh assumption: upstream scoring writes timestamped rows to
-- cent_analytics_gold.fcast_multi_client_ib_uplift_predictions.
--
-- This view protects downstream consumers from duplicate scored rows by
-- returning the most recent forecast per client and event date.
CREATE OR REPLACE VIEW cent_analytics_gold.vw_multi_client_ib_uplift_forecast AS
SELECT
    client_name,
    event_date,
    predicted_volume,
    model_version,
    run_id,
    scored_at
FROM cent_analytics_gold.fcast_multi_client_ib_uplift_predictions
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY client_name, event_date
    ORDER BY scored_at DESC
) = 1;
