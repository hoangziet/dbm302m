import json
import logging
import os
import time
from datetime import date, datetime, timezone
from decimal import Decimal

import psycopg2
import websocket
from configs import BINANCE20
from psycopg2.extras import execute_values
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)

PG_CONN_INFO = dict(
    host = os.getenv("POSTGRES_HOST"),
    port = os.getenv("POSTGRES_PORT"),
    dbname = os.getenv("POSTGRES_DB"),
    user = os.getenv("POSTGRES_USER"),
    password = os.getenv("POSTGRES_PASSWORD")
)

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "200"))
FLUSH_SECS = float(os.getenv("FLUSH_SECS", "1.0"))



def to_decimal(s: str) -> Decimal: 
    return Decimal(s)


def to_ts_ms(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000.0,
                                  tz = timezone.utc).replace(tzinfo=None)
    

@retry(stop=stop_after_attempt(5),wait=wait_exponential(min=1, max=30))
def open_pg():
    return psycopg2.connect(**PG_CONN_INFO)

def insert_batch(conn, rows):
    if not rows: return 
    
    sql = """
        INSERT INTO public.coin_ticks (
            symbol, event_time, price, price_change, price_change_percent, high, low, volume, ingest_ts
        ) VALUES %s
        ON CONFLICT (symbol, event_time) DO NOTHING 
    """
    
    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
    conn.commit()
    
    
    
class Processor():
    def __init__(self):
        self.conn = open_pg()
        self.buffer = []
        self.last_flush = time.time()
        
    def handle_message(self, message: str):
        data = json.loads(message)
        if not isinstance(data, list): return 
        for dat in data:
            sym = dat.get("s")
            if sym not in BINANCE20: continue
            try:
                event_time = to_ts_ms(int(dat["E"]))
                price = to_decimal(dat["c"])
                price_change = to_decimal(dat["p"])
                price_change_percent = to_decimal(dat["P"])
                high = to_decimal(dat["h"])
                low = to_decimal(dat["l"])
                volume = to_decimal(dat["v"])
            except Exception as e:
                continue
        
            self.buffer.append((
                sym, event_time, price, price_change, price_change_percent, high, low, volume, datetime.utcnow()
            ))
        
        now = time.time()
        if len(self.buffer) >= BATCH_SIZE or (now - self.last_flush) >= FLUSH_SECS:
            try:
                insert_batch(self.conn, self.buffer)
                self.buffer.clear()
                self.last_flush = now
            except Exception as e:
                logging.error(f"Database error: {e}")
                try:
                    self.conn.close()
                except:
                    pass
                self.conn = open_pg()
        

def on_message(ws, message):
    ws.processor.handle_message(message)

def on_error(ws, error):
    logging.error(f"WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    logging.info("WebSocket connection closed:", close_status_code, close_msg)
    
def on_open(ws):
    logging.info("WebSocket connection opened")

def main():
    url = "wss://stream.binance.com:9443/ws/!ticker@arr"
    while True:
        try:
            ws = websocket.WebSocketApp(
                url, 
                on_open = on_open,
                on_message = on_message,
                on_error = on_error,
                on_close = on_close
            )
            ws.processor = Processor()
            ws.run_forever(ping_interval=15, ping_timeout=10)
        except Exception as e:
            logging.error("WebSocket connection error:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
    
    