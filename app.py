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

# ---- Tab 1: Players ----
with tab1:
    colL, colR = st.columns([1, 1])
    with colL:
        st.markdown("#### 新增球員")
        name = st.text_input("姓名", key="p_name")
        POS_OPTIONS = ["主攻", "攔中", "副攻", "舉球", "自由", "（不填）"]
        pos_sel = st.selectbox("位置（可選）", POS_OPTIONS, index=0, key="p_pos_sel")
        position = "" if pos_sel == "（不填）" else pos_sel

        grade_year = st.text_input("年級（例：大一/大二）", key="p_grade")
        if st.button("新增球員", key="p_add"):
            if not name.strip():
                st.error("姓名必填。")
            else:
                exec_one(con, "INSERT INTO players (name, position, grade_year) VALUES (?, ?, ?);",
                         (name.strip(), position, grade_year.strip()))
                st.success("已新增。")
    with colR:
        st.markdown("#### 球員列表")
        st.dataframe(df(con, "SELECT player_id, name, position, grade_year, created_at FROM players ORDER BY player_id DESC;"),
                     use_container_width=True, hide_index=True)

# ---- Tab 2: Drills ----
with tab2:
    colL, colR = st.columns([1, 1])
    with colL:
        st.markdown("#### 新增訓練項目")
        drill_name = st.text_input("訓練項目名稱", key="d_name")
        objective = st.text_input("目的（可選）", key="d_obj")
        category = st.text_input("分類（例：serve_receive / defense / attack_chain / serve）", key="d_cat")
        difficulty = st.slider("難度（1-5）", 1, 5, 3, key="d_diff")
        if st.button("新增訓練項目", key="d_add"):
            if not drill_name.strip():
                st.error("訓練項目名稱必填。")
            else:
                exec_one(con, "INSERT INTO drills (drill_name, objective, category, difficulty) VALUES (?, ?, ?, ?);",
                         (drill_name.strip(), objective.strip(), category.strip(), int(difficulty)))
                st.success("已新增。")
    with colR:
        st.markdown("#### 訓練項目列表")
        st.dataframe(df(con, "SELECT drill_id, drill_name, category, difficulty, created_at FROM drills ORDER BY drill_id DESC;"),
                     use_container_width=True, hide_index=True)

# ---- Tab 3: Sessions ----
with tab3:
    colL, colR = st.columns([1, 1])
    with colL:
        st.markdown("#### 新增訓練場次")
        session_date = st.date_input("日期", key="s_date")
        duration_min = st.number_input("時長（分鐘）", min_value=0, value=120, step=5, key="s_dur")
        theme = st.text_input("主題（例：接發與防守 / 攻擊鏈）", key="s_theme")
        notes = st.text_area("備註（可選）", key="s_notes", height=90)
        if st.button("新增場次", key="s_add"):
            exec_one(con, "INSERT INTO sessions (session_date, duration_min, theme, notes) VALUES (?, ?, ?, ?);",
                     (session_date.isoformat(), int(duration_min), theme.strip(), notes.strip()))
            st.success("已新增。")

        st.markdown("---")
        st.markdown("#### 將訓練項目加入場次（session_drills）")
        sessions = df(con, "SELECT session_id, session_date, theme FROM sessions ORDER BY session_date DESC;")
        drills = df(con, "SELECT drill_id, drill_name FROM drills ORDER BY drill_name;")

        if sessions.empty or drills.empty:
            st.info("先新增至少一個場次與一個訓練項目。")
        else:
            session_id = st.selectbox("選擇場次", sessions.apply(lambda r: f"{r.session_id}｜{r.session_date}｜{r.theme}", axis=1))
            session_id = int(session_id.split("｜")[0])
            drill_id = st.selectbox("選擇訓練項目", drills.apply(lambda r: f"{r.drill_id}｜{r.drill_name}", axis=1))
            drill_id = int(drill_id.split("｜")[0])
            sequence_no = st.number_input("順序（sequence_no）", min_value=1, value=1, step=1)
            planned_minutes = st.number_input("預計分鐘（可選）", min_value=0, value=20, step=5)
            planned_reps = st.number_input("預計次數（可選）", min_value=0, value=50, step=5)
            if st.button("加入場次", key="sd_add"):
                exec_one(con, """
                    INSERT OR REPLACE INTO session_drills
                    (session_id, drill_id, sequence_no, planned_minutes, planned_reps)
                    VALUES (?, ?, ?, ?, ?);
                """, (session_id, drill_id, int(sequence_no), int(planned_minutes), int(planned_reps)))
                st.success("已加入/更新。")

    with colR:
        st.markdown("#### 場次列表")
        st.dataframe(df(con, "SELECT session_id, session_date, duration_min, theme, created_at FROM sessions ORDER BY session_date DESC;"),
                     use_container_width=True, hide_index=True)
        st.markdown("#### 場次-項目（session_drills）")
        st.dataframe(df(con, """
            SELECT sd.session_id, s.session_date, s.theme,
                   sd.sequence_no, sd.drill_id, d.drill_name,
                   sd.planned_minutes, sd.planned_reps
            FROM session_drills sd
            JOIN sessions s ON s.session_id = sd.session_id
            JOIN drills d ON d.drill_id = sd.drill_id
            ORDER BY s.session_date DESC, sd.sequence_no ASC;
        """), use_container_width=True, hide_index=True)

# --- Tab 4: Results ---
with tab4:
    st.markdown("#### 新增成效記錄（drill_results）")

    # 只改這三行：players 多抓 grade_year，並維持你的排序習慣即可
    sessions = df(con, "SELECT session_id, session_date, duration_min, theme FROM sessions ORDER BY session_date DESC;")
    drills   = df(con, "SELECT drill_id, drill_name FROM drills ORDER BY drill_name;")
    players  = df(con, "SELECT player_id, name, position, grade_year FROM players ORDER BY name;")

    if sessions.empty or drills.empty or players.empty:
        st.info("先新增場次、訓練項目、球員。")
    else:
      c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 1])

    # ---------- c1: 場次（不顯示 id；顯示 12/15 綜合訓練（85min）） ----------
    with c1:
        def _session_label(r):
            # session_date: 'YYYY-MM-DD' -> 'MM/DD'
            s = (r.session_date or "").strip()
            mmdd = s[5:7] + "/" + s[8:10] if len(s) >= 10 else s

            theme = (getattr(r, "theme", "") or "").strip()
            dur = getattr(r, "duration_min", None)

            # 顯示成：12/15 綜合訓練（85min）
            dur_txt = f"（{int(dur)}min）" if dur is not None and str(dur).strip() != "" else ""
            return f"{mmdd} {theme}{dur_txt}".strip() if theme else f"{mmdd}{dur_txt}".strip()

        session_map = {int(r.session_id): _session_label(r) for r in sessions.itertuples(index=False)}

        session_id = st.selectbox(
            "場次",
            options=list(session_map.keys()),
            format_func=lambda sid: session_map[sid],
            key="r_session",
        )

    # ---------- c2: 訓練項目（不顯示 id） ----------
    with c2:
        def _drill_label(r):
            return (r.drill_name or "").strip()

        drill_map = {int(r.drill_id): _drill_label(r) for r in drills.itertuples(index=False)}

        drill_id = st.selectbox(
            "訓練項目",
            options=list(drill_map.keys()),
            format_func=lambda did: drill_map[did],
            key="r_drill",
        )

    # ---------- c3: 球員（小涵（主攻｜大二）） ----------
    with c3:
        def _player_label(r):
            name = (r.name or "").strip()
            pos = (r.position or "").strip()
            grade = (getattr(r, "grade_year", "") or "").strip()

            if pos and grade:
                return f"{name}（{pos}｜{grade}）"
            elif pos:
                return f"{name}（{pos}）"
            elif grade:
                return f"{name}（{grade}）"
            else:
                return name

        player_map = {int(r.player_id): _player_label(r) for r in players.itertuples(index=False)}

        player_id = st.selectbox(
            "球員",
            options=list(player_map.keys()),
            format_func=lambda pid: player_map[pid],
            key="r_player",
        )

    with c4:
            error_type = st.text_input("失誤類型（可選）", key="r_err")
            # ... 你原本 success_count / total_count / notes / INSERT INTO drill_results 那段照舊


# ---- Tab 5: Analytics ----
with tab5:
    st.markdown("#### 分析（對應附錄 SQL 範例）")
    colA, colB = st.columns(2)

    with colA:
        st.markdown("**1｜近 4 週每位球員訓練量**")
        st.dataframe(df(con, """
            SELECT
              r.player_id,
              p.name,
              COUNT(DISTINCT r.session_id) AS sessions_in_last_4w,
              SUM(r.total_count) AS total_actions
            FROM drill_results r
            JOIN players p ON p.player_id = r.player_id
            JOIN sessions s ON s.session_id = r.session_id
            WHERE s.session_date >= date('now','-28 day')
            GROUP BY r.player_id, p.name
            ORDER BY total_actions DESC;
        """), use_container_width=True, hide_index=True)

        st.markdown("**3｜指定球員 × 指定 drill 的週別進步趨勢**")
        players = df(con, "SELECT player_id, name FROM players ORDER BY name;")
        drills = df(con, "SELECT drill_id, drill_name FROM drills ORDER BY drill_name;")
        if not players.empty and not drills.empty:
            pid = st.selectbox("選擇球員", players.apply(lambda r: f"{r.player_id}｜{r.name}", axis=1), key="a_pid")
            did = st.selectbox("選擇 drill", drills.apply(lambda r: f"{r.drill_id}｜{r.drill_name}", axis=1), key="a_did")
            pid = int(pid.split("｜")[0])
            did = int(did.split("｜")[0])
            trend = df(con, """
                SELECT
                  strftime('%Y-%W', s.session_date) AS year_week,
                  ROUND(1.0 * SUM(r.success_count) / NULLIF(SUM(r.total_count), 0), 3) AS success_rate,
                  SUM(r.total_count) AS total_actions
                FROM drill_results r
                JOIN sessions s ON s.session_id = r.session_id
                WHERE r.player_id = ?
                  AND r.drill_id = ?
                GROUP BY strftime('%Y-%W', s.session_date)
                ORDER BY year_week ASC;
            """, (pid, did))
            st.dataframe(trend, use_container_width=True, hide_index=True)
        else:
            st.info("需要先有球員與 drill。")

    with colB:
        st.markdown("**2｜成功率最低的訓練項目（最低→最高）**")
        st.dataframe(df(con, """
            SELECT
              d.drill_id,
              d.drill_name,
              d.category,
              ROUND(1.0 * SUM(r.success_count) / NULLIF(SUM(r.total_count), 0), 3) AS success_rate,
              SUM(r.total_count) AS total_actions
            FROM drill_results r
            JOIN drills d ON d.drill_id = r.drill_id
            GROUP BY d.drill_id, d.drill_name, d.category
            HAVING SUM(r.total_count) >= 30
            ORDER BY success_rate ASC;
        """), use_container_width=True, hide_index=True)

        st.markdown("**4｜依訓練主題（theme）統計整體表現**")
        st.dataframe(df(con, """
            SELECT
              s.theme,
              COUNT(DISTINCT s.session_id) AS sessions,
              ROUND(1.0 * SUM(r.success_count) / NULLIF(SUM(r.total_count), 0), 3) AS overall_success_rate
            FROM sessions s
            JOIN drill_results r ON r.session_id = s.session_id
            GROUP BY s.theme
            ORDER BY sessions DESC;
        """), use_container_width=True, hide_index=True)

        st.markdown("**5｜失誤類型排行榜**")
        st.dataframe(df(con, """
            SELECT
              COALESCE(NULLIF(TRIM(r.error_type),''), '(未填)') AS error_type,
              COUNT(*) AS error_events
            FROM drill_results r
            GROUP BY COALESCE(NULLIF(TRIM(r.error_type),''), '(未填)')
            ORDER BY error_events DESC;
        """), use_container_width=True, hide_index=True)
