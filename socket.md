Binance Websocket Response 
```
{
  'e': '24hrTicker',     # event type (sự kiện gì) 
  'E': 1727069554471,    # event time (timestamp ms)
  's': 'BTCUSDT',        # symbol (cặp coin)
  'p': '100.00',         # price change (giá thay đổi so với 24h trước)
  'P': '0.5',            # price change percent (tỉ lệ % thay đổi giá 24h)
  'w': '20000.25',       # weighted avg price (giá trung bình gia quyền 24h)
  'x': '19900.00',       # first trade price (giá mở cửa 24h trước)
  'c': '20000.00',       # last price (giá cuối cùng hiện tại)
  'Q': '0.1',            # last qty (khối lượng của lệnh cuối cùng)
  'b': '19999.00',       # best bid price (giá mua cao nhất hiện tại)
  'B': '1.5',            # best bid qty (số lượng đặt mua ở giá cao nhất)
  'a': '20001.00',       # best ask price (giá bán thấp nhất hiện tại)
  'A': '2.0',            # best ask qty (số lượng đặt bán ở giá thấp nhất)
  'o': '19900.00',       # open price (giá mở cửa 24h)
  'h': '20100.00',       # high price (giá cao nhất 24h)
  'l': '19800.00',       # low price (giá thấp nhất 24h)
  'v': '1234.56',        # volume (khối lượng giao dịch 24h)
  'q': '24691357.89',    # quote volume (giá trị volume tính theo USDT)
  'O': 1726983154471,    # open time (timestamp ms mở cửa 24h)
  'C': 1727069554471,    # close time (timestamp ms đóng cửa 24h)
  'F': 100,              # first trade ID (id lệnh đầu tiên 24h)
  'L': 200,              # last trade ID (id lệnh cuối cùng 24h)
  'n': 101               # total trades (số lượng lệnh giao dịch trong 24h)
}
```
