CREATE TABLE IF NOT EXISTS public.coin_ticks (
  symbol VARCHAR(16) NOT NULL,
  event_time TIMESTAMP NOT NULL,
  price NUMERIC(38, 8) NOT NULL,
  price_change NUMERIC(38, 8),
  price_change_percent NUMERIC(9, 4),
  high NUMERIC(38, 8),
  low NUMERIC(38, 8),
  volume NUMERIC(38, 8),
  ingest_ts TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (symbol, event_time)
);

CREATE INDEX IF NOT EXISTS idx_coin_ticks_symbol_time_desc
  ON public.coin_ticks (symbol, event_time DESC);
