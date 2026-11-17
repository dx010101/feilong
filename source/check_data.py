import pandas as pd
import time

if __name__ == "__main__":
    print("begin loadin data...")
    start = time.time()
    # df = pd.read_csv("MarketData.csv")
    file_path = "/data/common/data_3s_temp/FirstLevel.csv"
    df = pd.read_csv("MarketData.csv", encoding="gbk")
    print("data loaded, begin stats cal..")
    # 修正ExchangeID筛选
    sh_df = df[df["ExchangeID"] == 1]  # 上海
    sz_df = df[df["ExchangeID"] == 2]  # 深圳，根据实际ExchangeID调整
    
    print(f"SH time: {sh_df['DataTimeStamp'].iloc[0]}, SZ time: {sz_df['DataTimeStamp'].iloc[0]}")
    
    # 时间戳转换（如果需要）
    sh_df["DataTimeStamp"] = sh_df["DataTimeStamp"] * 1000
    
    # 修正时间筛选条件语法
    sh_df = sh_df[(sh_df["DataTimeStamp"] >= 93500000) & (sh_df["DataTimeStamp"] <= 150000000)]
    sz_df = sz_df[(sz_df["DataTimeStamp"] >= 93500000) & (sz_df["DataTimeStamp"] <= 150000000)]
    
    # 计算延迟
    delay_sh = sh_df["LocalTimeStamp"] - sh_df["DataTimeStamp"]
    delay_sz = sz_df["LocalTimeStamp"] - sz_df["DataTimeStamp"]
    
    average_sh = delay_sh.mean()
    average_sz = delay_sz.mean()
    
    end = time.time()
    duration = end - start
    print(f"SH delay: {average_sh}")
    print(f"SZ delay: {average_sz}")
    print(f"total duration: {duration}")