import os
import sqlite3
from typing import Tuple, Dict, List

import pandas as pd
import streamlit as st


# =========================
# 0) 基本設定 & DB
# =========================
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
    run_sql_script(con, SCHEMA_PATH)
    if fresh and os.path.exists(SEED_PATH):
        run_sql_script(con, SEED_PATH)
    return con


def df(con, query: str, params: Tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(query, con, params=params)


def exec_one(con, query: str, params: Tuple = ()):
    con.execute(query, params)
    con.commit()


def fetch_one(con, query: str, params: Tuple = ()):
    cur = con.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    cur.close()
    return row


con = init_db_if_needed()


def detect_drills_text_col(con) -> str:
    cols = df(con, "PRAGMA table_info(drills);")["name"].tolist()
    if "purpose" in cols:
        return "purpose"
    if "objective" in cols:
        return "objective"
    raise RuntimeError("drills 表缺少 purpose/objective 欄位，請檢查 schema.sql")


DRILLS_TEXT_COL = detect_drills_text_col(con)


# =========================
# 1) 全域：中文分類與對照
# =========================
CATEGORY_OPTIONS_ZH = ["攻擊", "接發", "防守", "發球", "舉球", "攔網", "綜合"]


def cat_to_zh(c: str) -> str:
    c = (c or "").strip()
    mapping = {
        "attack_chain": "攻擊",
        "attack": "攻擊",
        "serve_receive": "接發",
        "receive": "接發",
        "defense": "防守",
        "serve": "發球",
        "set": "舉球",
        "setting": "舉球",
        "block": "攔網",
        "blocking": "攔網",
        "all": "綜合",
        "mix": "綜合",
        "mixed": "綜合",
        "comprehensive": "綜合",
        "summary": "綜合",
    }
    if c in CATEGORY_OPTIONS_ZH:
        return c
    return mapping.get(c, c)


# 目的模板（依分類）
PURPOSE_TEMPLATES: Dict[str, List[str]] = {
    "攻擊": ["提升擊球點", "加快攻擊節奏", "提升打點選擇", "提升斜線/直線控制"],
    "接發": ["提升到位率", "穩定平台角度", "提升判斷與移動", "降低失誤率"],
    "防守": ["提升防守反應", "提升移動與站位", "提升救球品質", "提升二波防守"],
    "發球": ["提升穩定度", "提升落點控制", "提升破壞性", "降低失誤率"],
    "舉球": ["提升舉球穩定度", "提升節奏控制", "提升分配判斷", "提升傳球到位"],
    "攔網": ["提升手型與封網", "提升起跳時機", "提升判斷與移動", "提升連續攔防"],
    "綜合": ["整合攻防節奏", "提升溝通與配合", "提升臨場決策", "提升整體穩定度"],
}


# =========================
# 2) UI
# =========================
st.title("排球訓練知識庫（SQLite + Streamlit）")
st.caption("重點：表格全中文、隱藏所有 id、分類固定中文下拉、purpose/objective 永不踩雷。")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["球員", "訓練項目", "訓練場次", "成效紀錄", "分析"]
)


# =========================
# Tab1：球員
# =========================
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
            if not (name or "").strip():
                st.error("姓名必填。")
            else:
                exec_one(
                    con,
                    "INSERT INTO players (name, position, grade_year) VALUES (?, ?, ?);",
                    (name.strip(), position, (grade_year or "").strip()),
                )
                st.success("已新增。")

    with colR:
        st.markdown("#### 球員列表")
        st.dataframe(
            df(
                con,
                """
                SELECT
                  name       AS 姓名,
                  position   AS 位置,
                  grade_year AS 年級,
                  created_at AS 建立時間
                FROM players
                ORDER BY created_at DESC;
                """,
            ),
            use_container_width=True,
            hide_index=True,
        )


# =========================
# Tab2：訓練項目（drills）
# =========================
with tab2:
    colL, colR = st.columns([1, 1])

    with colL:
        st.markdown("#### 新增訓練項目")
        drill_name = st.text_input("訓練項目名稱", key="d_name")

        category_zh = st.selectbox("分類（固定）", CATEGORY_OPTIONS_ZH, key="d_category_zh")

        preset = st.selectbox(
            "常用目的（可選）",
            options=["（不使用）"] + PURPOSE_TEMPLATES.get(category_zh, []),
            key="d_preset",
        )
        default_purpose = "" if preset == "（不使用）" else preset
        purpose_text = st.text_area("目的（可選，可自行修改）", value=default_purpose, height=90, key="d_purpose")

        difficulty = st.slider("難度（1-5）", 1, 5, 3, key="d_diff")

        if st.button("新增訓練項目", key="d_add"):
            _name = (drill_name or "").strip()
            _purpose = (purpose_text or "").strip()
            if not _name:
                st.error("訓練項目名稱不可為空。")
            else:
                exec_one(
                    con,
                    f"INSERT INTO drills (drill_name, {DRILLS_TEXT_COL}, category, difficulty) VALUES (?, ?, ?, ?);",
                    (_name, _purpose, category_zh, int(difficulty)),
                )
                st.success("已新增。")

    with colR:
        st.markdown("#### 訓練項目列表（全中文 / 隱藏 id / 難度置前）")
        st.dataframe(
            df(
                con,
                f"""
                SELECT
                    difficulty AS 難度,
                    drill_name AS 訓練項目,
                    CASE
                        WHEN category IN ('攻擊','接發','防守','發球','舉球','攔網','綜合') THEN category
                        WHEN category = 'attack_chain' THEN '攻擊'
                        WHEN category = 'serve_receive' THEN '接發'
                        WHEN category = 'defense' THEN '防守'
                        WHEN category = 'serve' THEN '發球'
                        WHEN category IN ('set','setting') THEN '舉球'
                        WHEN category IN ('block','blocking') THEN '攔網'
                        WHEN category IN ('all','mix','mixed','comprehensive','summary') THEN '綜合'
                        ELSE COALESCE(category, '')
                    END AS 類別,
                    COALESCE({DRILLS_TEXT_COL}, '') AS 目的,
                    created_at AS 建立時間
                FROM drills
                ORDER BY created_at DESC;
                """,
            ),
            use_container_width=True,
            hide_index=True,
        )


# =========================
# Tab3：訓練場次（sessions + session_drills）
# =========================
with tab3:
    colL, colR = st.columns([1, 1])

    sessions = df(
        con,
        """
        SELECT session_id, session_date, duration_min, theme
        FROM sessions
        ORDER BY session_date DESC, session_id DESC;
        """,
    )

    drills = df(
        con,
        f"""
        SELECT
            drill_id,
            drill_name,
            CASE
                WHEN category IN ('攻擊','接發','防守','發球','舉球','攔網','綜合') THEN category
                WHEN category = 'attack_chain' THEN '攻擊'
                WHEN category = 'serve_receive' THEN '接發'
                WHEN category = 'defense' THEN '防守'
                WHEN category = 'serve' THEN '發球'
                WHEN category IN ('set','setting') THEN '舉球'
                WHEN category IN ('block','blocking') THEN '攔網'
                WHEN category IN ('all','mix','mixed','comprehensive','summary') THEN '綜合'
                ELSE COALESCE(category, '')
            END AS category_zh
        FROM drills
        ORDER BY drill_name;
        """,
    )

    with colL:
        st.markdown("#### 場次操作")

        # 1) 先選場次（主流程，不逼你一直重填）
        if sessions.empty:
            st.info("目前沒有場次。請先建立一個場次。")
            st.session_state.pop("selected_session_id", None)
            selected_session_id = None
        else:
            session_ids = sessions["session_id"].astype(int).tolist()
            label_map = {
                int(r.session_id): f"{r.session_date}｜{r.theme}（{int(r.duration_min)} 分）"
                for r in sessions.itertuples(index=False)
            }

            if "selected_session_id" not in st.session_state:
                st.session_state["selected_session_id"] = int(session_ids[0])

            if st.session_state["selected_session_id"] not in label_map:
                st.session_state["selected_session_id"] = int(session_ids[0])

            default_index = session_ids.index(int(st.session_state["selected_session_id"]))

            selected_session_id = st.selectbox(
                "選擇場次（不顯示 id）",
                options=session_ids,
                index=default_index,
                format_func=lambda sid: label_map.get(int(sid), str(sid)),
                key="selected_session_id",
            )

        # 2) 建立新場次（放 expander）
        with st.expander("＋ 建立新場次", expanded=bool(sessions.empty)):
            session_date = st.date_input("日期", key="s_date")
            duration_min = st.number_input("總時長（分鐘）", min_value=0, value=120, step=5, key="s_dur")
            theme = st.text_input("主題（例：接發與防守 / 攻擊鏈）", key="s_theme")
            notes = st.text_area("備註（可選）", key="s_notes", height=90)

            if st.button("新增場次", key="s_add"):
                _theme = (theme or "").strip()
                _notes = (notes or "").strip()

                if not _theme:
                    st.error("主題不可為空。")
                else:
                    existed = fetch_one(
                        con,
                        "SELECT session_id FROM sessions WHERE session_date=? AND theme=? LIMIT 1;",
                        (session_date.isoformat(), _theme),
                    )
                    if existed:
                        st.session_state["selected_session_id"] = int(existed[0])
                        st.info("此日期＋主題的場次已存在，已切換到該場次。")
                    else:
                        exec_one(
                            con,
                            "INSERT INTO sessions (session_date, duration_min, theme, notes) VALUES (?, ?, ?, ?);",
                            (session_date.isoformat(), int(duration_min), _theme, _notes),
                        )
                        new_id = fetch_one(con, "SELECT last_insert_rowid();")[0]
                        st.session_state["selected_session_id"] = int(new_id)
                        st.success("已新增，並已切換到新場次。")

        st.markdown("---")
        st.markdown("#### 將訓練項目加入場次（不顯示 id）")

        if selected_session_id is None or drills.empty:
            st.info("先新增至少一個場次與一個訓練項目。")
        else:
            drill_ids = drills["drill_id"].astype(int).tolist()
            drill_label_map = {
                int(r.drill_id): f"{r.drill_name}（{r.category_zh}）"
                for r in drills.itertuples(index=False)
            }

            selected_drill_id = st.selectbox(
                "選擇訓練項目（不顯示 id）",
                options=drill_ids,
                format_func=lambda did: drill_label_map.get(int(did), str(did)),
                key="sd_drill_select",
            )

            next_seq = fetch_one(
                con,
                "SELECT COALESCE(MAX(sequence_no), 0) + 1 FROM session_drills WHERE session_id=?;",
                (int(selected_session_id),),
            )[0]

            sequence_no = st.number_input(
                "順序（sequence_no）",
                min_value=1,
                value=int(next_seq),
                step=1,
                key="sd_seq",
            )

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
                    (
                        int(selected_session_id),
                        int(selected_drill_id),
                        int(sequence_no),
                        int(planned_minutes),
                        int(planned_reps),
                    ),
                )
                st.success("已加入/更新。")

    with colR:
        st.markdown("#### 場次列表（全中文 / 隱藏 id）")
        st.dataframe(
            df(
                con,
                """
                SELECT
                    session_date AS 日期,
                    duration_min AS 總時長_分鐘,
                    theme        AS 主題,
                    created_at   AS 建立時間
                FROM sessions
                ORDER BY session_date DESC, session_id DESC;
                """,
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### 場次-項目（全中文 / 隱藏 id）")
        st.dataframe(
            df(
                con,
                f"""
                SELECT
                    s.session_date AS 日期,
                    s.theme        AS 主題,
                    sd.sequence_no AS 順序,
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
                    d.drill_name   AS 訓練項目,
                    sd.planned_minutes AS 預計分鐘,
                    sd.planned_reps    AS 預計次數
                FROM session_drills sd
                JOIN sessions s ON s.session_id = sd.session_id
                JOIN drills d ON d.drill_id = sd.drill_id
                ORDER BY s.session_date DESC, sd.sequence_no ASC;
                """,
            ),
            use_container_width=True,
            hide_index=True,
        )


# =========================
# Tab4：成效紀錄（drill_results）
# =========================
with tab4:
    st.markdown("#### 新增成效記錄（全中文 / 不顯示 id）")

    sessions = df(con, "SELECT session_id, session_date, duration_min, theme FROM sessions ORDER BY session_date DESC;")
    players = df(con, "SELECT player_id, name, position, grade_year FROM players ORDER BY name;")

    # 確保存在「本場次總結」drill（避免 drill_results.drill_id NOT NULL）
    summary_row = df(con, "SELECT drill_id FROM drills WHERE drill_name = '本場次總結' LIMIT 1;")
    if summary_row.empty:
        exec_one(
            con,
            f"INSERT INTO drills (drill_name, {DRILLS_TEXT_COL}, category, difficulty) VALUES (?, ?, ?, ?);",
            ("本場次總結", "場次/個人修正目標與觀察", "綜合", 1),
        )
        summary_row = df(con, "SELECT drill_id FROM drills WHERE drill_name = '本場次總結' LIMIT 1;")
    summary_drill_id = int(summary_row.iloc[0]["drill_id"])

    if sessions.empty or players.empty:
        st.info("請先新增至少一個場次與一個球員。")
    else:
        session_ids = sessions["session_id"].astype(int).tolist()
        session_label = {
            int(r.session_id): f"{r.session_date}｜{r.theme}（{int(r.duration_min)} 分）"
            for r in sessions.itertuples(index=False)
        }
        player_ids = players["player_id"].astype(int).tolist()
        player_label = {
            int(r.player_id): f"{r.name}（{(r.position or '').strip()} {(r.grade_year or '').strip()}）".strip()
            for r in players.itertuples(index=False)
        }

        sid = st.selectbox(
            "場次",
            options=session_ids,
            format_func=lambda x: session_label.get(int(x), str(x)),
            key="r_sid",
        )
        pid = st.selectbox(
            "球員",
            options=player_ids,
            format_func=lambda x: player_label.get(int(x), str(x)),
            key="r_pid",
        )

        focus_area = st.selectbox("面向", CATEGORY_OPTIONS_ZH, key="r_focus")

        main_target = st.text_input("常見錯誤/觀察點（可簡短）", key="r_target")
        correction_goal = st.text_input("修正目標（你希望下次做到什麼）", key="r_goal")
        success_rate = st.slider("成功率（%）", 0, 100, 64, key="r_rate")
        notes = st.text_area("備註（可選）", height=90, key="r_notes")

        if st.button("新增成效紀錄", key="r_add"):
            exec_one(
                con,
                """
                INSERT INTO drill_results
                (session_id, player_id, drill_id, focus_area, main_target, correction_goal, success_rate, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    int(sid),
                    int(pid),
                    int(summary_drill_id),
                    (focus_area or "").strip(),
                    (main_target or "").strip(),
                    (correction_goal or "").strip(),
                    int(success_rate),
                    (notes or "").strip(),
                ),
            )
            st.success("已新增。")

    st.markdown("---")
    st.markdown("#### 成效紀錄列表（全中文 / 隱藏 id）")
    st.dataframe(
        df(
            con,
            """
            SELECT
                s.session_date AS 日期,
                s.theme        AS 主題,
                p.name         AS 球員,
                r.focus_area   AS 面向,
                r.main_target  AS 常見錯誤,
                r.correction_goal AS 修正目標,
                r.success_rate AS 成功率_百分比,
                r.notes        AS 備註,
                r.created_at   AS 建立時間
            FROM drill_results r
            JOIN sessions s ON s.session_id = r.session_id
            JOIN players  p ON p.player_id  = r.player_id
            ORDER BY r.created_at DESC;
            """,
        ),
        use_container_width=True,
        hide_index=True,
    )


# =========================
# Tab5：分析（簡版）
# =========================
with tab5:
    st.markdown("#### 分析（全中文 / 隱藏 id）")

    st.markdown("##### 1) 各球員平均成功率（依面向）")
    st.dataframe(
        df(
            con,
            """
            SELECT
                p.name       AS 球員,
                r.focus_area AS 面向,
                ROUND(AVG(r.success_rate), 1) AS 平均成功率
            FROM drill_results r
            JOIN players p ON p.player_id = r.player_id
            GROUP BY p.name, r.focus_area
            ORDER BY p.name, r.focus_area;
            """,
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("##### 2) 最近 10 筆成效紀錄")
    st.dataframe(
        df(
            con,
            """
            SELECT
                s.session_date AS 日期,
                s.theme        AS 主題,
                p.name         AS 球員,
                r.focus_area   AS 面向,
                r.main_target  AS 常見錯誤,
                r.correction_goal AS 修正目標,
                r.success_rate AS 成功率_百分比
            FROM drill_results r
            JOIN sessions s ON s.session_id = r.session_id
            JOIN players  p ON p.player_id  = r.player_id
            ORDER BY r.created_at DESC
            LIMIT 10;
            """,
        ),
        use_container_width=True,
        hide_index=True,
    )
