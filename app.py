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
                
import plotly.express as px  # 確保你在程式碼最上方有 import plotly.express as px

import plotly.express as px

# ---- Tab 5: Analytics (Plotly 專業修復版) ----
with tab5:
    st.subheader("數據戰報與進步趨勢")
    
    # 中文映射字典，確保圖表標籤美觀
    CAT_MAP = {
        "attack": "攻擊", "defense": "防守", "serve": "發球", 
        "set": "舉球", "receive": "接發", "block": "攔網",
        "attack_chain": "攻擊鏈", "serve_receive": "接發球"
    }

    col_trend, col_team = st.columns([1, 1.2])

    # 1. 左欄：個人成長趨勢
    with col_trend:
        st.markdown("#### 個人技術成長曲線")
        p_data = df(con, "SELECT player_id, name FROM players ORDER BY name;")
        if not p_data.empty:
            c1, c2 = st.columns(2)
            with c1:
                sel_p_id = st.selectbox("選擇球員", options=p_data['player_id'], 
                                        format_func=lambda x: p_data[p_data['player_id']==x]['name'].values[0], key="ana_p")
            with c2:
                sel_cat = st.selectbox("技術類別", options=["攻擊", "接發", "防守", "發球", "舉球", "攔網"], key="ana_cat")

            trend_df = df(con, """
                SELECT strftime('%Y-%m-%d', s.session_date) AS 日期,
                       SUM(r.success_count) AS 成功, SUM(r.total_count) AS 總次數
                FROM drill_results r
                JOIN sessions s ON s.session_id = r.session_id
                JOIN drills d ON d.drill_id = r.drill_id
                WHERE r.player_id = ? AND (d.category = ? OR d.drill_name LIKE '%' || ? || '%')
                GROUP BY 日期 ORDER BY 日期 ASC
            """, (int(sel_p_id), sel_cat, sel_cat))

            if not trend_df.empty:
                trend_df['成功率'] = (trend_df['成功'] / trend_df['總次數'] * 100).round(1)
                fig_line = px.line(trend_df, x='日期', y='成功率', markers=True, 
                                   labels={'成功率': '成功率 (%)'}, title=f"{sel_cat} 趨勢")
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("尚無足夠數據產生曲線。")

    # 2. 右欄：全隊技術短板 (橫式圖表)
    with col_team:
        st.markdown("#### 全隊技術短板分析")
        team_stats = df(con, """
            SELECT d.category AS cat,
                   CAST(SUM(r.success_count) AS FLOAT) / SUM(r.total_count) * 100 AS rate
            FROM drill_results r
            JOIN drills d ON d.drill_id = r.drill_id
            WHERE d.category != 'summary' AND r.total_count > 0
            GROUP BY d.category
        """)
        
        if not team_stats.empty:
            team_stats['技術類別'] = team_stats['cat'].apply(lambda x: CAT_MAP.get(x, x))
            team_stats['成功率(%)'] = team_stats['rate'].round(1)
            plot_df = team_stats.sort_values(by='成功率(%)', ascending=True)

            # 使用 Plotly 畫橫向條形圖
            fig_bar = px.bar(
                plot_df, x="成功率(%)", y="技術類別", orientation='h',
                text="成功率(%)", color="成功率(%)",
                color_continuous_scale='Blues', range_x=[0, 100]
            )
            fig_bar.update_layout(showlegend=False, xaxis_title="成功率 (%)", yaxis_title="", height=400)
            fig_bar.update_traces(textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("尚無全隊統計數據。")
