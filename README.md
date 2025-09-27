# dbm302m

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
docker compose up -d postgres superset processor
```

## 3. Kết nối Superset với Postgres
- Truy cập Superset tại: **http://localhost:8088**  
- Kết nối bằng URI:
```text
postgresql+psycopg2://crypto:crypto@postgres:5432/crypto
```
- Dữ liệu được lưu ở bảng: **public.coin_ticks**

---

## Schema: `public.coin_ticks`

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
