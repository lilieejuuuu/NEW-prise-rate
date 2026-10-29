from datetime import date
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="稼動率料金變動比對系統", layout="centered")

st.title("稼動率料金變動比對系統")

# --- 1. 最新精確淡旺季與天數階梯料金計算邏輯 ---
def calculate_price(month, day, days_diff, util):
    md = (month, day)

    # 旺季: 12/29~1/3、1/9~1/12、3/19~5/23、7/17~8/31、9/18~9/26、10/15~11/30
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
            else: return 11000
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
        else:
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
        else:
            if days_diff >= 61: return 18000
            elif 31 <= days_diff <= 60: return 19500
            else: return 20000

DAYS_IN_MONTH = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}

# --- 2. ① 今天更新日期 ---
st.subheader("① 今天更新日期")
update_date_input = st.text_input("更新日期 (格式如 7/22 或 8/1)", value=f"{date.today().month}/{date.today().day}")

current_y = date.today().year
try:
    parts = update_date_input.split("/")
    cur_m = int(parts[0])
    cur_d = int(parts[1])
    base_date = date(current_y, cur_m, cur_d)
except Exception:
    cur_m = date.today().month
    cur_d = date.today().day
    base_date = date(current_y, cur_m, cur_d)

num_symbols = ["②", "③", "④", "⑤", "⑥", "⑦", "⑧"]
months_to_input = []

for i in range(7):
    m = (cur_m + i - 1) % 12 + 1
    y = current_y if (cur_m + i <= 12) else current_y + 1
    months_to_input.append({"month": m, "year": y, "symbol": num_symbols[i]})

st.write("---")

# --- 3. ②~⑧ 未來 7 個月稼動率輸入欄位 ---
month_inputs = {}
for item in months_to_input:
    m = item["month"]
    sym = item["symbol"]
    label = f"{sym} {m}月稼動率"
    month_inputs[m] = st.text_input(
        label,
        placeholder=f"貼上 {m} 月 1~31 號稼動率 (可只貼想看的部分月份)...",
        key=f"input_{m}"
    )

st.write("---")

# --- 4. A. 昨日數據 (上傳 CSV 檔案) ---
st.subheader("A. 昨日數據")
uploaded_history = st.file_uploader("【上傳 CSV 檔案】", type=["csv"], label_visibility="collapsed")

yesterday_prices = {}
latest_detected_update = ""

if uploaded_history is not None:
    try:
        try:
            y_df = pd.read_csv(uploaded_history, encoding="utf-8-sig")
        except Exception:
            uploaded_history.seek(0)
            y_df = pd.read_csv(uploaded_history)
        
        valid_rows = []
        for idx, row in y_df.iterrows():
            u_date = str(row.get("更新日", row.iloc[0] if len(row) > 0 else "")).strip()
            d_val  = str(row.get("日期", row.iloc[1] if len(row) > 1 else "")).strip()
            p_val  = row.get("區間金額", row.iloc[3] if len(row) > 3 else None)
            
            if d_val and d_val != "nan" and pd.notnull(p_val):
                d_val_clean = d_val.replace("月", "/").replace("日", "")
                if "/" in d_val_clean:
                    p_split = [p for p in d_val_clean.split("/") if p]
                    if len(p_split) == 3:
                        clean_d = f"{int(p_split[1])}/{int(p_split[2])}"
                    elif len(p_split) == 2:
                        clean_d = f"{int(p_split[0])}/{int(p_split[1])}"
                    else:
                        clean_d = d_val_clean
                else:
                    clean_d = d_val_clean
                
                try:
                    valid_rows.append({
                        "更新日": u_date,
                        "目標日期": clean_d,
                        "區間金額": int(float(p_val))
                    })
                except ValueError:
                    continue
        
        if valid_rows:
            v_df = pd.DataFrame(valid_rows)
            latest_detected_update = v_df["更新日"].iloc[-1]
            latest_df = v_df[v_df["更新日"] == latest_detected_update]
            
            for idx, row in latest_df.iterrows():
                yesterday_prices[row["目標日期"]] = row["區間金額"]
                
            st.success(f"✅ 已成功載入歷史紀錄（更新日：{latest_detected_update}），共 {len(yesterday_prices)} 筆！")
        else:
            st.warning("⚠️ 上傳的 CSV 檔中未包含有效的「區間金額」數據。")
            
    except Exception as e:
        st.error(f"昨日 CSV 讀取失敗：{e}")

# --- 5. 運算與 B. 昨日對比有變動日期及金額 ---
today_records = []
changed_results = []

for item in months_to_input:
    m = item["month"]
    y = item["year"]
    text = month_inputs[m].strip()
    if text:
        nums = re.findall(r"\d+\.?\d*", text)
        for idx, num_str in enumerate(nums):
            day = idx + 1
            if day > DAYS_IN_MONTH[m]:
                break

            # 過濾早於今天的日期
            if m == cur_m and day < cur_d:
                continue

            util_val = float(num_str)
            date_key = f"{m}/{day}"

            target_date = date(y, m, day)
            days_diff = (target_date - base_date).days

            price = calculate_price(m, day, days_diff, util_val)

            today_records.append({
                "更新日": update_date_input,
                "日期": date_key,
                "稼動率": util_val,
                "區間金額": price
            })

            if date_key in yesterday_prices:
                old_p = yesterday_prices[date_key]
                if price != old_p:
                    changed_results.append({
                        "日期": date_key,
                        "距今(天)": days_diff,
                        "最新金額": price
                    })

st.write("---")
st.subheader("B. 昨日對比有變動日期及金額")

def color_rows(row):
    days = row["距今(天)"]
    if 0 <= days <= 30:
        return ['background-color: #FFF3CD; color: #856404; font-weight: bold;'] * len(row)
    elif 31 <= days <= 60:
        return ['background-color: #FFE5D0; color: #A73A00; font-weight: bold;'] * len(row)
    else:
        return ['background-color: #D1E7DD; color: #0F5132; font-weight: bold;'] * len(row)

if changed_results:
    res_df = pd.DataFrame(changed_results)
    
    st.markdown("""
    <span style="color: #E6A100; font-weight: bold;">黃色(0-30天)</span> | 
    <span style="color: #D9531E; font-weight: bold;">橘色(31-60天)</span> | 
    <span style="color: #198754; font-weight: bold;">綠色(61天以上)</span>
    """, unsafe_allow_html=True)
    
    styled_df = res_df.style.apply(color_rows, axis=1)
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "日期": st.column_config.TextColumn("日期"),
            "距今(天)": st.column_config.NumberColumn("距今(天)", format="%d 天"),
            "最新金額": st.column_config.NumberColumn("最新金額", format="%d")
        }
    )
else:
    if uploaded_history is not None and len(today_records) > 0:
        st.success("✅ 所有日期料金與昨日相比完全相同，無變動！")
    else:
        st.info("💡 請貼上稼動率數據並上傳昨日 CSV 檔進行比對。")

# --- 6. 匯出今天 CSV 備份 ---
if today_records:
    st.write("---")
    export_df = pd.DataFrame(today_records)
    csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="下載CSV",
        data=csv_bytes,
        file_name=f"料金紀錄_{update_date_input.replace('/', '_')}.csv",
        mime="text/csv",
        type="primary"
    )
