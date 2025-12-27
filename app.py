import os
import sqlite3
from typing import Optional, Tuple

import pandas as pd
import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "volley_training.db")
SCHEMA_PATH = os.path.join(APP_DIR, "schema.sql")
SEED_PATH = os.path.join(APP_DIR, "seed_data.sql")


# -----------------------
# DB helpers
# -----------------------
def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def run_sql_script(con: sqlite3.Connection, path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        con.executescript(f.read())
    con.commit()


def init_db_if_needed() -> sqlite3.Connection:
    con = connect()
    if not os.path.exists(DB_PATH):
        # fresh create
        run_sql_script(con, SCHEMA_PATH)
        run_sql_script(con, SEED_PATH)
    else:
        # sanity: if DB exists but tables missing, recreate
        try:
            con.execute("SELECT 1 FROM players LIMIT 1;").fetchone()
        except Exception:
            # rebuild
            con.close()
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            con = connect()
            run_sql_script(con, SCHEMA_PATH)
            run_sql_script(con, SEED_PATH)
    return con


def reset_db_to_seed() -> None:
    # Close any open connections by recreating DB file (Streamlit rerun will reconnect)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = connect()
    run_sql_script(con, SCHEMA_PATH)
    run_sql_script(con, SEED_PATH)
    con.close()


def df(con: sqlite3.Connection, sql: str, params: Tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, con, params=params)


def exec_one(con: sqlite3.Connection, sql: str, params: Tuple = ()) -> None:
    con.execute(sql, params)
    con.commit()


# -----------------------
# UI config
# -----------------------
st.set_page_config(page_title="排球訓練知識庫（SQLite + Streamlit）", layout="wide")


# -----------------------
# Sidebar
# -----------------------
with st.sidebar:
    st.markdown("### 資料庫")
    st.code(DB_PATH, language="text")
    st.caption("（Streamlit Cloud 上為暫存檔案系統；重啟/重新部署可能重置資料。）")

    if st.button("重置為示例資料（會清空現有資料）", type="primary"):
        reset_db_to_seed()
        st.success("已重置為示例資料。請稍等 1–2 秒後重新整理頁面（或等待自動 rerun）。")
        st.rerun()


# -----------------------
# Main
# -----------------------
st.title("排球訓練知識庫（SQLite + Streamlit 最小可用版）")
st.caption("用途：把 ERD/SQL 變成可操作的系統。可新增球員/訓練項目/場次/成效紀錄，並做基本統計分析。")

con = init_db_if_needed()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["球員 players", "訓練項目 drills", "訓練場次 sessions", "成效紀錄 drill_results", "分析（SQL）"]
)

# -----------------------
# Tab 1: Players
# -----------------------
POSITIONS = ["主攻", "副攻", "攔中", "舉球", "自由"]

with tab1:
    colL, colR = st.columns([1, 1])

    with colL:
        st.markdown("#### 新增球員")
        name = st.text_input("姓名", key="p_name")
        position = st.selectbox("位置", options=POSITIONS, index=0, key="p_pos")
        grade_year = st.text_input("年級（例：大一/大二）", key="p_grade")

        if st.button("新增球員", key="p_add"):
            if not name.strip():
                st.error("姓名必填。")
            else:
                exec_one(
                    con,
                    "INSERT INTO players (name, position, grade_year) VALUES (?, ?, ?);",
                    (name.strip(), position.strip(), grade_year.strip()),
                )
                st.success("已新增球員。")
                st.rerun()

    with colR:
        st.markdown("#### 球員列表")
        players_df = df(
            con,
            "SELECT player_id, name, position, grade_year, created_at FROM players ORDER BY created_at DESC;",
        )
        st.dataframe(players_df, use_container_width=True, hide_index=True)


# -----------------------
# Tab 2: Drills
# -----------------------
with tab2:
    colL, colR = st.columns([1, 1])

    with colL:
        st.markdown("#### 新增訓練項目")
        drill_name = st.text_input("訓練項目名稱", key="d_name")
        objective = st.text_input("目的（可選）", key="d_obj")
        category = st.text_input("分類（例：serve_receive / defense / attack_chain / serve）", key="d_cat")
        difficulty = st.slider("難度（1-5）", min_value=1, max_value=5, value=3, step=1, key="d_diff")

        if st.button("新增訓練項目", key="d_add"):
            if not drill_name.strip():
                st.error("訓練項目名稱必填。")
            else:
                exec_one(
                    con,
                    "INSERT INTO drills (drill_name, objective, category, difficulty) VALUES (?, ?, ?, ?);",
                    (drill_name.strip(), objective.strip(), category.strip(), int(difficulty)),
                )
                st.success("已新增訓練項目。")
                st.rerun()

    with colR:
        st.markdown("#### 訓練項目列表")
        drills_df = df(
            con,
            "SELECT drill_id, drill_name, category, difficulty, created_at FROM drills ORDER BY created_at DESC;",
        )
        st.dataframe(drills_df, use_container_width=True, hide_index=True)


# -----------------------
# Tab 3: Sessions + session_drills
# -----------------------
with tab3:
    colL, colR = st.columns([1, 1])

    with colL:
        st.markdown("#### 新增訓練場次")
        session_date = st.date_input("日期", key="s_date")
        duration_min = st.number_input("時長（分鐘）", min_value=0, value=120, step=5, key="s_dur")
        theme = st.text_input("主題（例：接發與防守 / 攻擊鏈）", key="s_theme")
        notes = st.text_area("備註（可選）", key="s_notes", height=90)

        if st.button("新增場次", key="s_add"):
            exec_one(
                con,
                "INSERT INTO sessions (session_date, duration_min, theme, notes) VALUES (?, ?, ?, ?);",
                (session_date.isoformat(), int(duration_min), theme.strip(), notes.strip()),
            )
            st.success("已新增場次。")
            st.rerun()

        st.markdown("---")
        st.markdown("#### 將訓練項目加入場次（session_drills）")

        sessions = df(con, "SELECT session_id, session_date, theme FROM sessions ORDER BY session_date DESC;")
        drills = df(con, "SELECT drill_id, drill_name FROM drills ORDER BY drill_name;")

        if sessions.empty or drills.empty:
            st.info("先新增至少一個場次與一個訓練項目。")
        else:
            # Build id->label maps to avoid split parsing errors
            session_map = {int(r.session_id): f"{r.session_date}｜{r.theme}" for r in sessions.itertuples(index=False)}
            drill_map = {int(r.drill_id): f"{r.drill_name}" for r in drills.itertuples(index=False)}

            session_id = st.selectbox(
                "選擇場次",
                options=list(session_map.keys()),
                format_func=lambda sid: f"{sid}｜{session_map[sid]}",
                key="sd_session",
            )
            drill_id = st.selectbox(
                "選擇訓練項目",
                options=list(drill_map.keys()),
                format_func=lambda did: f"{did}｜{drill_map[did]}",
                key="sd_drill",
            )
            sequence_no = st.number_input("順序（sequence_no）", min_value=1, value=1, step=1, key="sd_seq")
            planned_minutes = st.number_input("預計分鐘（可選）", min_value=0, value=20, step=5, key="sd_min")
            planned_reps = st.number_input("預計次數（可選）", min_value=0, value=50, step=5, key="sd_reps")

            if st.button("加入場次", key="sd_add"):
                exec_one(
                    con,
                    """
                    INSERT OR REPLACE INTO session_drills
                    (session_id, drill_id, sequence_no, planned_minutes, planned_reps)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (int(session_id), int(drill_id), int(sequence_no), int(planned_minutes), int(planned_reps)),
                )
                st.success("已加入/更新。")
                st.rerun()

    with colR:
        st.markdown("#### 場次列表")
        st.dataframe(
            df(
                con,
                "SELECT session_id, session_date, duration_min, theme, created_at FROM sessions ORDER BY session_date DESC;",
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### 場次-項目（session_drills）")
        st.dataframe(
            df(
                con,
                """
                SELECT sd.session_id, s.session_date, s.theme,
                       sd.sequence_no, sd.drill_id, d.drill_name,
                       sd.planned_minutes, sd.planned_reps
                FROM session_drills sd
                JOIN sessions s ON s.session_id = sd.session_id
                JOIN drills d ON d.drill_id = sd.drill_id
                ORDER BY s.session_date DESC, sd.sequence_no ASC;
                """,
            ),
            use_container_width=True,
            hide_index=True,
        )


# -----------------------
# Tab 4: drill_results
# -----------------------
ERROR_TYPES = ["", "腳步不到位", "發球失誤", "接發不到位", "傳球不穩", "攻擊出界", "攔網觸網", "判斷失誤", "其他"]

with tab4:
    colL, colR = st.columns([1, 1])

    with colL:
        st.markdown("#### 輸入成效紀錄（drill_results）")

        players = df(con, "SELECT player_id, name, position FROM players ORDER BY name;")
        sessions = df(con, "SELECT session_id, session_date, theme FROM sessions ORDER BY session_date DESC;")

        if players.empty or sessions.empty:
            st.info("請先新增球員與場次。")
        else:
            player_map = {int(r.player_id): f"{r.name}（{r.position}）" for r in players.itertuples(index=False)}
            session_map = {int(r.session_id): f"{r.session_date}｜{r.theme}" for r in sessions.itertuples(index=False)}

            player_id = st.selectbox(
                "選擇球員",
                options=list(player_map.keys()),
                format_func=lambda pid: f"{pid}｜{player_map[pid]}",
                key="r_player",
            )
            session_id = st.selectbox(
                "選擇場次",
                options=list(session_map.keys()),
                format_func=lambda sid: f"{sid}｜{session_map[sid]}",
                key="r_session",
            )

            # Prefer drills already added to that session; fallback to all drills
            drills_in_session = df(
                con,
                """
                SELECT d.drill_id, d.drill_name
                FROM session_drills sd
                JOIN drills d ON d.drill_id = sd.drill_id
                WHERE sd.session_id = ?
                ORDER BY sd.sequence_no ASC;
                """,
                params=(int(session_id),),
            )

            if drills_in_session.empty:
                drills = df(con, "SELECT drill_id, drill_name FROM drills ORDER BY drill_name;")
            else:
                drills = drills_in_session

            drill_map = {int(r.drill_id): f"{r.drill_name}" for r in drills.itertuples(index=False)}
            drill_id = st.selectbox(
                "選擇訓練項目",
                options=list(drill_map.keys()),
                format_func=lambda did: f"{did}｜{drill_map[did]}",
                key="r_drill",
            )

            total_cnt = st.number_input("總次數（total_cnt）", min_value=0, value=50, step=1, key="r_total")
            success_cnt = st.number_input("成功次數（success_cnt）", min_value=0, value=40, step=1, key="r_success")
            error_type = st.selectbox("主要失誤類型（可選）", options=ERROR_TYPES, index=0, key="r_err")
            note = st.text_area("備註（可選）", key="r_note", height=80)

            if st.button("新增成效紀錄", key="r_add"):
                if int(total_cnt) <= 0:
                    st.error("總次數必須 > 0。")
                elif int(success_cnt) < 0 or int(success_cnt) > int(total_cnt):
                    st.error("成功次數必須介於 0 到 總次數之間。")
                else:
                    exec_one(
                        con,
                        """
                        INSERT INTO drill_results
                        (player_id, session_id, drill_id, success_cnt, total_cnt, error_type, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            int(player_id),
                            int(session_id),
                            int(drill_id),
                            int(success_cnt),
                            int(total_cnt),
                            error_type.strip(),
                            note.strip(),
                        ),
                    )
                    st.success("已新增成效紀錄。")
                    st.rerun()

    with colR:
        st.markdown("#### 成效紀錄列表（最近 200 筆）")
        results_df = df(
            con,
            """
            SELECT r.result_id,
                   r.player_id, p.name AS player_name,
                   r.session_id, s.session_date, s.theme,
                   r.drill_id, d.drill_name,
                   r.success_cnt, r.total_cnt,
                   ROUND(CAST(r.success_cnt AS REAL) / r.total_cnt, 3) AS success_rate,
                   r.error_type,
                   r.created_at
            FROM drill_results r
            JOIN players p ON p.player_id = r.player_id
            JOIN sessions s ON s.session_id = r.session_id
            JOIN drills d ON d.drill_id = r.drill_id
            ORDER BY r.created_at DESC
            LIMIT 200;
            """,
        )
        st.dataframe(results_df, use_container_width=True, hide_index=True)


# -----------------------
# Tab 5: Analysis (SQL examples)
# -----------------------
with tab5:
    st.markdown("## 分析（對應附錄 SQL 範例）")
    st.caption("以下為常見統計查詢：訓練量、瓶頸項目、趨勢、主題表現、失誤統計。")

    colA, colB = st.columns([1, 1])

    with colA:
        st.markdown("### 1｜近 4 週每位球員訓練量")
        q1 = """
        SELECT
            p.player_id,
            p.name,
            COUNT(DISTINCT r.session_id) AS sessions_in_last_4w,
            SUM(r.total_cnt) AS total_actions
        FROM drill_results r
        JOIN players p ON p.player_id = r.player_id
        JOIN sessions s ON s.session_id = r.session_id
        WHERE date(s.session_date) >= date('now', '-28 day')
        GROUP BY p.player_id, p.name
        ORDER BY total_actions DESC;
        """
        st.dataframe(df(con, q1), use_container_width=True, hide_index=True)

    with colB:
        st.markdown("### 2｜成功率最低的訓練項目（最低→最高）")
        q2 = """
        SELECT
            d.drill_id,
            d.drill_name,
            d.category,
            ROUND(SUM(r.success_cnt) * 1.0 / SUM(r.total_cnt), 3) AS success_rate,
            SUM(r.total_cnt) AS total_actions
        FROM drill_results r
        JOIN drills d ON d.drill_id = r.drill_id
        GROUP BY d.drill_id, d.drill_name, d.category
        HAVING SUM(r.total_cnt) > 0
        ORDER BY success_rate ASC, total_actions DESC
        LIMIT 20;
        """
        st.dataframe(df(con, q2), use_container_width=True, hide_index=True)

    st.markdown("---")
    colC, colD = st.columns([1, 1])

    with colC:
        st.markdown("### 3｜指定球員 × 指定 drill 的週別進步趨勢")
        players = df(con, "SELECT player_id, name FROM players ORDER BY name;")
        drills = df(con, "SELECT drill_id, drill_name FROM drills ORDER BY drill_name;")

        if players.empty or drills.empty:
            st.info("需要至少一位球員與一個訓練項目才可分析。")
        else:
            pid = st.selectbox(
                "選擇球員",
                options=players["player_id"].tolist(),
                format_func=lambda x: f"{int(x)}｜{players.loc[players['player_id'] == x, 'name'].iloc[0]}",
                key="a_pid",
            )
            did = st.selectbox(
                "選擇 drill",
                options=drills["drill_id"].tolist(),
                format_func=lambda x: f"{int(x)}｜{drills.loc[drills['drill_id'] == x, 'drill_name'].iloc[0]}",
                key="a_did",
            )

            q3 = """
            SELECT
                strftime('%Y-%W', s.session_date) AS year_week,
                ROUND(SUM(r.success_cnt) * 1.0 / SUM(r.total_cnt), 3) AS success_rate,
                SUM(r.total_cnt) AS total_actions
            FROM drill_results r
            JOIN sessions s ON s.session_id = r.session_id
            WHERE r.player_id = ? AND r.drill_id = ?
            GROUP BY year_week
            ORDER BY year_week ASC;
            """
            st.dataframe(df(con, q3, params=(int(pid), int(did))), use_container_width=True, hide_index=True)

    with colD:
        st.markdown("### 4｜依訓練主題（theme）統計整體表現")
        q4 = """
        SELECT
            s.theme,
            COUNT(DISTINCT r.session_id) AS sessions,
            ROUND(SUM(r.success_cnt) * 1.0 / SUM(r.total_cnt), 3) AS overall_success_rate
        FROM drill_results r
        JOIN sessions s ON s.session_id = r.session_id
        GROUP BY s.theme
        HAVING SUM(r.total_cnt) > 0
        ORDER BY sessions DESC, overall_success_rate DESC;
        """
        st.dataframe(df(con, q4), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 5｜失誤類型排行榜")
    q5 = """
    SELECT
        COALESCE(NULLIF(TRIM(r.error_type), ''), '(未填)') AS error_type,
        COUNT(*) AS error_events
    FROM drill_results r
    GROUP BY error_type
    ORDER BY error_events DESC
    LIMIT 20;
    """
    st.dataframe(df(con, q5), use_container_width=True, hide_index=True)
