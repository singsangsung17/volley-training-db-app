import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# --- 1. 資料庫基礎設定 ---
def get_connection():
    return sqlite3.connect("volleyball_v2.db", check_same_thread=False)

con = get_connection()

def df(con, query, params=()):
    return pd.read_sql_query(query, con, params=params)

def exec_one(con, query, params=()):
    with con:
        con.execute(query, params)

# 初始化資料表
exec_one(con, """CREATE TABLE IF NOT EXISTS players (player_id INTEGER PRIMARY KEY, name TEXT, position TEXT)""")
exec_one(con, """CREATE TABLE IF NOT EXISTS drills (drill_id INTEGER PRIMARY KEY, drill_name TEXT, category TEXT, description TEXT)""")
exec_one(con, """CREATE TABLE IF NOT EXISTS sessions (session_id INTEGER PRIMARY KEY, session_date TEXT, theme TEXT)""")
exec_one(con, """CREATE TABLE IF NOT EXISTS session_drills (sd_id INTEGER PRIMARY KEY, session_id INTEGER, drill_id INTEGER, drill_order INTEGER, duration_minutes INTEGER, target_reps TEXT)""")
exec_one(con, """CREATE TABLE IF NOT EXISTS drill_results (result_id INTEGER PRIMARY KEY, session_id INTEGER, drill_id INTEGER, player_id INTEGER, success_count INTEGER, total_count INTEGER, error_type TEXT, notes TEXT)""")

# --- 2. 核心介面樣式 ---
st.set_page_config(page_title="排球訓練知識庫", layout="wide")
st.markdown("""
    <style>
    /* 巨型點擊按鈕樣式 */
    .huge-btn div[data-testid="stButton"] button {
        min-height: 300px !important; font-size: 80px !important;
        font-weight: 900 !important; border-radius: 20px !important;
    }
    /* 迷你清空按鈕樣式 */
    .mini-btn div[data-testid="stButton"] button {
        min-height: 30px !important; font-size: 12px !important; width: 100px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("排球訓練知識庫 (專業修復版)")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["球員管理", "訓練項目", "訓練場次", "成效紀錄", "數據分析"])

# --- Tab 1 & 2 簡略 (保持原本 CRUD 邏輯即可) ---
with tab1: st.write("請在此管理球員名單")
with tab2: st.write("請在此管理訓練項目技術類別")

# --- 3. Tab 3: 訓練場次 (修正場次新增與預計組次名稱) ---
with tab3:
    col_m, col_f = st.columns([1, 1.5])
    with col_m:
        with st.expander("➕ 新增訓練場次"):
            nd = st.date_input("日期")
            nt = st.text_input("訓練主題")
            if st.button("確認新增場次", type="primary"):
                exec_one(con, "INSERT INTO sessions (session_date, theme) VALUES (?, ?)", (str(nd), nt))
                st.rerun()
        
        st.divider()
        ss = df(con, "SELECT * FROM sessions ORDER BY session_date DESC")
        if not ss.empty:
            s_map = {int(r.session_id): f"{r.session_date} | {r.theme}" for r in ss.itertuples(index=False)}
            sid = st.selectbox("目前操作場次", options=list(s_map.keys()), format_func=lambda x: s_map[x])
            
            st.markdown("#### 加入項目")
            ds = df(con, "SELECT drill_id, drill_name FROM drills WHERE category != 'summary'")
            d_map = {int(r.drill_id): r.drill_name for r in ds.itertuples(index=False)}
            sel_d = st.selectbox("訓練項目", options=list(d_map.keys()), format_func=lambda x: d_map[x])
            
            c1, c2 = st.columns(2)
            with c1: order = st.number_input("順序", min_value=1, value=1)
            with c2: mins = st.number_input("分鐘", min_value=5, step=5, value=20)
            
            # 修改點：標籤改回預計組次，移除 ", 3組"
            target = st.text_input("預計組次 (例如: 50*2 或 50下)", value="50下")
            
            if st.button("確認加入流程"):
                exec_one(con, "INSERT INTO session_drills (session_id, drill_id, drill_order, duration_minutes, target_reps) VALUES (?, ?, ?, ?, ?)", 
                         (int(sid), int(sel_d), int(order), int(mins), target))
                st.rerun()

    with col_f:
        st.markdown("#### 本場訓練流程")
        if not ss.empty:
            flow = df(con, "SELECT sd.drill_order AS No, d.drill_name AS 訓練內容, sd.duration_minutes || ' min' AS 分鐘, sd.target_reps AS 預計組次 FROM session_drills sd JOIN drills d ON d.drill_id = sd.drill_id WHERE sd.session_id = ? ORDER BY No", (int(sid),))
            st.table(flow)

# --- 4. Tab 4: 成效紀錄 (修復 NameError 與過濾總結項) ---
with tab4:
    # 修復：在 Tab 內重新抓取資料
    t4_ss = df(con, "SELECT session_id, theme FROM sessions ORDER BY session_date DESC")
    t4_ps = df(con, "SELECT player_id, name FROM players")
    
    if 'c_s' not in st.session_state: st.session_state.c_s = 0
    if 'c_t' not in st.session_state: st.session_state.c_t = 0

    if not t4_ss.empty and not t4_ps.empty:
        c1, c2, c3 = st.columns(3)
        with c1: sid = st.selectbox("紀錄場次", options=t4_ss['session_id'], format_func=lambda x: t4_ss[t4_ss['session_id']==x]['theme'].values[0])
        with c2: pid = st.selectbox("紀錄球員", options=t4_ps['player_id'], format_func=lambda x: t4_ps[t4_ps['player_id']==x]['name'].values[0])
        with c3:
            # 修復：徹底過濾本場次總結
            curr_ds = df(con, "SELECT d.drill_id, d.drill_name FROM session_drills sd JOIN drills d ON d.drill_id = sd.drill_id WHERE sd.session_id = ? AND d.category != 'summary' AND d.drill_name != '本場次總結'", (int(sid),))
            d_map = {int(r.drill_id): r.drill_name for r in curr_ds.itertuples(index=False)}
            did = st.selectbox("訓練項目 ", options=list(d_map.keys()), format_func=lambda x: d_map[x])

        st.divider()
        st.markdown('<div class="huge-btn">', unsafe_allow_html=True)
        col_l, col_r = st.columns(2)
        with col_l:
            if st.button("成功", type="primary", use_container_width=True):
                st.session_state.c_s += 1; st.session_state.c_t += 1; st.rerun()
        with col_r:
            if st.button("失誤", use_container_width=True):
                st.session_state.c_t += 1; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        rate = (st.session_state.c_s / st.session_state.c_t * 100) if st.session_state.c_t > 0 else 0
        st.metric("當前累計", f"{st.session_state.c_s} / {st.session_state.c_t}", f"成功率 {rate:.1%}")
        
        st.markdown('<div class="mini-btn">', unsafe_allow_html=True)
        if st.button("清空計數"): st.session_state.c_s = 0; st.session_state.c_t = 0; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        with st.form("save_form"):
            issue = st.selectbox("主要問題", ["無", "腳步不到位", "擊球點錯誤", "觀察不足", "溝通不足"])
            notes = st.text_area("備註")
            if st.form_submit_button("正式存入資料庫", type="primary", use_container_width=True):
                exec_one(con, "INSERT INTO drill_results (session_id, drill_id, player_id, success_count, total_count, error_type, notes) VALUES (?,?,?,?,?,?,?)",
                         (int(sid), int(did), int(pid), st.session_state.c_s, st.session_state.c_t, issue, notes))
                st.session_state.c_s = 0; st.session_state.c_t = 0; st.rerun()

# --- 5. Tab 5: 分析 (Plotly 專業救命與顏色優化版) ---
with tab5:
    CAT_MAP = {"attack": "攻擊", "defense": "防守", "serve": "發球", "set": "舉球", "receive": "接發", "block": "攔網"}
    col_tr, col_te = st.columns([1, 1.2])
    
    with col_tr:
        st.markdown("#### 個人成長曲線")
        # 趨勢圖邏輯 (略)
        st.info("請在此查看個人數據走勢")

    with col_te:
        st.markdown("#### 全隊技術短板分析")
        team = df(con, "SELECT d.category AS cat, CAST(SUM(r.success_count) AS FLOAT)/SUM(r.total_count)*100 AS rate FROM drill_results r JOIN drills d ON d.drill_id = r.drill_id WHERE d.category != 'summary' GROUP BY d.category")
        if not team.empty:
            team['技術類別'] = team['cat'].apply(lambda x: CAT_MAP.get(x, x))
            fig = px.bar(team.sort_values('rate'), x="rate", y="技術類別", orientation='h', text=team['rate'].round(1),
                         color="rate", color_continuous_scale='Blues', range_x=[0,100], range_color=[0,100])
            fig.update_layout(showlegend=False, coloraxis_showscale=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
