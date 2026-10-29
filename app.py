from datetime import date
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="稼動率料金變動比對系統", layout="centered")

st.title("稼動率料金變動比對系統")

# --- 1. 最新精確淡旺季（含例外日期）與天數階梯料金計算邏輯 ---
def calculate_price(month, day, days_diff, util):
    md = (month, day)

    # 判斷是否為旺季：
    # 12/29~1/3、1/9~1/12、3/19~5/23、7/17~8/31、9/18~9/26、10/15~11/30
    is_peak_season = (
        (md >= (12, 29) or md <= (1, 3)) or
        ((1, 9) <= md <= (1, 12)) or
        ((3, 19) <= md <= (5, 23)) or
        ((7, 17) <= md <= (8, 31)) or
        ((9, 18) <= md <= (9, 26)) or
        ((10, 15) <= md <= (11, 30))
    )

    is_low_season = not is_peak_season

    # 【淡季對照表】
    if is_low_season:
        if util <= 20.0:
            if days_diff >= 61: return 11000
            elif 31 <= days_diff <= 60: return 11500
            else: return 11000  # 0~30天
        elif util <= 30.0:
            if days_diff >= 61: return 11500
            elif 31 <= days_diff <= 60: return 12000
            else: return 11500
        elif util <= 40.0:
            if days_diff >= 61: return 12000
            elif 31 <= days_diff <= 60: return 12500
            else: return 12000
        elif util <= 50.0:
            if days_diff >= 61: return 12250
            elif 31 <= days_diff <= 60: return 13250
            else: return 12250
        elif util <= 60.0:
            if days_diff >= 61: return 13000
            elif 31 <= days_diff <= 60: return 13750
            else: return 13000
        elif util <= 70.0:
            if days_diff >= 61: return 13750
            elif 31 <= days_diff <= 60: return 14750
            else: return 13750
        elif util <= 80.0:
            if days_diff >= 61: return 14500
            elif 31 <= days_diff <= 60: return 15750
            else: return 16000
        elif util <= 85.0:
            if days_diff >= 61: return 15000
            elif 31 <= days_diff <= 60: return 16250
            else: return 16500
        elif util <= 90.0:
            if days_diff >= 61: return 15750
            elif 31 <= days_diff <= 60: return 17000
            else: return 17500
        else:               # 91% 以上
            if days_diff >= 61: return 17500
            elif 31 <= days_diff <= 60: return 19000
            else: return 19500

    # 【旺季對照表】
    else:
        if util <= 20.0:
            if days_diff >= 61: return 12500
            elif 31 <= days_diff <= 60: return 13000
            else: return 12500
        elif util <= 30.0:
            if days_diff >= 61: return 13000
            elif 31 <= days_diff <= 60: return 13500
            else: return 13000
        elif util <= 40.0:
            if days_diff >= 61: return 13500
            elif 31 <= days_diff <= 60: return 14000
            else: return 13500
        elif util <= 50.0:
            if days_diff >= 61: return 13750
            elif 31 <= days_diff <= 60: return 14500
            else: return 13750
        elif util <= 60.0:
            if days_diff >= 61: return 14000
            elif 31 <= days_diff <= 60: return 14750
            else: return 14000
        elif util <= 70.0:
            if days_diff >= 61: return 14250
            elif 31 <= days_diff <= 60: return 15000
            else: return 14250
        elif util <= 80.0:
            if days_diff >= 61: return 14750
            elif 31 <= days_diff <= 60: return 16000
            else: return 16250
        elif util <= 85.0:
            if days_diff >= 61: return 15250
            elif 31 <= days_diff <= 60: return 16500
            else: return 16750
        elif util <= 90.0:
            if days_diff >= 61: return 16250
            elif 31 <= days_diff <= 60: return 17500
            else: return 18000
        else:               # 91% 以上
            if days_diff >= 61: return 18000
            elif 31 <= days_diff <= 60: return 19500
            else: return 20000

DAYS_IN_MONTH = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}

# --- 2. ① 今天更新日期 ---
st.subheader("① 今天更新日期")
update_date_input = st.text_input("更新日期 (格式如 7/22 或 8/1)", value=f"{date.today().month}/{date.today().day}")

# 解析今天更新日期的「月份」、「日期」與「年份」
current_y = date.today().year
try:
    parts = update_date_input.split("/")
    cur_m = int(parts[0])
    cur_d = int(parts[1])
    base_date = date(current_y, cur_m, cur_d)
except:
    cur_m = date.today().month
    cur_d = date.today().day
    base_date = date(current_y, cur_m, cur_d)

# 動態推算未來 7 個月的月份與對應年份
num_symbols = ["②", "③", "④", "⑤", "⑥", "⑦", "⑧"]
months_to_input = []

for i in range(7):
    m = (cur_m + i - 1) % 12 + 1
    y = current_y if (cur_m + i <= 12) else current_y + 1
    months_to_input.append({"month": m, "year": y, "symbol": num_symbols[i]})

st.write("---")

# --- 3. ②~⑧ 自動推算未來 7 個月稼動率輸入欄位 ---
month_inputs = {}

for item in months_to_input:
    m = item["month"]
    sym = item["symbol"]
    label = f"{sym} {m}月稼動率"
    
    month_inputs[m] = st.text_input(
        label,
        placeholder=f"貼上 {m} 月
