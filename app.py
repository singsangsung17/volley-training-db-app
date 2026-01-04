import os
import sqlite3
from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd
import streamlit as st
import plotly.express as px

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "volley_training.db")
SCHEMA_PATH = os.path.join(APP_DIR, "schema.sql")
SEED_PATH = os.path.join(APP_DIR, "seed_data.sql")

# 修改前：st.set_page_config(page_title="排球訓練知識庫（最小可用版）", ...)
st.set_page_config(page_title="VolleyData | 排球科學化管理系統", layout="wide")
# 統一全域按鈕顏色為綠色
st.markdown("""
<style>
    /* 定義 primary 按鈕的顏色 */
    div.stButton > button[kind="primary"] {
        background-color: #28a745; /* 綠色背景 */
        color: white;             /* 白色文字 */
        border: none;
        border-radius: 5px;       /* 圓角 */
        padding: 0.5rem 1rem;
    }
    
    /* 滑鼠移上去時變深一點的綠色 */
    div.stButton > button[kind="primary"]:hover {
        background-color: #218838;
        color: white;
        border: none;
    }
    
    /* 按鈕點擊時的顏色 */
    div.stButton > button[kind="primary"]:active {
        background-color: #1e7e34;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


def connect():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA foreign_keys = ON;")
    return con

def run_sql_script(con, path: str):
    with open(path, "r", encoding="utf-8") as f:
        con.executescript(f.read())
    con.commit()

def init_db_if_needed():
    fresh = not os.path.exists(DB_PATH)
    con = connect()
    # Always ensure schema exists
    run_sql_script(con, SCHEMA_PATH)
    if fresh:
        # Seed demo data for first run
        run_sql_script(con, SEED_PATH)
    return con

def df(con, query: str, params: Tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(query, con, params=params)

def exec_one(con, query: str, params: Tuple = ()):
    con.execute(query, params)
    con.commit()

con = init_db_if_needed()
def detect_drills_text_col(con) -> str:
    cols = df(con, "PRAGMA table_info(drills);")["name"].tolist()
    if "purpose" in cols:
        return "purpose"
    if "objective" in cols:
        return "objective"
    raise RuntimeError("drills 表缺少 purpose/objective 欄位，請檢查 schema.sql")

DRILLS_TEXT_COL = detect_drills_text_col(con)  # 後續統一用這個欄位名


# 修改前：st.title("排球訓練知識庫（SQLite + Streamlit 最小可用版）")
st.title("排球訓練科學化管理與數據分析系統")
st.caption("用途：把 ERD/SQL 附錄變成真的能用的系統。你可以新增球員/訓練/訓練項目，並記錄成效；右側提供常見統計查詢。")

import traceback

def reset_to_seed():
    try:
        # 1) 刪掉舊 DB 檔（最乾淨，避免殘留）
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        # 2) 重新建表
        con = connect()
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            con.executescript(f.read())

        # 3) 灌入 seed
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            con.executescript(f.read())

        con.commit()
        con.close()
        return True, None
    except Exception as e:
        return False, traceback.format_exc()

# Sidebar reset button
with st.sidebar:
    if st.button("重置為示例資料（會清空現有資料）"):
        ok, err = reset_to_seed()
        if ok:
            st.success("已重置為示例資料。")
            st.rerun()
        else:
            st.error("重置失敗，錯誤如下：")
            st.code(err)


tab1, tab2, tab3, tab4, tab5 = st.tabs(["球員 players", "訓練項目 drills", "訓練場次 sessions", "成效紀錄 drill_results", "分析（SQL）"])

# ---- Tab 1: Players (極簡動態管理：含背號、預設年級、備註與完整儲存邏輯) ----
with tab1:
    st.subheader("🏐 球員名單管理")
    st.caption("使用說明：1. 點擊表格底部「+」新增球員。 2. 雙擊儲存格修改。 3. 選取行後按 Delete 刪除。 4. 修改後務必點擊下方的「儲存名單變更」。")

    # 1. 從資料庫讀取最新名單
    # 確保欄位包含 jersey_number 與 notes
    query = "SELECT player_id, jersey_number, name, grade_year, position, notes FROM players ORDER BY jersey_number ASC"
    players_df = df(con, query)
    
    # 定義年級選項順序
    STANDARD_GRADES = ["一年級", "二年級", "三年級", "四年級", "碩一", "碩二"]

    # 2. 使用 st.data_editor 顯示可編輯表格
    edited_p_df = st.data_editor(
        players_df,
        key="p_manager_final",
        use_container_width=True,
        num_rows="dynamic",  # 允許動態增減行
        hide_index=True,
        column_config={
            "player_id": None, # 【隱藏 ID】
            "jersey_number": st.column_config.NumberColumn(
                "背號", 
                min_value=1, 
                max_value=99, 
                format="%d", 
                width="small",
                required=True
            ),
            "name": st.column_config.TextColumn("姓名", required=True, width="medium"),
            "grade_year": st.column_config.SelectboxColumn(
                "年級", 
                options=STANDARD_GRADES, 
                default="一年級", # 【預設值】新增行時自動帶入
                required=True,
                width="small"
            ),
            "position": st.column_config.SelectboxColumn(
                "位置", 
                options=["主攻", "攔中", "副攻", "舉球", "自由", "未定"],
                width="small"
            ),
            "notes": st.column_config.TextColumn(
                "備註", 
                help="可記錄慣用手、傷病史或訓練重點", # 使用 help 替代 placeholder 避免報錯
                width="large"
            )
        }
    )

    # 3. 完整儲存邏輯 (CRUD 核心)
    if st.button("💾 儲存名單變更", type="primary", use_container_width=True):
        try:
            # A. 處理刪除：找出在原資料中存在，但在編輯後消失的 ID
            original_ids = set(players_df['player_id'].dropna().unique())
            current_ids = set(edited_p_df['player_id'].dropna().unique())
            deleted_ids = original_ids - current_ids
            
            for d_id in deleted_ids:
                exec_one(con, "DELETE FROM players WHERE player_id = ?", (int(d_id),))

            # B. 處理新增與更新
            for _, row in edited_p_df.iterrows():
                # 取得各欄位數值，處理可能的空值
                p_name = row['name'].strip() if row['name'] else ""
                p_num = row['jersey_number']
                p_grade = row['grade_year']
                p_pos = row['position']
                p_notes = row['notes'] if row['notes'] else ""

                if not p_name:
                    continue # 略過姓名空白的行

                if pd.isna(row['player_id']): 
                    # --- Create: 如果沒有 ID，代表是按「+」新增的 ---
                    exec_one(con, """
                        INSERT INTO players (name, jersey_number, position, grade_year, notes) 
                        VALUES (?, ?, ?, ?, ?)
                    """, (p_name, p_num, p_pos, p_grade, p_notes))
                else:
                    # --- Update: 如果有 ID，更新現有資料 ---
                    exec_one(con, """
                        UPDATE players 
                        SET name = ?, jersey_number = ?, position = ?, grade_year = ?, notes = ? 
                        WHERE player_id = ?
                    """, (p_name, p_num, p_pos, p_grade, p_notes, int(row['player_id'])))
            
            st.success("🎉 球員名單已成功同步至資料庫！")
            st.rerun() # 重新整理頁面以顯示最新排序
            
        except Exception as e:
            st.error(f"儲存過程中發生錯誤：{e}")
        
# ---- Tab 2: Drills (中文化介面 + 神經負荷專業版) ----
with tab2:
    st.subheader("🏐 訓練項目庫管理")
    st.caption("點選類別查看教案，表格依人數排序，勾選「隱藏」並點擊儲存可移至鎖頭分頁管理。")

    # 1. 定義類別與建立分頁
    MAIN_CATS = ["綜合訓練", "傳球", "發球", "接球", "攻擊", "攔網", "位置別", "實戰練習"]
    drill_tabs = st.tabs(MAIN_CATS + ["🔒 已隱藏項目"])
    editor_states = {} 

    # 2. 渲染技術分頁
    for i, cat_name in enumerate(MAIN_CATS):
        with drill_tabs[i]:
            # 從資料庫抓取資料 (注意：SQL 欄位名稱維持英文以對應資料庫)
            df_cat = df(con, """
                SELECT drill_id, drill_name, min_players, neuromuscular_load, objective, notes, is_hidden
                FROM drills WHERE category = ? AND is_hidden = 0
                ORDER BY min_players ASC
            """, (cat_name,))
            
            # 【關鍵：中文化配置】透過 column_config 將英文標頭轉為中文
            editor_states[cat_name] = st.data_editor(
                df_cat,
                key=f"editor_final_zh_{cat_name}",
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True,
                column_config={
                    "drill_id": None, # 隱藏 ID 不顯示
                    "drill_name": st.column_config.TextColumn("項目名稱", required=True, width="medium"),
                    "min_players": st.column_config.NumberColumn("人數", format="%d人+", min_value=1, width="small"),
                    "neuromuscular_load": st.column_config.SelectboxColumn(
                        "神經負荷", 
                        help="根據神經肌肉負荷評分 (1:極低 - 5:極高)", 
                        options=[1, 2, 3, 4, 5], 
                        width="small"
                    ),
                    "objective": st.column_config.TextColumn("訓練重點", width="medium"),
                    "notes": st.column_config.TextColumn("備註", width="medium"),
                    "is_hidden": st.column_config.CheckboxColumn("隱藏?", default=False)
                }
            )

    # 3. 渲染隱藏分頁
    with drill_tabs[-1]:
        df_hidden = df(con, """
            SELECT drill_id, drill_name, category, min_players, neuromuscular_load, objective, notes, is_hidden
            FROM drills WHERE is_hidden = 1 ORDER BY min_players ASC
        """)
        editor_states["hidden_items"] = st.data_editor(
            df_hidden,
            key="editor_hidden_zh",
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "drill_id": None,
                "drill_name": st.column_config.TextColumn("項目名稱"),
                "category": st.column_config.SelectboxColumn("原類別", options=MAIN_CATS),
                "min_players": st.column_config.NumberColumn("人數", format="%d人+"),
                "neuromuscular_load": st.column_config.SelectboxColumn("神經負荷", options=[1, 2, 3, 4, 5]),
                "objective": st.column_config.TextColumn("訓練重點"),
                "is_hidden": st.column_config.CheckboxColumn("隱藏?", default=True)
            }
        )

    # 4. 統一儲存按鈕 (與分頁同級，確保縮排正確)
    st.write("") 
    if st.button("💾 儲存所有項目變更", type="primary", use_container_width=True):
        try:
            for cat_key, edited_df in editor_states.items():
                # A. 處理刪除邏輯
                if cat_key == "hidden_items":
                    db_df = df(con, "SELECT drill_id FROM drills WHERE is_hidden = 1")
                else:
                    db_df = df(con, "SELECT drill_id FROM drills WHERE category = ? AND is_hidden = 0", (cat_key,))
                
                original_ids = set(db_df['drill_id'].dropna().unique())
                current_ids = set(edited_df['drill_id'].dropna().unique())
                for d_id in (original_ids - current_ids):
                    exec_one(con, "DELETE FROM drills WHERE drill_id = ?", (int(d_id),))

                # B. 處理新增與更新 (欄位名稱需與資料庫 neuromuscular_load 一致)
                for _, row in edited_df.iterrows():
                    target_cat = row['category'] if cat_key == "hidden_items" else cat_key
                    if pd.isna(row['drill_id']): # 新增
                        exec_one(con, """
                            INSERT INTO drills (drill_name, category, min_players, neuromuscular_load, objective, notes, is_hidden)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (row['drill_name'], target_cat, row['min_players'], row['neuromuscular_load'], row['objective'], row['notes'], row['is_hidden']))
                    else: # 更新
                        exec_one(con, """
                            UPDATE drills SET drill_name=?, category=?, min_players=?, neuromuscular_load=?, objective=?, notes=?, is_hidden=?
                            WHERE drill_id=?
                        """, (row['drill_name'], target_cat, row['min_players'], row['neuromuscular_load'], row['objective'], row['notes'], row['is_hidden'], int(row['drill_id'])))
            
            st.success("🎉 數據已同步！神經負荷評分已更新。")
            st.rerun()
        except Exception as e:
            st.error(f"儲存失敗：{e}")
            
# ---- Tab 3: Sessions (智慧排球訓練中控台) ----
with tab3:
    # 1. 資料庫自動修復邏輯 (解決 image_1ce5c3.png 的欄位缺失問題)
    try:
        existing_cols = [row[1] for row in con.execute("PRAGMA table_info(sessions)").fetchall()]
        if 'phase' not in existing_cols:
            exec_one(con, "ALTER TABLE sessions ADD COLUMN phase TEXT DEFAULT '基礎期'")
        if 'target_duration' not in existing_cols:
            exec_one(con, "ALTER TABLE sessions ADD COLUMN target_duration INTEGER DEFAULT 120")
    except Exception as e:
        st.error(f"資料庫升級錯誤: {e}")

    # 獲取場次資料 (依日期正序 ASC，日期早的在上面)
    sess_df = df(con, "SELECT session_id, session_date, theme, phase, target_duration FROM sessions ORDER BY session_date ASC")

    if sess_df.empty:
        st.warning("⚠️ 目前無場次。請利用最下方的「賽季週期藍圖工具」生成場次。")
    else:
        # --- 第一階段：場次定位與設定 ---
        st.markdown("### 🎯 第一階段：場次定位與設定")
        
        # 【智慧定位】：自動計算並定位至與今天 (2026-01-05) 最接近的場次
        sess_df['date_dt'] = pd.to_datetime(sess_df['session_date'])
        now = pd.Timestamp.now().normalize()
        smart_idx = (sess_df['date_dt'] - now).abs().idxmin() 
        
        s_options = {int(r.session_id): f"📅 {r.session_date} | {r.phase} | {r.theme}" for r in sess_df.itertuples()}
        s_list = list(s_options.keys())
        
        # 渲染選單：日期早的在上面，自動選中最近場次
        current_sid = st.selectbox(
            "選擇目前規劃場次 (依日期正序)", 
            options=s_list, 
            index=int(sess_df.index.get_loc(smart_idx)),
            format_func=lambda x: s_options[x]
        )

        curr_s = sess_df[sess_df['session_id'] == current_sid].iloc[0]
        with st.container(border=True):
            c_th, c_ph, c_tm, c_del = st.columns([2.5, 1, 1, 0.8])
            with c_th:
                u_theme = st.text_input("本場訓練主題", value=curr_s['theme'])
            with c_ph:
                u_phase = st.selectbox("週期相位", ["基礎期", "強化期", "巔峰期", "恢復期"], 
                                      index=["基礎期", "強化期", "巔峰期", "恢復期"].index(curr_s['phase']))
            with c_tm:
                u_dur = st.number_input("預計時長 (min)", value=int(curr_s['target_duration']), step=10)
            with c_del:
                st.write("") # 垂直對齊
                if st.button("🗑️ 刪除", type="secondary", use_container_width=True):
                    exec_one(con, "DELETE FROM sessions WHERE session_id = ?", (current_sid,))
                    st.rerun()
            
            if st.button("💾 儲存場次設定變更", type="primary", use_container_width=True):
                exec_one(con, "UPDATE sessions SET theme=?, phase=?, target_duration=? WHERE session_id=?", (u_theme, u_phase, u_dur, current_sid))
                st.rerun()

        st.divider()

        # --- 第二階段：預計出席與流程編排 ---
        col_l, col_r = st.columns([1, 2.2])

        with col_l:
            st.markdown("#### 👥 1. 預計出席設定")
            players_all = df(con, "SELECT player_id, name FROM players ORDER BY name")
            att_curr = df(con, "SELECT player_id, status FROM attendance WHERE session_id=?", (current_sid,))
            att_map = dict(zip(att_curr['player_id'], att_curr['status']))
            
            with st.container(border=True):
                new_att = {}
                for _, p in players_all.iterrows():
                    new_att[p['player_id']] = st.selectbox(f"{p['name']}", ["出席", "請假", "遲到", "缺席"], 
                                                           index=["出席", "請假", "遲到", "缺席"].index(att_map.get(p['player_id'], "出席")), key=f"att_s3_{p['player_id']}")
                if st.button("💾 更新預計人數", type="primary", use_container_width=True):
                    for pid, stat in new_att.items():
                        exec_one(con, "INSERT OR REPLACE INTO attendance (session_id, player_id, status) VALUES (?,?,?)", (current_sid, pid, stat))
                    st.rerun()
            
            avail_p = sum(1 for v in new_att.values() if v in ["出席", "遲到"])
            st.metric("當前預計可用人數", f"{avail_p} 人")

        with col_r:
            st.markdown("#### 🏐 2. 訓練流程編排")
            drills_lib = df(con, "SELECT drill_id, drill_name, category, min_players, neuromuscular_load FROM drills WHERE is_hidden=0")
            
            c_cat, c_dril = st.columns([1, 2])
            sel_cat = c_cat.selectbox("篩選分類", options=["全部"] + sorted(drills_lib['category'].unique().tolist()))
            f_drills = drills_lib if sel_cat=="全部" else drills_lib[drills_lib['category'] == sel_cat]
            d_opts = {int(r.drill_id): f"{r.drill_name} [{r.min_players}人+][負荷:{r.neuromuscular_load}]" for r in f_drills.itertuples()}
            sel_did = c_dril.selectbox("選擇教案", options=list(d_opts.keys()), format_func=lambda x: d_opts[x])

            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                seq = st.number_input("順序", value=int(con.execute("SELECT COALESCE(MAX(sequence_no),0)+1 FROM session_drills WHERE session_id=?", (current_sid,)).fetchone()[0]))
            with cc2:
                p_min = st.number_input("時間 (min)", value=20, step=5)
            with cc3:
                p_reps = st.text_input("預計量", "50下")

            if st.button("➕ 加入訓練流程", type="primary", use_container_width=True):
                exec_one(con, "INSERT OR REPLACE INTO session_drills (session_id, drill_id, sequence_no, planned_minutes, planned_reps) VALUES (?,?,?,?,?)", (current_sid, sel_did, seq, p_min, p_reps))
                st.rerun()

            st.divider()
            
            # 流程預覽與生理監控
            flow = df(con, "SELECT sd.sequence_no as 順序, d.drill_name as 內容, sd.planned_reps as 預計量, d.neuromuscular_load as 負荷, sd.planned_minutes as 分鐘, d.min_players as 需人數 FROM session_drills sd JOIN drills d ON d.drill_id=sd.drill_id WHERE sd.session_id=? ORDER BY sd.sequence_no", (current_sid,))

            if not flow.empty:
                # 時長進度條
                total_min = flow['分鐘'].sum()
                st.write(f"⏱️ **規劃時長進度：{total_min} / {u_dur} min**")
                st.progress(min(total_min / u_dur, 1.0))

                k1, k2, k3 = st.columns(3)
                k1.metric("平均強度", f"{flow['負荷'].mean():.1f}")
                # 神經肌肉衝量 (Load)
                total_load = (flow['分鐘'] * flow['負荷']).sum()
                k2.metric("總神經衝量 (Load)", f"{total_load}", help="Load = Intensity x Time")
                k3.metric("最高人數需求", f"{flow['需人數'].max()}人")

                ed_flow = st.data_editor(flow, use_container_width=True, hide_index=True, num_rows="dynamic", key=f"ed_s3_{current_sid}",
                                         column_config={"內容": st.column_config.TextColumn(disabled=True), "負荷": st.column_config.NumberColumn(disabled=True)})

                if st.button("💾 儲存流程編輯結果", type="primary", use_container_width=True):
                    exec_one(con, "DELETE FROM session_drills WHERE session_id=?", (current_sid,))
                    for _, r in ed_flow.iterrows():
                        did = con.execute("SELECT drill_id FROM drills WHERE drill_name=?", (r['內容'],)).fetchone()[0]
                        exec_one(con, "INSERT INTO session_drills (session_id, drill_id, sequence_no, planned_minutes, planned_reps) VALUES (?,?,?,?,?)", (current_sid, did, r['順序'], r['分鐘'], r['預計量']))
                    st.rerun()
                if avail_p < flow['需人數'].max(): st.error("⚠️ 警告：目前可用人數不足！")

    # --- 第三階段：賽季週期藍圖工具 (移至底部) ---
    st.divider()
    with st.expander("📅 第三階段：賽季週期藍圖 (批量生成訓練場次)"):
        bc1, bc2, bc3 = st.columns([1, 1, 1])
        with bc1:
            b_s = st.date_input("開始日期", key="batch_s_final")
            b_e = st.date_input("結束日期", key="batch_e_final")
        with bc2:
            b_d = st.multiselect("練球日", ["週一", "週二", "週三", "週四", "週五", "週六", "週日"], default=["週一", "週三", "週五"])
        with bc3:
            b_p = st.selectbox("賽季相位", ["基礎期", "強化期", "巔峰期", "恢復期"], key="batch_p_final")
        
        if st.button("🚀 確認安排週期場次", type="primary", use_container_width=True):
            from datetime import timedelta
            day_map = {"週一":0, "週二":1, "週三":2, "週四":3, "週五":4, "週六":5, "週日":6}
            target_days = [day_map[d] for d in b_d]
            curr, count = b_s, 0
            while curr <= b_e:
                if curr.weekday() in target_days:
                    exec_one(con, "INSERT INTO sessions (session_date, theme, phase, target_duration) VALUES (?, ?, ?, ?)", (str(curr), "常規訓練", b_p, 120))
                    count += 1
                curr += timedelta(days=1)
            st.success(f"已安排 {count} 場次！")
            st.rerun()
        
# ---- Tab 4: Drill Results (正式點名、智慧定位與成效紀錄) ----
with tab4:
    st.info("📊 **數據紀錄流程**：1. 確認正式點名 → 2. 選擇訓練項目 → 3. 輸入數據並檢核成功率")

    # 獲取場次資料 (依日期正序 ASC)
    sess_df = df(con, "SELECT session_id, session_date, theme, phase FROM sessions ORDER BY session_date ASC")
    
    if sess_df.empty:
        st.warning("⚠️ 目前無場次資料，請先至 Tab 3 安排訓練。")
    else:
        # --- 第一階段：場次選取 (智慧定位) ---
        sess_df['date_dt'] = pd.to_datetime(sess_df['session_date'])
        now = pd.Timestamp.now().normalize()
        smart_idx = (sess_df['date_dt'] - now).abs().idxmin()
        
        s_options = {int(r.session_id): f"📅 {r.session_date} | {r.theme}" for r in sess_df.itertuples()}
        s_list = list(s_options.keys())
        
        sid = st.selectbox(
            "🎯 選擇紀錄場次 (依日期正序，已智慧定位最近日期)", 
            options=s_list, 
            index=int(sess_df.index.get_loc(smart_idx)),
            format_func=lambda x: s_options[x], 
            key="tab4_sid_final"
        )

        st.divider()

        # --- 第二階段：正式出缺席確認 (摺疊選單) ---
        with st.expander("📝 正式出缺席確認 (請先確認點名狀態)", expanded=False):
            st.caption("在此確認球員的最終出席狀態，這將自動過濾下方的紀錄名單。")
            players_all = df(con, "SELECT player_id, name, jersey_number FROM players ORDER BY name")
            curr_att = df(con, "SELECT player_id, status FROM attendance WHERE session_id=?", (sid,))
            att_map = dict(zip(curr_att['player_id'], curr_att['status']))
            
            att_cols = st.columns(2)
            new_final_status = {}
            for idx, p in players_all.iterrows():
                with att_cols[idx % 2]:
                    c_val = att_map.get(p['player_id'], "出席")
                    new_final_status[p['player_id']] = st.selectbox(
                        f"{p['name']} (#{p['jersey_number']})", 
                        ["出席", "請假", "遲到", "缺席"], 
                        index=["出席", "請假", "遲到", "缺席"].index(c_val), 
                        key=f"f_att_s4_{p['player_id']}_{sid}"
                    )
            
            if st.button("💾 更新本日正式出缺席狀態", type="primary", use_container_width=True):
                for pid, stat in new_final_status.items():
                    exec_one(con, "INSERT OR REPLACE INTO attendance (session_id, player_id, status) VALUES (?,?,?)", (sid, pid, stat))
                st.success("點名狀態已更新！")
                st.rerun()

        st.divider()

        # --- 第三階段：項目成效紀錄 ---
        planned_drills = df(con, "SELECT d.drill_id, d.drill_name FROM session_drills sd JOIN drills d ON d.drill_id = sd.drill_id WHERE sd.session_id = ? ORDER BY sd.sequence_no", (sid,))

        if planned_drills.empty:
            st.info("此場次尚未安排訓練項目。")
        else:
            sel_did = st.selectbox("選擇要紀錄的訓練項目", options=planned_drills['drill_id'].tolist(),
                                   format_func=lambda x: planned_drills[planned_drills['drill_id']==x]['drill_name'].values[0])

            # 僅紀錄「出席」或「遲到」的人員
            present_p_list = [pid for pid, stat in new_final_status.items() if stat in ["出席", "遲到"]]
            
            if not present_p_list:
                st.error("此場次無人出席，無法錄入數據。")
            else:
                exist_res = df(con, "SELECT player_id, success_count, total_count, error_type, notes FROM drill_results WHERE session_id=? AND drill_id=?", (sid, sel_did))
                final_players = players_all[players_all['player_id'].isin(present_p_list)]
                record_df = final_players.merge(exist_res, on='player_id', how='left')
                
                # 初始化數據
                record_df['success_count'] = record_df['success_count'].fillna(0).astype(int)
                record_df['total_count'] = record_df['total_count'].fillna(0).astype(int)
                record_df['error_type'] = record_df['error_type'].fillna("無")
                record_df['notes'] = record_df['notes'].fillna("")
                
                # 計算成功率展示
                record_df['成功率%'] = (record_df['success_count'] / record_df['total_count'] * 100).fillna(0).round(1)

                st.write(f"錄入對象：**{planned_drills[planned_drills['drill_id']==sel_did]['drill_name'].values[0]}**")
                
                # 數據編輯表格
                edited_res = st.data_editor(
                    record_df[['player_id', 'name', 'success_count', 'total_count', '成功率%', 'error_type', 'notes']],
                    use_container_width=True, hide_index=True, key=f"res_s4_{sid}_{sel_did}",
                    column_config={
                        "player_id": None,
                        "name": st.column_config.TextColumn("球員", disabled=True),
                        "success_count": st.column_config.NumberColumn("成功次數", min_value=0),
                        "total_count": st.column_config.NumberColumn("總次數", min_value=0),
                        "成功率%": st.column_config.ProgressColumn("成功率視覺化", format="%f%%", min_value=0, max_value=100),
                        "error_type": st.column_config.SelectboxColumn("失誤原因", options=["無", "腳步", "擊球點", "力道", "判斷", "反應慢"]),
                        "notes": st.column_config.TextColumn("備註")
                    }
                )

                # 儲存與數據檢核 (總數 >= 成功數)
                if st.button("💾 儲存本項訓練成效", type="primary", use_container_width=True):
                    errors = []
                    for _, row in edited_res.iterrows():
                        if int(row['success_count']) > int(row['total_count']):
                            errors.append(row['name'])
                    
                    if errors:
                        st.error(f"❌ 錯誤：球員 {', '.join(errors)} 的成功次數大於總次數！請修正。")
                    else:
                        for _, row in edited_res.iterrows():
                            exec_one(con, """
                                INSERT OR REPLACE INTO drill_results (session_id, drill_id, player_id, success_count, total_count, error_type, notes)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (sid, sel_did, int(row['player_id']), int(row['success_count']), int(row['total_count']), row['error_type'], row['notes']))
                        st.success("🎉 數據已同步儲存！")
                        st.rerun()
                

# ---- Tab 5: Analytics (終極戰情室：個人趨勢 + 全隊分析) ----
with tab5:
    st.subheader("排球戰略分析儀表板")
    
    # 0. 基礎中文映射字典 (處理資料庫與介面顯示)
    CAT_MAP = {
        "attack": "攻擊", "defense": "防守", "serve": "發球", 
        "set": "舉球", "receive": "接發", "block": "攔網",
        "attack_chain": "攻擊鏈", "serve_receive": "接發球",
        "receive": "接發", "set": "舉球",
        "綜合": "綜合", "攻擊": "攻擊", "接發": "接發", "防守": "防守", "發球": "發球", "舉球": "舉球", "攔網": "攔網", "接球": "接球", "傳球": "傳球"
    }

    # 1. 頂層：全隊關鍵績效指標 (KPI Cards)
    total_stats = df(con, "SELECT SUM(success_count) as s, SUM(total_count) as t FROM drill_results;")
    if not total_stats.empty and total_stats['t'].iloc[0] > 0:
        k1, k2, k3 = st.columns(3)
        total_s, total_t = total_stats['s'].iloc[0], total_stats['t'].iloc[0]
        avg_rate = (total_s / total_t * 100).round(1)
        k1.metric("全隊總平均成功率", f"{avg_rate}%")
        k2.metric("累計訓練總擊球數", f"{int(total_t)} 顆")
        top_err = df(con, "SELECT error_type, COUNT(*) as c FROM drill_results WHERE error_type != '無' GROUP BY error_type ORDER BY c DESC LIMIT 1;")
        if not top_err.empty:
            k3.metric("首要優化環節", top_err['error_type'].iloc[0])
    
    st.divider()

    # 2. 中層：【個人深度分析】 (雷達圖 + 成長曲線)
    st.markdown("### 👤 個人表現深度追蹤")
    p_list = df(con, "SELECT player_id, name FROM players ORDER BY name;")
    
    if not p_list.empty:
        # 在個人區上方放置篩選器
        sel_c1, sel_c2 = st.columns(2)
        with sel_c1:
            sel_p = st.selectbox("分析球員", options=p_list['player_id'], format_func=lambda x: p_list[p_list['player_id']==x]['name'].values[0], key="deep_p")
        with sel_c2:
            sel_cat = st.selectbox("技術類別", options=["攻擊", "接發", "防守", "發球", "舉球", "攔網", "接球", "傳球"], key="deep_cat")

        col_radar, col_trend = st.columns([1, 1.2])
        
        with col_radar:
            # 雷達圖邏輯
            radar_raw = df(con, "SELECT d.category, CAST(SUM(r.success_count) AS FLOAT)/SUM(r.total_count)*100 as rate FROM drill_results r JOIN drills d ON d.drill_id = r.drill_id WHERE r.player_id = ? AND d.category != 'summary' GROUP BY d.category", (int(sel_p),))
            if not radar_raw.empty:
                radar_raw['技術項目'] = radar_raw['category'].apply(lambda x: CAT_MAP.get(x, x))
                fig_radar = px.line_polar(radar_raw, r='rate', theta='技術項目', line_close=True)
                fig_radar.update_traces(fill='toself', line_color='#28a745') 
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, height=350)
                st.plotly_chart(fig_radar, use_container_width=True)
            else:
                st.info("尚無數據產生雷達圖")

        with col_trend:
            # 成長曲線邏輯
            trend_df = df(con, """
                SELECT strftime('%m/%d', s.session_date) AS 日期,
                       SUM(r.success_count) AS s, SUM(r.total_count) AS t
                FROM drill_results r JOIN sessions s ON s.session_id = r.session_id
                JOIN drills d ON d.drill_id = r.drill_id
                WHERE r.player_id = ? AND (d.category = ? OR d.drill_name LIKE '%' || ? || '%')
                GROUP BY 日期 ORDER BY s.session_date ASC
            """, (int(sel_p), sel_cat, sel_cat))
            
            if not trend_df.empty:
                trend_df['成功率'] = (trend_df['s'] / trend_df['t'] * 100).round(1)
                fig_line = px.line(trend_df, x='日期', y='成功率', markers=True, title=f"{sel_cat} 歷史成長走勢")
                fig_line.update_layout(yaxis_range=[0, 105], height=350)
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("尚無該項目的歷史數據")

    st.divider()

    # 3. 下層：【全隊戰略分析】 (訓練比例 + 短板監控 + 失誤佔比)
    st.markdown("### 🏐 全隊戰略監控")
    col_prop, col_bar, col_pie = st.columns([1, 1.2, 1])
    
    with col_prop:
        st.markdown("#### 訓練項目佔比")
        prop_data = df(con, "SELECT d.category, COUNT(*) as count FROM drill_results r JOIN drills d ON d.drill_id = r.drill_id WHERE d.category != 'summary' GROUP BY d.category")
        if not prop_data.empty:
            prop_data['類別'] = prop_data['category'].apply(lambda x: CAT_MAP.get(x, x))
            fig_prop = px.pie(prop_data, values='count', names='類別', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_prop.update_layout(showlegend=True, height=350, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_prop, use_container_width=True)
        
    with col_bar:
        st.markdown("#### 技術短板監控")
        team_stats = df(con, "SELECT d.category as cat, CAST(SUM(r.success_count) AS FLOAT)/SUM(r.total_count)*100 as rate FROM drill_results r JOIN drills d ON d.drill_id = r.drill_id WHERE d.category != 'summary' AND r.total_count > 0 GROUP BY d.category")
        if not team_stats.empty:
            team_stats['類別'] = team_stats['cat'].apply(lambda x: CAT_MAP.get(x, x))
            team_stats['成功率'] = team_stats['rate'].round(1)
            fig_bar = px.bar(team_stats.sort_values('成功率'), x="成功率", y="類別", orientation='h', text="成功率",
                             color="成功率", color_continuous_scale='Blues', range_x=[0, 110], range_color=[0, 100])
            fig_bar.update_layout(showlegend=False, coloraxis_showscale=False, height=350, xaxis_title="", yaxis_title="")
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_pie:
        st.markdown("#### 失誤主因分析")
        pie_data = df(con, "SELECT error_type, COUNT(*) as count FROM drill_results WHERE error_type != '無' GROUP BY error_type")
        if not pie_data.empty:
            fig_pie = px.pie(pie_data, values='count', names='error_type', hole=0.3, color_discrete_sequence=px.colors.sequential.Blues_r)
            fig_pie.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)
