import requests
import pandas as pd
import time
import matplotlib.pyplot as plt
import seaborn as sns

# Cấu hình thông số
symbol = "ETHUSDT"  # Cặp giao dịch (đổi thành ETHUSDT)
current_time = int(time.time() * 1000)  # Thời gian hiện tại (milliseconds)
time_threshold = current_time - (5 * 60 * 1000)  # Trừ đi 5 phút

# Danh sách lưu trữ tất cả giao dịch
total_trades = []
limit = 1000  # Giới hạn mỗi lần request (Binance tối đa 1000)
last_trade_id = None  # Lưu ID của giao dịch cuối cùng để request tiếp

# Lặp để lấy tất cả giao dịch trong khoảng thời gian 5 phút
while True:
    url = f"https://api.binance.com/api/v3/historicalTrades?symbol={symbol}&limit={limit}"
    if last_trade_id:
        url += f"&fromId={last_trade_id}"
    
    response = requests.get(url)
    trades = response.json()
    
    if not trades:
        break  # Nếu không có dữ liệu, thoát vòng lặp
    
    # Chuyển dữ liệu thành DataFrame tạm thời
    df_temp = pd.DataFrame(trades)[["time", "isBuyerMaker", "price", "qty", "id"]]
    df_temp["time"] = pd.to_datetime(df_temp["time"], unit="ms")
    df_temp["side"] = df_temp["isBuyerMaker"].apply(lambda x: "SELL" if x else "BUY")
    df_temp["qty"] = df_temp["qty"].astype(float)
    
    # Lọc giao dịch trong vòng 5 phút
    df_temp = df_temp[df_temp["time"] >= pd.to_datetime(time_threshold, unit="ms")]
    
    if df_temp.empty:
        break  # Nếu không còn giao dịch nào trong khoảng thời gian mong muốn, dừng lại
    
    total_trades.append(df_temp)
    
    # Cập nhật ID của giao dịch cuối cùng để lấy tiếp
    last_trade_id = df_temp["id"].max() + 1
    
    time.sleep(0.2)  # Nghỉ 0.2 giây để tránh quá tải API

# Ghép tất cả dữ liệu lại nếu có dữ liệu
if total_trades:
    df = pd.concat(total_trades, ignore_index=True)
    
    # Lọc bỏ các giao dịch có qty <= 0
    df = df[df["qty"] > 0]
    
    # Xác định các tứ phân vị
    Q1 = df["qty"].quantile(0.25)
    Q3 = df["qty"].quantile(0.75)
    
    # Phân loại kích thước giao dịch theo tứ phân vị
    def categorize_trade(qty):
        if qty >= Q3:
            return "Large"
        elif qty >= Q1:
            return "Medium"
        else:
            return "Small"
    
    df["trade_size"] = df["qty"].apply(categorize_trade)
    
    # Tính tổng khối lượng mua & bán theo từng nhóm
    summary = df.groupby(["trade_size", "side"])["qty"].sum().unstack(fill_value=0)
    summary["Inflow"] = summary.get("BUY", 0) - summary.get("SELL", 0)
    
    # Thêm cột tổng cộng
    total_row = summary.sum()
    total_row.name = "Total"
    summary = pd.concat([summary, total_row.to_frame().T])
    
    # Định dạng số liệu với ký hiệu "K"
    def format_k(value):
        return f"{value / 1000:.2f}K" if value >= 1000 else f"{value:.2f}"
    
    summary = summary.applymap(format_k)
    
    # Xuất bảng dữ liệu tổng hợp
    print(summary)
    
    # Lưu thành file CSV
    file_name = "binance_trades_summary.csv"
    summary.to_csv(file_name)
    
    print(f"✅ Đã lưu bảng tổng hợp giao dịch vào {file_name}")
    
    # Vẽ biểu đồ hình tròn (Donut Chart)
    plt.figure(figsize=(8, 8))
    buy_sizes = df[df["side"] == "BUY"]["trade_size"].value_counts()
    sell_sizes = df[df["side"] == "SELL"]["trade_size"].value_counts()
    
    labels = [f"Buy {label}" for label in buy_sizes.index] + [f"Sell {label}" for label in sell_sizes.index]
    sizes = list(buy_sizes.values) + list(sell_sizes.values)
    colors = ["#4CAF50", "#66BB6A", "#81C784", "#E57373", "#EF5350", "#D32F2F"]
    
    plt.pie(sizes, labels=labels, autopct="%.2f%%", colors=colors, wedgeprops={"edgecolor": "black"})
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    plt.gca().add_artist(centre_circle)
    plt.title(f"Trade Size Distribution for {symbol}")
    plt.show()
    
else:
    print("⚠️ Không có giao dịch nào trong 5 phút gần nhất.")