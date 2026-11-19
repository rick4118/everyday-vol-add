import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# --------------------------
# 核心爆量篩選邏輯
# --------------------------
class DailyExplosiveVolumeFinder:
    def __init__(self, tickers, start_date="2023-01-01", end_date=None, increase_threshold=1.5):
        self.tickers = tickers
        self.start_date = start_date
        self.increase_threshold = increase_threshold
        self.end_date = pd.to_datetime(end_date).strftime("%Y-%m-%d") if end_date else datetime.today().strftime("%Y-%m-%d")

    def fix_columns(self, df):
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        if "Close" not in df.columns and "Adj Close" in df.columns:
            df["Close"] = df["Adj Close"]
        volume_cols = [col for col in df.columns if "Volume" in col]
        if "Volume" not in df.columns and len(volume_cols) > 0:
            df["Volume"] = df[volume_cols[0]]
        return df if {"Open", "High", "Low", "Close", "Volume"}.issubset(df.columns) else None

    def get_daily(self, ticker):
        try:
            df = yf.download(ticker, start=self.start_date, end=self.end_date, auto_adjust=False, progress=False)
        except:
            return None

        df = self.fix_columns(df)
        if df is None or df.empty:
            return None

        df.index = pd.to_datetime(df.index)
        return df if len(df) >= 2 else None

    def run(self):
        results = []
        for ticker in self.tickers:
            daily = self.get_daily(ticker)
            if daily is None:
                continue

            date_str = daily.index[-1].strftime("%Y-%m-%d")
            vol_today = daily["Volume"].iloc[-1]
            vol_yesterday = daily["Volume"].iloc[-2]
            if vol_yesterday == 0:
                continue

            ratio = vol_today / vol_yesterday
            if ratio >= self.increase_threshold:
                results.append({
                    "Ticker": ticker,
                    "Date": date_str,
                    "TodayVolume": int(vol_today),
                    "YesterdayVolume": int(vol_yesterday),
                    "IncreaseFactor": round(ratio, 2),
                    "Increase%": f"{round((ratio - 1) * 100, 2)}%"
                })

        if not results:
            return pd.DataFrame()
        return pd.DataFrame(results).sort_values("IncreaseFactor", ascending=False).reset_index(drop=True)

# --------------------------
# Streamlit 介面
# --------------------------
st.set_page_config(page_title="每日爆量股票篩選器", layout="wide")

st.title("📈 每日爆量股票篩選器")
st.write("此工具可幫助您快速篩選出最新交易日成交量顯著放大的股票。")

# 側邊欄設定
st.sidebar.header("⚙️ 參數設定")

ticker_input = st.sidebar.text_area(
    "輸入股票代號 (以英文逗號隔開)",
    "2465.TW, 5426.TWO, 7704.TWO"
)

start_date = st.sidebar.date_input(
    "開始日期",
    datetime(2025, 1, 1)
)

end_date = st.sidebar.date_input(
    "結束日期",
    datetime.today()
)

increase_threshold = st.sidebar.slider(
    "爆量倍數門檻 (今日量/昨日量)",
    min_value=1.0,
    max_value=5.0,
    value=1.5,
    step=0.1
)

tickers = [t.strip() for t in ticker_input.split(",") if t.strip()]

# 開始搜尋按鈕
if st.sidebar.button("🔍 開始篩選", type="primary"):
    if not tickers:
        st.warning("⚠️ 請輸入至少一個股票代號")
    else:
        with st.spinner("正在下載數據並分析中，請稍候..."):
            finder = DailyExplosiveVolumeFinder(
                tickers=tickers,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                increase_threshold=increase_threshold
            )
            df_result = finder.run()
            
        if df_result.empty:
            st.info("⚠️ 在此設定條件下，查無符合爆量條件的股票。")
        else:
            st.success(f"✨ 篩選完成！共找到 {len(df_result)} 檔符合條件的股票。")
            
            # 呈現表格
            st.subheader("📊 篩選結果數據表")
            st.dataframe(df_result, use_container_width=True)
            
            # 最終名單清單
            st.subheader("🎯 最終符合條件股票清單")
            result_list = df_result["Ticker"].tolist()
            st.code(str(result_list), language="python")
