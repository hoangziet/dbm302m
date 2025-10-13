# Hướng dẫn sử dụng Prophet Time Series Forecasting trong Superset

## Tổng quan

Hệ thống đã được tích hợp thành công với Facebook Prophet để dự đoán giá cryptocurrency. Các thành phần chính:

1. **Prophet Forecaster Service**: API service để tạo dự đoán
2. **Database Schema**: Bảng lưu trữ kết quả dự đoán
3. **Superset Integration**: Dashboard hiển thị dữ liệu và dự đoán
4. **Automated Scheduling**: Tự động chạy dự đoán định kỳ

## Cấu trúc hệ thống

```
services/
├── processor/              # Thu thập dữ liệu từ Binance
├── prophet-forecaster/     # Service dự đoán Prophet
│   ├── app.py             # Main API application
│   ├── scheduler.py       # Tự động hóa dự đoán
│   ├── configs.py         # Cấu hình symbols
│   ├── requirements.txt   # Dependencies
│   └── Dockerfile         # Container config
init-scripts/
├── 001_create_coin_ticks.sql    # Bảng dữ liệu thực tế
└── 002_create_forecasts.sql     # Bảng dự đoán và view
superset_configs/
├── prophet_integration.py       # Tích hợp Prophet với Superset
├── superset_config.py          # Cấu hình Superset
└── sample_queries.sql          # SQL queries mẫu
```

## Khởi động hệ thống

### 1. Tạo file .env
```env
POSTGRES_USER=crypto
POSTGRES_PASSWORD=crypto
POSTGRES_DB=crypto
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

ADMIN_USERNAME=admin
ADMIN_FIRSTNAME=Admin
ADMIN_LASTNAME=User
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin
```

### 2. Khởi động các services
```bash
# Khởi động tất cả services
docker compose up -d

# Kiểm tra trạng thái
docker compose ps

# Xem logs của Prophet service
docker compose logs -f prophet-forecaster
```

### 3. Kiểm tra kết nối

**Prophet Service**: http://localhost:5000
```bash
curl http://localhost:5000/health
```

**Superset**: http://localhost:8088 (admin/admin)

## Sử dụng Prophet API

### Endpoints chính

#### 1. Health Check
```bash
GET http://localhost:5000/health
```

#### 2. Dự đoán cho một symbol
```bash
GET http://localhost:5000/forecast/BTCUSDT?days=30&periods=24
```
- `days`: Số ngày dữ liệu lịch sử để train model (mặc định: 30)
- `periods`: Số giờ dự đoán (mặc định: 24)

#### 3. Dự đoán batch cho tất cả symbols
```bash
GET http://localhost:5000/forecast/batch
```

### Ví dụ Response
```json
{
  "symbol": "BTCUSDT",
  "forecast_periods": 24,
  "training_days": 30,
  "forecast": [
    {
      "time": "2025-10-12T15:00:00",
      "predicted_price": 45230.50,
      "lower_bound": 44800.25,
      "upper_bound": 45660.75
    },
    ...
  ]
}
```

## Database Schema

### Bảng coin_forecasts
```sql
CREATE TABLE public.coin_forecasts (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    forecast_time TIMESTAMP NOT NULL,
    predicted_price NUMERIC(38, 8) NOT NULL,
    lower_bound NUMERIC(38, 8),
    upper_bound NUMERIC(38, 8),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(symbol, forecast_time)
);
```

### View coin_data_with_forecasts
Kết hợp dữ liệu thực tế và dự đoán để dễ dàng visualize trong Superset.

## Superset Dashboard

### SQL Queries hữu ích

#### 1. Xem dữ liệu thực tế vs dự đoán
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
WHERE symbol = 'BTCUSDT'
    AND time >= NOW() - INTERVAL '7 days'
ORDER BY time;
```

#### 2. Dashboard real-time
```sql
SELECT 
    c.symbol,
    c.event_time,
    c.price as current_price,
    c.price_change_percent,
    f.predicted_price as next_hour_forecast,
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
        symbol, predicted_price
    FROM public.coin_forecasts
    WHERE forecast_time >= NOW()
    ORDER BY symbol, forecast_time ASC
) f ON c.symbol = f.symbol;
```

#### 3. Phân tích độ chính xác
```sql
WITH forecast_vs_actual AS (
    SELECT 
        f.symbol,
        f.predicted_price,
        a.price as actual_price,
        ABS(f.predicted_price - a.price) / a.price * 100 as error_percent
    FROM public.coin_forecasts f
    INNER JOIN public.coin_ticks a ON f.symbol = a.symbol
        AND ABS(EXTRACT(EPOCH FROM (f.forecast_time - a.event_time))) < 1800
    WHERE f.forecast_time < NOW() - INTERVAL '1 hour'
)
SELECT 
    symbol,
    COUNT(*) as total_forecasts,
    ROUND(AVG(error_percent), 2) as avg_error_percent
FROM forecast_vs_actual
GROUP BY symbol
ORDER BY avg_error_percent;
```

### Tạo Charts trong Superset

#### 1. Line Chart - Price với Forecast
- **Dataset**: coin_data_with_forecasts
- **X-axis**: time
- **Metrics**: actual_price, predicted_price
- **Group by**: symbol, data_type
- **Filters**: symbol = 'BTCUSDT', time >= 7 days ago

#### 2. Line Chart - Confidence Bands
- **Dataset**: coin_forecasts
- **X-axis**: forecast_time
- **Metrics**: predicted_price, lower_bound, upper_bound
- **Group by**: symbol
- **Filters**: created_at >= 2 hours ago

#### 3. Table - Real-time Status
- **Dataset**: SQL query (dashboard real-time query above)
- **Columns**: symbol, current_price, price_change_percent, forecast_sentiment

## Tự động hóa

### Scheduler Service
Service tự động chạy dự đoán:
- **Batch forecast**: Mỗi giờ cho tất cả symbols
- **Priority symbols**: Mỗi 30 phút cho BTC, ETH, BNB, SOL

### Cron Jobs (tuỳ chọn)
```bash
# Chạy batch forecast mỗi giờ
0 * * * * curl -X GET http://localhost:5000/forecast/batch

# Chạy dự đoán cho BTC mỗi 30 phút
*/30 * * * * curl -X GET "http://localhost:5000/forecast/BTCUSDT?periods=24"
```

## Monitoring và Troubleshooting

### Kiểm tra logs
```bash
# Prophet service logs
docker compose logs prophet-forecaster

# Database logs
docker compose logs postgres

# Superset logs
docker compose logs superset
```

### Metrics quan trọng
1. **Forecast accuracy**: Theo dõi % error trung bình
2. **API response time**: Thời gian tạo dự đoán
3. **Data freshness**: Thời gian delay của dữ liệu
4. **Model performance**: R² score, MAE, RMSE

### Troubleshooting phổ biến

#### Prophet service không khởi động
```bash
# Kiểm tra dependencies
docker compose exec prophet-forecaster pip list

# Kiểm tra kết nối database
docker compose exec prophet-forecaster python -c "import psycopg2; print('DB OK')"
```

#### Không có dữ liệu dự đoán
```bash
# Kiểm tra dữ liệu trong database
docker compose exec postgres psql -U crypto -d crypto -c "SELECT COUNT(*) FROM coin_ticks;"

# Trigger manual forecast
curl -X GET "http://localhost:5000/forecast/BTCUSDT"
```

#### Superset không hiển thị charts
1. Kiểm tra database connection trong Superset
2. Verify datasets đã được tạo
3. Check SQL queries syntax

## Tối ưu hóa

### Model Parameters
Trong `services/prophet-forecaster/app.py`, có thể tuning:
```python
model = Prophet(
    daily_seasonality=True,
    weekly_seasonality=True,
    yearly_seasonality=False,
    changepoint_prior_scale=0.05,  # Giảm = ít flexible hơn
    seasonality_prior_scale=10.0,   # Tăng = theo seasonality nhiều hơn
    interval_width=0.8              # Confidence interval width
)
```

### Performance Tuning
1. **Batch size**: Tăng batch size cho việc insert forecast
2. **Caching**: Enable caching trong Superset
3. **Indexing**: Thêm indexes cho queries thường dùng
4. **Parallel processing**: Xử lý multiple symbols song song

## Mở rộng

### Thêm indicators khác
1. **Technical indicators**: RSI, MACD, Bollinger Bands
2. **Sentiment analysis**: News sentiment, social media
3. **External factors**: Market cap, volume, correlation

### Alerts và Notifications
1. **Price alerts**: Khi giá vượt ngưỡng dự đoán
2. **Accuracy alerts**: Khi độ chính xác giảm
3. **System alerts**: Khi services gặp lỗi

### Machine Learning enhancements
1. **Ensemble models**: Kết hợp Prophet với LSTM, ARIMA
2. **Feature engineering**: Thêm external features
3. **AutoML**: Tự động tuning hyperparameters