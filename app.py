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
            
# ---- Tab 3: Sessions (顯示優化：名稱優先 + 生理監控版) ----
with tab3:
    st.subheader("📅 訓練場次規劃與生理監控")

    # --- A. 週期化訓練規劃 (全寬度佈局) ---
    with st.expander("⚙️ 週期化訓練規劃：自動生成場次", expanded=False):
        st.write("根據球隊固定練習時間，快速生成賽季訓練場次。")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            start_date = st.date_input("開始日期", key="s_start_v6")
            end_date = st.date_input("結束日期", key="s_end_v6")
        with c2:
            days_options = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
            fixed_days = st.multiselect("固定訓練日", days_options, default=["週一", "週三", "週五"])
        with c3:
            season_phase = st.selectbox("賽季相位", ["基礎期", "強化期", "巔峰期", "恢復期"])
        
        if st.button("🚀 生成週期訓練場次", type="primary", use_container_width=True):
            day_map = {d: i for i, d in enumerate(days_options)}
            target_days = [day_map[d] for d in fixed_days]
            from datetime import timedelta
            curr, count = start_date, 0
            while curr <= end_date:
                if curr.weekday() in target_days:
                    exec_one(con, "INSERT INTO sessions (session_date, theme, phase) VALUES (?, ?, ?)", 
                             (str(curr), "常規技術訓練", season_phase))
                    count += 1
                curr += timedelta(days=1)
            st.success(f"已成功為「{season_phase}」安排 {count} 場訓練場次！")
            st.rerun()

    st.divider()

    # 獲取基礎資料
    sessions_df = df(con, "SELECT session_id, session_date, theme, phase FROM sessions ORDER BY session_date DESC")
    
    if sessions_df.empty:
        st.warning("目前尚未安排場次，請使用上方工具新增。")
    else:
        # --- B. 選擇場次與預計點名 ---
        s_options = {int(r.session_id): f"{r.session_date} | {r.phase} | {r.theme}" for r in sessions_df.itertuples()}
        sid = st.selectbox("🎯 選擇目前規劃場次", options=list(s_options.keys()), format_func=lambda x: s_options[x])
        
        col_att, col_plan = st.columns([1, 2.2])
        
        with col_att:
            st.markdown("#### 1. 預計出席設定")
            all_players = df(con, "SELECT player_id, name FROM players ORDER BY name")
            curr_att = df(con, "SELECT player_id, status FROM attendance WHERE session_id=?", (sid,))
            att_map = dict(zip(curr_att['player_id'], curr_att['status']))
            
            with st.container(border=True):
                new_status = {}
                for _, p in all_players.iterrows():
                    c_val = att_map.get(p['player_id'], "出席")
                    new_status[p['player_id']] = st.selectbox(f"{p['name']}", ["出席", "請假", "遲到", "缺席"], 
                                                              index=["出席", "請假", "遲到", "缺席"].index(c_val), key=f"att_v6_{p['player_id']}")
                
                if st.button("💾 更新預計出席狀態", type="primary", use_container_width=True):
                    for pid, stat in new_status.items():
                        exec_one(con, "INSERT OR REPLACE INTO attendance (session_id, player_id, status) VALUES (?,?,?)", (sid, pid, stat))
                    st.rerun()

            available_count = sum(1 for v in new_status.values() if v in ["出席", "遲到"])
            st.metric("當前預計可用人數", f"{available_count} 人")

        with col_plan:
            st.markdown("#### 2. 訓練流程編排")
            
            drills_master = df(con, "SELECT drill_id, drill_name, category, min_players, neuromuscular_load FROM drills WHERE is_hidden = 0")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                all_cats = sorted(drills_master['category'].unique().tolist())
                sel_cat = st.selectbox("篩選技術類別", options=["全部"] + all_cats)
            with c2:
                filtered_drills = drills_master if sel_cat == "全部" else drills_master[drills_master['category'] == sel_cat]
                # 【修改重點】：調整 f-string 順序，將名稱放在最前面
                d_opts = {int(r.drill_id): f"{r.drill_name} [{r.min_players}人+][負荷:{r.neuromuscular_load}]" for r in filtered_drills.itertuples()}
                sel_did = st.selectbox("選擇訓練項目", options=list(d_opts.keys()), format_func=lambda x: d_opts[x])

            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                next_seq = con.execute("SELECT COALESCE(MAX(sequence_no), 0) + 1 FROM session_drills WHERE session_id=?", (sid,)).fetchone()[0]
                seq = st.number_input("順序", value=int(next_seq), min_value=1)
            with cc2:
                p_min = st.number_input("時間 (min)", value=20, step=5)
            with cc3:
                p_reps = st.text_input("預計量 (如: 3組)", "50下")

            if st.button("➕ 加入訓練流程", type="primary", use_container_width=True):
                exec_one(con, "INSERT OR REPLACE INTO session_drills (session_id, drill_id, sequence_no, planned_minutes, planned_reps) VALUES (?,?,?,?,?)",
                         (sid, sel_did, seq, p_min, p_reps))
                st.rerun()

            st.divider()
            flow_df = df(con, """
                SELECT sd.sequence_no AS 順序, d.drill_name AS 內容, sd.planned_reps AS 預計量,
                       d.neuromuscular_load AS 負荷, sd.planned_minutes AS 分鐘, d.min_players AS 需人數
                FROM session_drills sd JOIN drills d ON d.drill_id = sd.drill_id
                WHERE sd.session_id = ? ORDER BY sd.sequence_no ASC
            """, (sid,))

            if not flow_df.empty:
                # 生理負荷計算
                total_load = (flow_df['分鐘'] * flow_df['負荷']).sum()
                avg_nm_load = flow_df['負荷'].mean()
                
                k1, k2, k3 = st.columns(3)
                k1.metric("總練習時長", f"{flow_df['分鐘'].sum()} min")
                k2.metric("平均神經強度", f"{avg_nm_load:.1f}")
                k3.metric(
                    "神經肌肉衝量 (Load)", 
                    f"{total_load}", 
                    help="神經肌肉衝量反映中樞神經系統在此場次承受的壓力總合。"
                )

                st.write("📋 流程清單 (點選行首並按 Delete 可移除項目)")
                edited_flow = st.data_editor(
                    flow_df,
                    key=f"flow_editor_v6_{sid}",
                    use_container_width=True,
                    num_rows="dynamic",
                    hide_index=True,
                    column_config={
                        "內容": st.column_config.TextColumn(disabled=True),
                        "負荷": st.column_config.NumberColumn(disabled=True),
                        "需人數": st.column_config.NumberColumn(disabled=True)
                    }
                )

                if st.button("💾 儲存訓練流程變更", type="primary", use_container_width=True):
                    exec_one(con, "DELETE FROM session_drills WHERE session_id = ?", (sid,))
                    for _, row in edited_flow.iterrows():
                        d_id = con.execute("SELECT drill_id FROM drills WHERE drill_name = ?", (row['內容'],)).fetchone()[0]
                        exec_one(con, """
                            INSERT INTO session_drills (session_id, drill_id, sequence_no, planned_minutes, planned_reps)
                            VALUES (?, ?, ?, ?, ?)
                        """, (sid, int(d_id), int(row['順序']), int(row['分鐘']), row['預計量']))
                    st.success("訓練流程已同步儲存！")
                    st.rerun()

                if available_count < flow_df['需人數'].max():
                    st.error(f"⚠️ 警報：今日預計出席人數 ({available_count}人) 低於教案需求！")
            else:
                st.info("目前尚未安排任何訓練項目。")
        
# ---- Tab 4: Results (終極巨型按鈕 + 確保過濾總結) ----
with tab4:
    # 這是關鍵的「黑科技」CSS，我把高度加到 350px，字體 80px，這絕對會超級大
    st.markdown("""
        <style>
            /* 1. 超級巨型計數按鈕：使用 min-height 強制拉高 */
            .super-huge-btn div[data-testid="stButton"] button {
                min-height: 350px !important; 
                font-size: 80px !important;
                font-weight: 900 !important;
                border-radius: 30px !important;
                width: 100% !important;
            }
            
            /* 2. 縮小清空按鈕：維持原本的小巧 */
            .small-clear-btn div[data-testid="stButton"] button {
                min-height: 40px !important;
                font-size: 14px !important;
                width: 150px !important;
                background-color: transparent !important;
                color: #888 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.subheader("現場數據紀錄")

    # 解決之前的 NameError，重新抓取資料
    t4_sessions = df(con, "SELECT session_id, session_date, theme FROM sessions ORDER BY session_date DESC;")
    t4_players = df(con, "SELECT player_id, name FROM players ORDER BY name;")

    if 'count_success' not in st.session_state: st.session_state.count_success = 0
    if 'count_total' not in st.session_state: st.session_state.count_total = 0

    if t4_sessions.empty or t4_players.empty:
        st.info("請先確認已建立場次與球員資料。")
    else:
        # --- 選擇區 ---
        c1, c2, c3 = st.columns(3)
        with c1:
            s_map = {int(r.session_id): f"{r.session_date} | {r.theme}" for r in t4_sessions.itertuples(index=False)}
            sid = st.selectbox("選擇場次", options=list(s_map.keys()), format_func=lambda x: s_map[x], key="t4_sid")
        with c2:
            p_map = {int(r.player_id): r.name for r in t4_players.itertuples(index=False)}
            pid = st.selectbox("選擇球員", options=list(p_map.keys()), format_func=lambda x: p_map[x], key="t4_pid")
        with c3:
            # 【徹底過濾】：在 SQL 查詢時就直接排除「本場次總結」與「summary」類別
            current_drills = df(con, """
                SELECT d.drill_id, d.drill_name FROM session_drills sd 
                JOIN drills d ON d.drill_id = sd.drill_id 
                WHERE sd.session_id = ? AND d.category != 'summary' AND d.drill_name != '本場次總結'
            """, (int(sid),))
            d_options = {int(r.drill_id): r.drill_name for r in current_drills.itertuples(index=False)}
            
            if not d_options:
                st.warning("此場次尚未安排具體訓練項目。")
                did = None
            else:
                did = st.selectbox("訓練項目", options=list(d_options.keys()), format_func=lambda x: d_options[x], key="t4_did")

        st.divider()

        # --- 核心：超級巨型按鈕 ---
        if did:
            st.markdown("#### 即時計數")
            
            # 使用 CSS 類別包覆
            st.markdown('<div class="super-huge-btn">', unsafe_allow_html=True)
            click_l, click_r = st.columns(2)
            with click_l:
                if st.button("成功", use_container_width=True, type="primary"):
                    st.session_state.count_success += 1
                    st.session_state.count_total += 1
                    st.rerun()
            with click_r:
                if st.button("失誤", use_container_width=True):
                    st.session_state.count_total += 1
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            # --- 原版成功率 (st.metric) ---
            curr_total = st.session_state.count_total
            curr_rate = (st.session_state.count_success / curr_total) if curr_total > 0 else 0
            
            st.write("") 
            st.metric(
                label="目前累計表現", 
                value=f"{st.session_state.count_success} / {curr_total}", 
                delta=f"成功率 {curr_rate:.1%}"
            )

            # --- 清空按鈕 (縮小) ---
            st.markdown('<div class="small-clear-btn">', unsafe_allow_html=True)
            if st.button("清空暫時計數", key="reset_click"):
                st.session_state.count_success = 0
                st.session_state.count_total = 0
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            st.divider()

            # --- 正式存檔區 (維持正常大小) ---
            with st.form("t4_final_save_form"):
                st.markdown("#### 確認數據並存檔")
                f1, f2 = st.columns(2)
                with f1:
                    final_s = st.number_input("確認成功數", value=st.session_state.count_success)
                with f2:
                    final_t = st.number_input("確認總次數", value=st.session_state.count_total)
                
                issue = st.selectbox("主要問題", ["無", "腳步不到位", "擊球點錯誤", "觀察判斷遲緩", "溝通喊聲不足"])
                notes = st.text_area("備註", height=80)

                if st.form_submit_button("正式存入資料庫", type="primary", use_container_width=True):
                    exec_one(con, """
                        INSERT INTO drill_results (session_id, drill_id, player_id, success_count, total_count, error_type, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                    """, (int(sid), int(did), int(pid), int(final_s), int(final_t), issue, notes))
                    
                    st.session_state.count_success = 0
                    st.session_state.count_total = 0
                    st.success("數據已成功錄入")
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
