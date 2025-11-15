# dbm302m - Cryptocurrency Real-time Analytics with Prophet Forecasting

## Tổng quan
Hệ thống phân tích và dự đoán giá cryptocurrency real-time sử dụng:
- **Data Collection**: Thu thập dữ liệu từ Binance WebSocket
- **Time Series Forecasting**: Facebook Prophet cho dự đoán giá
- **Visualization**: Apache Superset dashboard
- **Storage**: PostgreSQL database

## Kiến trúc hệ thống
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Binance API   │───▶│   Processor      │───▶│   PostgreSQL   │
│   (WebSocket)   │    │   Service        │    │   Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐             │
│   Apache        │◀───│   Prophet        │◀───────────┘
│   Superset      │    │   Forecaster     │
└─────────────────┘    └──────────────────┘
```

## 1. Tạo file `.env`
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

## 2. Compose các services
```bash
# Khởi động tất cả services bao gồm Prophet
docker compose up -d

# Kiểm tra trạng thái services
docker compose ps

# Xem logs của Prophet forecaster
docker compose logs -f prophet-forecaster
```

## 3. Các services và ports
- **PostgreSQL**: http://localhost:5432
- **Superset**: http://localhost:8088 (admin/admin)  
- **Prophet API**: http://localhost:5000

## 4. Prophet Time Series Forecasting

### Trigger dự đoán
```bash
# Dự đoán cho một symbol cụ thể
curl "http://localhost:5000/forecast/BTCUSDT?days=30&periods=24"

# Dự đoán batch cho tất cả symbols
curl "http://localhost:5000/forecast/batch"

# Kiểm tra health của service
curl "http://localhost:5000/health"
```

### Xem kết quả dự đoán
```sql
-- Xem dự đoán mới nhất
SELECT * FROM public.coin_forecasts 
WHERE symbol = 'BTCUSDT' 
ORDER BY forecast_time DESC 
LIMIT 24;

-- So sánh actual vs forecast
SELECT * FROM public.coin_data_with_forecasts 
WHERE symbol = 'BTCUSDT' 
    AND time >= NOW() - INTERVAL '7 days'
ORDER BY time;
```

## 5. Kết nối Superset với Postgres
- Truy cập Superset tại: **http://localhost:8088**  
- Kết nối bằng URI:
```text
postgresql+psycopg2://crypto:crypto@postgres:5432/crypto
```

- Dữ liệu thực tế: **public.coin_ticks**
- Dữ liệu dự đoán: **public.coin_forecasts** 
- View kết hợp: **public.coin_data_with_forecasts**

## 6. Import dashboard
```bash
docker exec -it dbm302m-superset-1 superset import-dashboards --path /app/superset_exports/dashboards.zip
```

## 7. Automated Prophet Forecasting

Hệ thống tự động chạy dự đoán:
- **Batch forecast**: Mỗi giờ cho tất cả 20 symbols
- **Priority symbols**: Mỗi 30 phút cho BTC, ETH, BNB, SOL

```bash
# Xem logs của scheduler
docker compose exec prophet-forecaster python scheduler.py
```

## 8. Hướng dẫn chi tiết

Xem file **PROPHET_GUIDE.md** để có hướng dẫn chi tiết về:
- Cách sử dụng Prophet API
- Tạo dashboard trong Superset  
- SQL queries hữu ích
- Monitoring và troubleshooting
- Tối ưu hóa performance

---

## 9. Database Schema

### Schema: `public.coin_ticks`

```sql
\d public.coin_ticks;
```

| Column               | Type                        | Nullable | Default |
|-----------------------|-----------------------------|----------|---------|
| symbol               | character varying(16)       | not null |         |
| event_time           | timestamp without time zone | not null |         |
| price                | numeric(38,8)               | not null |         |
| price_change         | numeric(38,8)               |          |         |
| price_change_percent | numeric(9,4)                |          |         |
| high                 | numeric(38,8)               |          |         |
| low                  | numeric(38,8)               |          |         |
| volume               | numeric(38,8)               |          |         |
| ingest_ts            | timestamp without time zone |          | now()   |

### Indexes
```text
"coin_ticks_pkey" PRIMARY KEY, btree (symbol, event_time)
"idx_coin_ticks_symbol_time_desc" btree (symbol, event_time DESC)
```

### Schema: `public.coin_forecasts`

| Column          | Type                        | Nullable | Default |
|-----------------|----------------------------|----------|---------|
| id              | serial                     | not null |         |
| symbol          | character varying(16)      | not null |         |
| forecast_time   | timestamp without time zone| not null |         |
| predicted_price | numeric(38,8)              | not null |         |
| lower_bound     | numeric(38,8)              |          |         |
| upper_bound     | numeric(38,8)              |          |         |
| created_at      | timestamp without time zone|          | now()   |

### Key Features
- ✅ **Real-time data collection** từ Binance WebSocket
- ✅ **Time series forecasting** với Facebook Prophet  
- ✅ **Interactive dashboards** trong Apache Superset
- ✅ **Automated scheduling** cho dự đoán định kỳ
- ✅ **RESTful API** cho integration
- ✅ **Confidence intervals** cho đánh giá risk

## 6. Import dashboard
```bash
docker exec -it dbm302m-superset-1 superset import-dashboards --path /app/superset_exports/dashboards.zip

```
