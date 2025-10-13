# 🚀 Manual Superset Dashboard Setup for Prophet Forecasting

## 🎯 Success Summary
✅ **Prophet Forecasting is Working!**
- 1,140 forecasts generated for 19 cryptocurrency symbols
- Real-time minute-level predictions available
- Database tables: `coin_ticks`, `coin_forecasts`, `coin_data_with_forecasts`
- API endpoints working at http://localhost:5000

## 📊 Manual Superset Setup Steps

### Step 1: Access Superset
1. Open your browser and go to: **http://localhost:8088**
2. Login with:
   - Username: `admin`
   - Password: `admin`

### Step 2: Create Database Connection
1. Go to **Settings** → **Database Connections**
2. Click **+ Database**
3. Select **PostgreSQL**
4. Fill in the connection details:
   ```
   Host: postgres
   Port: 5432
   Database: crypto
   Username: crypto
   Password: crypto
   ```
5. Or use the full URI:
   ```
   postgresql+psycopg2://crypto:crypto@postgres:5432/crypto
   ```
6. Test the connection and save

### Step 3: Create Datasets
Go to **Data** → **Datasets** and create these datasets:

1. **coin_ticks** (actual price data)
2. **coin_forecasts** (Prophet predictions)
3. **coin_data_with_forecasts** (combined view)

### Step 4: Sample SQL Queries for Charts

#### Query 1: Real-time Crypto Dashboard
```sql
SELECT 
    c.symbol,
    c.price as current_price,
    c.price_change_percent as current_change,
    f.predicted_price as next_forecast,
    f.lower_bound,
    f.upper_bound,
    CASE 
        WHEN f.predicted_price > c.price THEN 'BULLISH 📈'
        WHEN f.predicted_price < c.price THEN 'BEARISH 📉'
        ELSE 'NEUTRAL ➡️'
    END as forecast_sentiment,
    ROUND(((f.predicted_price - c.price) / c.price * 100), 2) as predicted_change_percent
FROM (
    SELECT DISTINCT ON (symbol) 
        symbol, price, price_change_percent, event_time
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
ORDER BY predicted_change_percent DESC NULLS LAST;
```

#### Query 2: Price History with Forecasts (Time Series)
```sql
SELECT 
    symbol,
    time,
    actual_price,
    predicted_price,
    lower_bound,
    upper_bound,
    data_type
FROM public.coin_data_with_forecasts
WHERE symbol IN ('BTCUSDT', 'ETHUSDT', 'SOLUSDT')  -- Top coins
    AND time >= NOW() - INTERVAL '6 hours'
ORDER BY symbol, time;
```

#### Query 3: Top Movers Forecast
```sql
WITH price_forecasts AS (
    SELECT 
        c.symbol,
        c.price as current_price,
        f.predicted_price,
        ROUND(((f.predicted_price - c.price) / c.price * 100), 2) as predicted_change_percent,
        c.price_change_percent as current_24h_change
    FROM (
        SELECT DISTINCT ON (symbol) 
            symbol, price, price_change_percent
        FROM public.coin_ticks 
        ORDER BY symbol, event_time DESC
    ) c
    INNER JOIN (
        SELECT DISTINCT ON (symbol)
            symbol, predicted_price
        FROM public.coin_forecasts
        WHERE forecast_time >= NOW()
        ORDER BY symbol, forecast_time ASC
    ) f ON c.symbol = f.symbol
)
SELECT 
    symbol,
    current_price,
    predicted_price,
    current_24h_change,
    predicted_change_percent,
    CASE 
        WHEN predicted_change_percent > 2 THEN '🚀 Strong Bull'
        WHEN predicted_change_percent > 0 THEN '📈 Bullish'
        WHEN predicted_change_percent < -2 THEN '💥 Strong Bear'
        WHEN predicted_change_percent < 0 THEN '📉 Bearish'
        ELSE '➡️ Neutral'
    END as signal
FROM price_forecasts
ORDER BY predicted_change_percent DESC;
```

#### Query 4: Forecast Accuracy Tracker
```sql
WITH forecast_accuracy AS (
    SELECT 
        f.symbol,
        f.predicted_price,
        a.price as actual_price,
        ABS(f.predicted_price - a.price) / a.price * 100 as error_percent,
        f.forecast_time,
        a.event_time
    FROM public.coin_forecasts f
    INNER JOIN public.coin_ticks a ON f.symbol = a.symbol
        AND ABS(EXTRACT(EPOCH FROM (f.forecast_time - a.event_time))) < 300
    WHERE f.forecast_time BETWEEN NOW() - INTERVAL '2 hours' AND NOW() - INTERVAL '30 minutes'
)
SELECT 
    symbol,
    COUNT(*) as predictions_tested,
    ROUND(AVG(error_percent), 2) as avg_error_percent,
    ROUND(MIN(error_percent), 2) as best_accuracy,
    ROUND(MAX(error_percent), 2) as worst_accuracy,
    CASE 
        WHEN AVG(error_percent) < 1 THEN '🎯 Excellent'
        WHEN AVG(error_percent) < 3 THEN '✅ Good'
        WHEN AVG(error_percent) < 5 THEN '⚠️ Fair'
        ELSE '❌ Poor'
    END as accuracy_rating
FROM forecast_accuracy
GROUP BY symbol
ORDER BY avg_error_percent;
```

### Step 5: Create Charts

#### Chart 1: Real-time Dashboard (Table)
- **Chart Type**: Table
- **SQL**: Use Query 1 above
- **Refresh**: Every 5 minutes

#### Chart 2: Price Trends (Line Chart)
- **Chart Type**: Line Chart
- **SQL**: Use Query 2 above
- **X-axis**: time
- **Metrics**: actual_price, predicted_price
- **Group by**: symbol, data_type

#### Chart 3: Forecast Signals (Big Number)
- **Chart Type**: Big Number with Trendline
- **SQL**: Use Query 3 above
- **Metric**: predicted_change_percent

#### Chart 4: Model Performance (Bar Chart)
- **Chart Type**: Bar Chart
- **SQL**: Use Query 4 above
- **X-axis**: symbol
- **Metric**: avg_error_percent

### Step 6: Create Dashboard
1. Go to **Dashboards** → **+ Dashboard**
2. Name it: "Crypto Prophet Forecasting"
3. Add all the charts created above
4. Arrange them in a logical layout
5. Set auto-refresh to 5 minutes

## 🔄 Automated Forecasting

Your system is now running automated forecasts! Here's what's happening:

### Current Status
```bash
# Check forecast count
docker compose exec postgres psql -U crypto -d crypto -c "SELECT COUNT(*) as forecasts, COUNT(DISTINCT symbol) as symbols FROM coin_forecasts;"

# Generate new forecasts
curl "http://localhost:5000/forecast/batch"

# Check specific symbol
curl "http://localhost:5000/forecast/BTCUSDT?granularity=minute&hours=3&periods=60"
```

### API Endpoints Summary
- **Individual Forecast**: `GET /forecast/{symbol}?granularity=minute&hours=3&periods=60`
- **Batch Forecast**: `GET /forecast/batch`
- **Health Check**: `GET /health`
- **Service Info**: `GET /`

### Key Features Working ✅
1. **Real-time Data Collection** - Binance WebSocket → PostgreSQL
2. **Prophet Time Series Forecasting** - Minute-level predictions
3. **Confidence Intervals** - Upper/lower bounds for risk assessment
4. **Batch Processing** - All 19 symbols at once
5. **Database Integration** - Forecasts saved with metadata
6. **RESTful API** - Easy integration and testing
7. **Flexible Granularity** - Minute or hourly forecasts
8. **Superset Ready** - All tables and views created

## 🎯 Next Steps

1. **Access Superset**: http://localhost:8088 (admin/admin)
2. **Set up charts** using the SQL queries above
3. **Create dashboard** combining all visualizations
4. **Schedule forecasts** to run automatically
5. **Monitor accuracy** and tune Prophet parameters as needed

## 🚀 Advanced Usage

### Trigger forecasts for specific symbols:
```bash
curl "http://localhost:5000/forecast/BTCUSDT?granularity=minute&hours=2&periods=30"
curl "http://localhost:5000/forecast/ETHUSDT?granularity=minute&hours=1&periods=60"
```

### Check recent forecasts:
```sql
SELECT symbol, forecast_time, predicted_price, created_at 
FROM coin_forecasts 
WHERE created_at >= NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

🎉 **Congratulations!** Your Prophet-powered cryptocurrency forecasting system is fully operational!