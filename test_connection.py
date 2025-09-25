import websocket
import json
from kafka import KafkaProducer

def on_message(ws, message):
    data = json.loads(message)
    # print(f"Trade ID: {data['t']} | Price: {data['p']} | Quantity: {data['q']}")
    # print(len(data))
    # print(data[0].keys())
    for dat in data:
        if dat.get("s").startswith("BUSD"):
            print("CHECK")
        
def on_error(ws, error):
    print("Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("Closed connection")

def on_open(ws):
    print("Connected to Binance WebSocket!")

if __name__ == "__main__":
    socket_url = "wss://stream.binance.com:9443/ws/!ticker@arr"
    ws = websocket.WebSocketApp(socket_url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()
    