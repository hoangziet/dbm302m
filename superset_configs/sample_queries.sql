-- Sample SQL queries for Prophet integration in Superset

-- 1. View actual vs forecast data for a specific symbol
-- Usage: Replace 'BTCUSDT' with any supported symbol
SELECT 
    symbol,
    time,
    actual_price,
    predicted_price,
    lower_bound,
    upper_bound,
    data_type
FROM public.coin_data_with_forecasts
WHERE symbol = 'BTCUSDT'
    AND time >= NOW() - INTERVAL '7 days'
ORDER BY time;

-- 2. Latest actual prices and next 24h forecasts
WITH latest_actual AS (
    SELECT 
        symbol,
        MAX(event_time) as latest_time,
        price as latest_price
    FROM public.coin_ticks 
    WHERE event_time >= NOW() - INTERVAL '1 hour'
    GROUP BY symbol, price
),
latest_forecast AS (
    SELECT 
        symbol,
        forecast_time,
        predicted_price,
        lower_bound,
        upper_bound,
        ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY forecast_time) as forecast_rank
    FROM public.coin_forecasts
    WHERE created_at >= NOW() - INTERVAL '2 hours'
        AND forecast_time > NOW()
)
SELECT 
    a.symbol,
    a.latest_time,
    a.latest_price,
    f.forecast_time,
    f.predicted_price,
    f.lower_bound,
    f.upper_bound,
    ROUND(((f.predicted_price - a.latest_price) / a.latest_price * 100), 2) as predicted_change_percent
FROM latest_actual a
LEFT JOIN latest_forecast f ON a.symbol = f.symbol
WHERE f.forecast_rank <= 24  -- Next 24 hours
ORDER BY a.symbol, f.forecast_time;

-- 3. Forecast accuracy analysis (compare predictions with actual values)
WITH forecast_vs_actual AS (
    SELECT 
        f.symbol,
        f.forecast_time,
        f.predicted_price,
        f.lower_bound,
        f.upper_bound,
        a.price as actual_price,
        ABS(f.predicted_price - a.price) as absolute_error,
        ABS(f.predicted_price - a.price) / a.price * 100 as percentage_error,
        CASE 
            WHEN a.price BETWEEN f.lower_bound AND f.upper_bound THEN true 
            ELSE false 
        END as within_bounds
    FROM public.coin_forecasts f
    INNER JOIN public.coin_ticks a ON f.symbol = a.symbol
        AND ABS(EXTRACT(EPOCH FROM (f.forecast_time - a.event_time))) < 1800  -- 30 minutes tolerance
    WHERE f.forecast_time < NOW() - INTERVAL '1 hour'  -- Only past forecasts
)
SELECT 
    symbol,
    COUNT(*) as total_forecasts,
    ROUND(AVG(percentage_error), 2) as avg_error_percent,
    ROUND(STDDEV(percentage_error), 2) as error_std_dev,
    ROUND(AVG(CASE WHEN within_bounds THEN 1.0 ELSE 0.0 END) * 100, 2) as accuracy_within_bounds_percent
FROM forecast_vs_actual
GROUP BY symbol
ORDER BY avg_error_percent;

-- 4. Top performing and worst performing forecasts
SELECT 
    symbol,
    forecast_time,
    predicted_price,
    'actual_price_placeholder' as actual_price,  -- This would need real-time data
    'error_placeholder' as error_percent,
    'performance_rank' as rank
FROM public.coin_forecasts
WHERE created_at >= NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC
LIMIT 100;

-- 5. Hourly price volatility for better Prophet model parameters
SELECT 
    symbol,
    DATE_TRUNC('hour', event_time) as hour,
    COUNT(*) as tick_count,
    MIN(price) as min_price,
    MAX(price) as max_price,
    AVG(price) as avg_price,
    STDDEV(price) as price_volatility,
    (MAX(price) - MIN(price)) / AVG(price) * 100 as hourly_volatility_percent
FROM public.coin_ticks
WHERE event_time >= NOW() - INTERVAL '7 days'
GROUP BY symbol, DATE_TRUNC('hour', event_time)
ORDER BY symbol, hour DESC;

-- 6. Real-time dashboard query - Latest data with forecasts
SELECT 
    c.symbol,
    c.event_time,
    c.price as current_price,
    c.price_change_percent as current_change_percent,
    f.predicted_price as next_hour_forecast,
    f.lower_bound as forecast_lower,
    f.upper_bound as forecast_upper,
    CASE 
        WHEN f.predicted_price > c.price THEN 'BULLISH'
        WHEN f.predicted_price < c.price THEN 'BEARISH'
        ELSE 'NEUTRAL'
    END as forecast_sentiment
FROM (
    SELECT DISTINCT ON (symbol) 
        symbol, event_time, price, price_change_percent
    FROM public.coin_ticks 
    ORDER BY symbol, event_time DESC
) c
LEFT JOIN (
    SELECT DISTINCT ON (symbol)
        symbol, predicted_price, lower_bound, upper_bound
    FROM public.coin_forecasts
    WHERE forecast_time >= NOW()
    ORDER BY symbol, forecast_time ASC
) f ON c.symbol = f.symbol
ORDER BY c.symbol;