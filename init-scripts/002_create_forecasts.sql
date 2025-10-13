-- Create table for storing Prophet forecasts
CREATE TABLE IF NOT EXISTS public.coin_forecasts (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    forecast_time TIMESTAMP NOT NULL,
    predicted_price NUMERIC(38, 8) NOT NULL,
    lower_bound NUMERIC(38, 8),
    upper_bound NUMERIC(38, 8),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(symbol, forecast_time)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_coin_forecasts_symbol_time 
    ON public.coin_forecasts (symbol, forecast_time DESC);

CREATE INDEX IF NOT EXISTS idx_coin_forecasts_created_at 
    ON public.coin_forecasts (created_at DESC);

-- Create a view to combine actual and forecasted data
CREATE OR REPLACE VIEW public.coin_data_with_forecasts AS
SELECT 
    symbol,
    event_time as time,
    price as actual_price,
    NULL as predicted_price,
    NULL as lower_bound,
    NULL as upper_bound,
    'actual' as data_type,
    ingest_ts as timestamp
FROM public.coin_ticks

UNION ALL

SELECT 
    symbol,
    forecast_time as time,
    NULL as actual_price,
    predicted_price,
    lower_bound,
    upper_bound,
    'forecast' as data_type,
    created_at as timestamp
FROM public.coin_forecasts

ORDER BY symbol, time;