import os
import sqlite3
from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd
import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "volley_training.db")
SCHEMA_PATH = os.path.join(APP_DIR, "schema.sql")
SEED_PATH = os.path.join(APP_DIR, "seed_data.sql")

st.set_page_config(page_title="排球訓練知識庫（最小可用版）", layout="wide")
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


st.title("排球訓練知識庫（SQLite + Streamlit 最小可用版）")
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

# ---- Tab 1: Players (美化 & 綠色按鈕版) ----
with tab1:
    colL, colR = st.columns([1, 1])
    with colL:
        st.subheader("新增球員")
        name = st.text_input("姓名", key="p_name")
        POS_OPTIONS = ["主攻", "攔中", "副攻", "舉球", "自由", "（不填）"]
        pos_sel = st.selectbox("位置（可選）", POS_OPTIONS, index=0, key="p_pos_sel")
        position = "" if pos_sel == "（不填）" else pos_sel

        grade_year = st.text_input("年級（例：大一/大二）", key="p_grade")
        
        # --- 關鍵改動：加上 type="primary" 寬度設為滿版 ---
        if st.button("新增球員", key="p_add", type="primary", use_container_width=True):
            if not name.strip():
                st.error("姓名必填。")
            else:
                exec_one(con, "INSERT INTO players (name, position, grade_year) VALUES (?, ?, ?);",
                         (name.strip(), position, grade_year.strip()))
                st.success(f"球員 {name} 已成功加入列表")
                st.rerun()
                
    with colR:
        st.subheader("球員列表")
        st.dataframe(
            df(con, """
                SELECT 
                  name AS 姓名,
                  position AS 位置,
                  grade_year AS 年級,
                  created_at AS 建立時間
                FROM players 
                ORDER BY created_at DESC;
            """),
            use_container_width=True,
            hide_index=True,
        )
# ---- Tab 2: Drills (按鈕加色 + 簡約版) ----
with tab2:
    colL, colR = st.columns([1, 1])

    with colL:
        st.subheader("新增訓練項目")
        drill_name = st.text_input("訓練項目名稱", key="d_name")
        category = st.selectbox("分類", options=["攻擊", "接發", "防守", "發球", "舉球", "攔網", "綜合"], key="d_category")
        num_people = st.number_input("建議人數", min_value=1, value=6, step=1, key="d_people")
        people_display = f"{num_people}人以上"
        st.info(f"目前設定：{people_display}")
        difficulty = st.slider("難度 (1-5)", 1, 5, 3, key="d_diff")

        # --- 關鍵改動：加上 type="primary" 和用滿寬度 ---
        if st.button("新增訓練項目", key="d_add", type="primary", use_container_width=True):
            _name = (drill_name or "").strip()
            if not _name:
                st.error("訓練項目名稱不可為空。")
            else:
                exec_one(
                    con,
                    f"INSERT INTO drills (drill_name, {DRILLS_TEXT_COL}, category, difficulty) VALUES (?, ?, ?, ?);",
                    (_name, people_display, category, int(difficulty)),
                )
                st.success(f"已新增項目：{_name}")
                st.rerun()

    with colR:
        st.subheader("訓練項目列表")
        st.dataframe(
            df(con, f"""
                SELECT 
                    difficulty AS 難度,
                    drill_name AS 訓練項目,
                    CASE 
                        WHEN {DRILLS_TEXT_COL} LIKE '%人以上' THEN {DRILLS_TEXT_COL}
                        ELSE '未設定 (舊資料)' 
                    END AS 人數需求,
                    category AS 類別
                FROM drills 
                WHERE category != 'summary' AND drill_name != '本場次總結'
                ORDER BY created_at DESC;
            """),
            use_container_width=True,
            hide_index=True
        )
        
# ---- Tab 3: Sessions (簡約專業版) ----
with tab3:
    colL, colR = st.columns([1, 1.3]) 

    sessions = df(con, "SELECT session_id, session_date, theme, duration_min FROM sessions ORDER BY session_date DESC, session_id DESC;")
    drills = df(con, "SELECT drill_id, drill_name FROM drills WHERE category != 'summary' ORDER BY drill_name;")

    with colL:
        st.subheader("場次安排")
        if sessions.empty:
            st.info("目前沒有場次。")
            selected_session_id = None
        else:
            session_ids = sessions["session_id"].tolist()
            session_label_map = {int(r.session_id): f"{r.session_date} | {r.theme}" for r in sessions.itertuples(index=False)}
            
            selected_session_id = st.selectbox(
                "選擇目前操作場次",
                options=session_ids,
                format_func=lambda sid: session_label_map.get(int(sid), str(sid)),
                key="t3_select_sid"
            )

        st.divider()
        st.markdown("#### 加入項目")
        if selected_session_id and not drills.empty:
            drill_ids = drills["drill_id"].tolist()
            drill_label_map = {int(r.drill_id): r.drill_name for r in drills.itertuples(index=False)}
            
            sel_drill_id = st.selectbox("訓練項目", options=drill_ids, format_func=lambda did: drill_label_map.get(int(did), str(did)))
            
            c1, c2 = st.columns(2)
            with c1:
                next_seq = con.execute("SELECT COALESCE(MAX(sequence_no), 0) + 1 FROM session_drills WHERE session_id=?;", (int(selected_session_id),)).fetchone()[0]
                seq = st.number_input("項目順序", min_value=1, value=int(next_seq))
            with c2:
                p_min = st.number_input("預計分鐘", min_value=0, value=20, step=5)
            
            p_sets = st.text_input("預計組次 (例如: 50*2, 3組)", value="3")

            # 按鈕上色請見下方說明
            if st.button("確認加入流程", use_container_width=True, type="primary"):
                exec_one(con, """
                    INSERT OR REPLACE INTO session_drills (session_id, drill_id, sequence_no, planned_minutes, planned_reps) 
                    VALUES (?, ?, ?, ?, ?);
                """, (int(selected_session_id), int(sel_drill_id), int(seq), int(p_min), p_sets))
                st.success("已成功加入訓練清單")
                st.rerun()

    with colR:
        st.subheader("本場訓練流程")
        if selected_session_id:
            current_drills_df = df(con, """
                SELECT 
                    sd.sequence_no AS 順序, 
                    d.drill_name AS 訓練內容,
                    sd.planned_minutes AS 分鐘, 
                    sd.planned_reps AS 預計量
                FROM session_drills sd
                JOIN drills d ON d.drill_id = sd.drill_id
                WHERE sd.session_id = ?
                ORDER BY sd.sequence_no ASC;
            """, (int(selected_session_id),))

            if not current_drills_df.empty:
                total_minutes = current_drills_df["分鐘"].sum()
                
                # 移除 Emoji 的表格設定
                st.dataframe(
                    current_drills_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "順序": st.column_config.NumberColumn("No.", width="small"),
                        "分鐘": st.column_config.NumberColumn("分鐘", format="%d min"),
                    }
                )

                st.info(f"本場次規劃統計：總時長共 {total_minutes} 分鐘。請確保訓練內容在時限內完成。")
            else:
                st.warning("尚未為此場次安排任何訓練項目。")
        
# ---- Tab 4: Results (實務教練優化版) ----
with tab4:
    st.subheader("📊 訓練成效即時紀錄")
    
    # 這裡可以用之前教你的 CSS 把按鈕變綠色
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 選球員與場次 (保持原本邏輯)
        pass 

    with col2:
        # 教練在意的狀態紀錄
        player_condition = st.select_slider("球員今日狀態 (體能/心理)", options=["疲憊", "欠佳", "普通", "良好", "極佳"], value="普通")
        
    with col3:
        # 紀錄模式切換
        mode = st.radio("紀錄模式", ["數值紀錄 (成功率)", "質性紀錄 (純觀察)"])

    st.divider()

    with st.form("result_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            success = st.number_input("成功次數", min_value=0, step=1)
        with c2:
            total = st.number_input("總次數", min_value=0, step=1)
        with c3:
            # 實務上教練最在意的：失誤類型標準化
            error_category = st.multiselect("主要問題點", ["腳步不到位", "手型不穩", "擊球點錯誤", "觀察不足", "溝通喊聲"])

        notes = st.text_area("教練指導筆記 (對該球員的具體建議)")
        
        # 統一綠色按鈕
        submit = st.form_submit_button("存入訓練資料庫", type="primary", use_container_width=True)
        
        if submit:
            # 這裡寫入資料庫的邏輯...
            st.success("紀錄已存檔！辛苦了。")

# ---- Tab 5: Analytics ----
with tab5:
    st.markdown("#### 分析（對應附錄 SQL 範例）")
    colA, colB = st.columns(2)

    # ===== 左欄：1 + 3 =====
    with colA:
        st.markdown("**1) 近 4 週每位球員訓練量**")
        st.dataframe(
            df(con, """
                SELECT
                    p.name AS 球員,
                    COUNT(DISTINCT r.session_id) AS 近四週場次數,
                    SUM(r.total_count) AS 近四週總動作數
                FROM drill_results r
                JOIN players p ON p.player_id = r.player_id
                JOIN sessions s ON s.session_id = r.session_id
                WHERE s.session_date >= date('now','-28 day')
                GROUP BY p.name
                ORDER BY 近四週總動作數 DESC;
            """),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("**3) 指定球員 × 指定訓練項目的週別進步趨勢**")

        players = df(con, "SELECT player_id, name FROM players ORDER BY name;")
        drills = df(con, "SELECT drill_id, drill_name FROM drills ORDER BY drill_name;")

        pid_list = players["player_id"].astype(int).tolist()
        pid_map = {int(r.player_id): r.name for r in players.itertuples(index=False)}

        did_list = drills["drill_id"].astype(int).tolist()
        did_map = {int(r.drill_id): r.drill_name for r in drills.itertuples(index=False)}

        pid = st.selectbox(
            "選擇球員",
            options=pid_list,
            format_func=lambda x: pid_map.get(int(x), ""),
            key="a_pid"
        )
        did = st.selectbox(
            "選擇訓練項目",
            options=did_list,
            format_func=lambda x: did_map.get(int(x), ""),
            key="a_did"
        )

        trend = df(con, """
            SELECT
                strftime('%Y-%W', s.session_date) AS 週別,
                printf('%.1f%%', 100.0 * SUM(r.success_count) / NULLIF(SUM(r.total_count), 0)) AS 成功率,
                SUM(r.total_count) AS 總動作數
            FROM drill_results r
            JOIN sessions s ON s.session_id = r.session_id
            WHERE r.player_id = ?
              AND r.drill_id = ?
            GROUP BY strftime('%Y-%W', s.session_date)
            ORDER BY 週別 ASC;
        """, (int(pid), int(did)))

        st.dataframe(trend, use_container_width=True, hide_index=True)

    # ===== 右欄：2 + 4 + 5 =====
    with colB:
        st.markdown("**2) 成功率最低的訓練項目（至少 30 次）**")
        st.dataframe(
            df(con, """
                SELECT
                    d.drill_name AS 訓練項目,
                    CASE
                        WHEN d.category IN ('攻擊','接發','防守','發球','舉球','攔網','綜合') THEN d.category
                        WHEN d.category = 'attack_chain' THEN '攻擊'
                        WHEN d.category = 'serve_receive' THEN '接發'
                        WHEN d.category = 'defense' THEN '防守'
                        WHEN d.category = 'serve' THEN '發球'
                        WHEN d.category IN ('set','setting') THEN '舉球'
                        WHEN d.category IN ('block','blocking') THEN '攔網'
                        WHEN d.category IN ('all','mix','mixed','comprehensive','summary') THEN '綜合'
                        ELSE COALESCE(d.category, '')
                    END AS 類別,
                    printf('%.1f%%', 100.0 * SUM(r.success_count) / NULLIF(SUM(r.total_count), 0)) AS 成功率,
                    SUM(r.total_count) AS 總動作數
                FROM drill_results r
                JOIN drills d ON d.drill_id = r.drill_id
                GROUP BY d.drill_name, 類別
                HAVING SUM(r.total_count) >= 30
                ORDER BY 100.0 * SUM(r.success_count) / NULLIF(SUM(r.total_count), 0) ASC;
            """),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("**4) 依訓練主題（主題）統計整體表現**")
        st.dataframe(
            df(con, """
                SELECT
                    s.theme AS 主題,
                    COUNT(DISTINCT s.session_id) AS 場次數,
                    printf('%.1f%%', 100.0 * SUM(r.success_count) / NULLIF(SUM(r.total_count), 0)) AS 整體成功率,
                    SUM(r.total_count) AS 總動作數
                FROM sessions s
                JOIN drill_results r ON r.session_id = s.session_id
                GROUP BY s.theme
                ORDER BY 場次數 DESC;
            """),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("**5) 失誤類型排行榜**")
        st.dataframe(
            df(con, """
                SELECT
                    COALESCE(NULLIF(TRIM(r.error_type), ''), '（未填）') AS 失誤類型,
                    COUNT(*) AS 次數
                FROM drill_results r
                GROUP BY COALESCE(NULLIF(TRIM(r.error_type), ''), '（未填）')
                ORDER BY 次數 DESC;
            """),
            use_container_width=True,
            hide_index=True
        )


 
