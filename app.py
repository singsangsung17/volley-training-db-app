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
        st.dataframe(
    df(con, """
        SELECT
          name       AS 姓名,
          position   AS 位置,
          grade_year AS 年級,
          created_at AS 建立時間
        FROM players
        ORDER BY created_at DESC;
    """),
    use_container_width=True,
    hide_index=True,
)


# ---- Tab 2: Drills (修正過濾「本場次總結」與人數顯示) ----
with tab2:
    colL, colR = st.columns([1, 1])

    with colL:
        st.markdown("#### 新增訓練項目")
        drill_name = st.text_input("訓練項目名稱", key="d_name")
        
        # 分類選擇
        CATEGORY_OPTIONS = ["攻擊", "接發", "防守", "發球", "舉球", "攔網", "綜合"]
        category = st.selectbox("分類", options=CATEGORY_OPTIONS, key="d_category")

        # 人數需求
        num_people = st.number_input("建議人數", min_value=1, value=6, step=1, key="d_people")
        people_display = f"{num_people}人以上"
        st.info(f"目前設定：{people_display}")

        difficulty = st.slider("難度（1-5）", 1, 5, 3, key="d_diff")

        if st.button("新增訓練項目", key="d_add"):
            _name = (drill_name or "").strip()
            if not _name:
                st.error("訓練項目名稱不可為空。")
            else:
                exec_one(
                    con,
                    f"INSERT INTO drills (drill_name, {DRILLS_TEXT_COL}, category, difficulty) VALUES (?, ?, ?, ?);",
                    (_name, people_display, (category or "").strip(), int(difficulty)),
                )
                st.success(f"已新增項目：{_name}")
                st.rerun()

    with colR:
        st.markdown("#### 訓練項目列表")
        # 這裡加入 WHERE 來過濾掉 summary，並用 CASE 處理舊資料顯示問題
        st.dataframe(
            df(con, f"""
                SELECT 
                    difficulty AS 難度,
                    drill_name AS 訓練項目,
                    -- 如果原本存的是說明文字而不是「X人以上」，表格顯示「未設定」
                    CASE 
                        WHEN {DRILLS_TEXT_COL} LIKE '%人以上' THEN {DRILLS_TEXT_COL}
                        ELSE '未設定 (舊資料)' 
                    END AS 人數需求,
                    CASE 
                        WHEN category IN ('攻擊','接發','防守','發球','舉球','攔網','綜合') THEN category
                        WHEN category = 'attack_chain' THEN '攻擊'
                        WHEN category = 'serve_receive' THEN '接發'
                        WHEN category = 'defense' THEN '防守'
                        WHEN category = 'serve' THEN '發球'
                        WHEN category IN ('set','setting') THEN '舉球'
                        WHEN category IN ('block','blocking') THEN '攔網'
                        ELSE COALESCE(category, '')
                    END AS 類別
                FROM drills 
                WHERE category != 'summary' AND drill_name != '本場次總結' -- 這裡過濾掉系統用的總結項
                ORDER BY created_at DESC;
            """),
            use_container_width=True,
            hide_index=True
        )
        
# ---- Tab 3: Sessions (優化：自定義組次、單場顯示、時間統計) ----
with tab3:
    colL, colR = st.columns([1, 1.2]) # 稍微調寬右側比例

    # 1. 抓取場次清單
    sessions = df(con, "SELECT session_id, session_date, theme, duration_min FROM sessions ORDER BY session_date DESC, session_id DESC;")
    
    # 2. 抓取訓練項目 (排除總結項)
    drills = df(con, "SELECT drill_id, drill_name FROM drills WHERE category != 'summary' ORDER BY drill_name;")

    with colL:
        st.markdown("#### 場次操作")
        if sessions.empty:
            st.info("目前沒有場次。")
            selected_session_id = None
        else:
            session_ids = sessions["session_id"].tolist()
            session_label_map = {int(r.session_id): f"{r.session_date}｜{r.theme}" for r in sessions.itertuples(index=False)}
            
            # 選取目前正在操作的場次
            selected_session_id = st.selectbox(
                "選擇操作場次",
                options=session_ids,
                format_func=lambda sid: session_label_map.get(int(sid), str(sid)),
                key="t3_select_sid"
            )

        st.markdown("---")
        st.markdown("#### 將項目加入訓練流程")
        if selected_session_id and not drills.empty:
            drill_ids = drills["drill_id"].tolist()
            drill_label_map = {int(r.drill_id): r.drill_name for r in drills.itertuples(index=False)}
            
            sel_drill_id = st.selectbox("選擇項目", options=drill_ids, format_func=lambda did: drill_label_map.get(int(did), str(did)))
            
            # 自動計算下一個順序
            next_seq = con.execute("SELECT COALESCE(MAX(sequence_no), 0) + 1 FROM session_drills WHERE session_id=?;", (int(selected_session_id),)).fetchone()[0]
            
            c1, c2 = st.columns(2)
            with c1:
                seq = st.number_input("順序", min_value=1, value=int(next_seq))
                p_min = st.number_input("預計分鐘", min_value=0, value=20, step=5)
            with c2:
                # 【修改點 1】：改為文字輸入，讓你可以填 50*2
                p_sets = st.text_input("預計組次 (如: 50*2)", value="3")

            if st.button("加入流程", use_container_width=True):
                exec_one(con, """
                    INSERT OR REPLACE INTO session_drills (session_id, drill_id, sequence_no, planned_minutes, planned_reps) 
                    VALUES (?, ?, ?, ?, ?);
                """, (int(selected_session_id), int(sel_drill_id), int(seq), int(p_min), p_sets))
                st.success("已加入")
                st.rerun()

    with colR:
        st.markdown("#### 本場訓練流程清單")
        if selected_session_id:
            # 【修改點 2】：SQL 只抓取當前選中的 session_id
            current_drills_df = df(con, """
                SELECT 
                    sd.sequence_no AS 順序, 
                    d.drill_name AS 訓練項目,
                    sd.planned_minutes AS 分鐘, 
                    sd.planned_reps AS 預計組次
                FROM session_drills sd
                JOIN drills d ON d.drill_id = sd.drill_id
                WHERE sd.session_id = ?
                ORDER BY sd.sequence_no ASC;
            """, (int(selected_session_id),))

            if not current_drills_df.empty:
                # 【修改點 3】：計算總時間並增加「總計」列
                total_minutes = current_drills_df["分鐘"].sum()
                
                # 建立總計列
                total_row = pd.DataFrame({
                    "順序": [""],
                    "訓練項目": ["**總計時間**"],
                    "分鐘": [total_minutes],
                    "預計組次": [""]
                })
                
                # 合併表格
                display_df = pd.concat([current_drills_df, total_row], ignore_index=True)

                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
                st.info(f"💡 此場次目前規劃總時長：**{total_minutes}** 分鐘")
            else:
                st.warning("此場次尚未安排訓練項目。")
        
# ---- Tab 4: Results ----
with tab4:
    st.markdown("#### 新增成效記錄（drill_results）")

    sessions = df(con, "SELECT session_id, session_date, duration_min, theme FROM sessions ORDER BY session_date DESC;")
    players  = df(con, "SELECT player_id, name, position, grade_year FROM players ORDER BY name;")

    # 確保有「本場次總結」這個 drill（drill_results.drill_id 是 NOT NULL）
    summary_row = df(con, "SELECT drill_id FROM drills WHERE drill_name = '本場次總結' LIMIT 1;")
    if summary_row.empty:
        exec_one(
            con,
            f"INSERT INTO drills (drill_name, {DRILLS_TEXT_COL}, category, difficulty) VALUES (?, ?, ?, ?);",
            ("本場次總結", "場次/個人修正目標與觀察", "summary", 1),
        )
        summary_row = df(con, "SELECT drill_id FROM drills WHERE drill_name = '本場次總結' LIMIT 1;")
    summary_drill_id = int(summary_row.iloc[0]["drill_id"])

    # --- 面向 -> 常見錯誤（你可持續擴充） ---
    TARGETS_BY_FOCUS = {
        "攻擊": ["助跑節奏", "起跳時機", "未確實擺臂", "擊球點太低/太後", "攻擊點選擇", "線路控制不穩", "力量控制不當", "與舉球配合", "被攔原因（打點/線路/節奏）"],
        "接發": ["接發不到位", "平台角度不穩", "腳步不到位", "落點判斷慢", "手型不穩", "重心不穩", "溝通喊聲不足"],
        "防守": ["判斷慢", "移動腳步不到位", "站位錯（線/斜）", "手型/面向不對", "起球高度不足", "方向控制差", "補位慢"],
        "發球": ["發球失誤", "拋球不穩", "落點不準", "節奏不穩", "壓迫性不足", "力量/旋轉不足", "關鍵分心理波動"],
        "舉球": ["高度不穩", "太貼網/太離網", "節奏不對", "位置不到位", "配合不佳（攻手節奏）", "傳球選擇不佳"],
        "攔網": ["手型不對（封角度）", "起跳時機不對", "橫移慢跟不上", "漏人/判斷錯攔誰", "手未伸過網", "高度不足"],
        "綜合": ["專注度不足", "溝通不足", "輪轉/站位錯", "節奏感不穩", "體能不足", "連鎖失誤控制"],
    }

    def _session_label(r):
        s = (r.session_date or "").strip()
        mmdd = s[5:7] + "/" + s[8:10] if len(s) >= 10 else s
        theme = (getattr(r, "theme", "") or "").strip()
        dur = getattr(r, "duration_min", None)
        dur_txt = f"（{int(dur)}min）" if dur is not None and str(dur).strip() != "" else ""
        return f"{mmdd} {theme}{dur_txt}".strip() if theme else f"{mmdd}{dur_txt}".strip()

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

    def _infer_focus_from_session(sess_id: int) -> str:
        """
        透過「數據蒐集項目」推斷面向：
        1) 先看該場次 session_drills 連到 drills.category / drill_name
        2) 沒排 drills 時，用 sessions.theme 關鍵字 fallback
        """
        # 1) 從 session_drills + drills.category
        rows = df(
            con,
            """
            SELECT d.category, d.drill_name
            FROM session_drills sd
            JOIN drills d ON d.drill_id = sd.drill_id
            WHERE sd.session_id = ?
            """,
            (int(sess_id),),
        )

        text = ""
        if not rows.empty:
            cats = " ".join([(str(x) if x is not None else "") for x in rows["category"].tolist()])
            names = " ".join([(str(x) if x is not None else "") for x in rows["drill_name"].tolist()])
            text = (cats + " " + names)

        # 2) fallback 用 theme
        row2 = df(con, "SELECT theme FROM sessions WHERE session_id=? LIMIT 1;", (int(sess_id),))
        theme = "" if row2.empty else (row2.iloc[0]["theme"] or "")
        text2 = (text + " " + str(theme))

        # 關鍵字/類別判斷（可自行加強）
        if any(k in text2 for k in ["attack_chain", "攻擊"]):
            return "攻擊"
        if any(k in text2 for k in ["serve_receive", "接發", "一傳"]):
            return "接發"
        if any(k in text2 for k in ["defense", "防守"]):
            return "防守"
        if any(k in text2 for k in ["serve", "發球"]):
            return "發球"
        if any(k in text2 for k in ["set", "舉球", "二傳"]):
            return "舉球"
        if any(k in text2 for k in ["block", "攔網", "攔中"]):
            return "攔網"
        return "綜合"

    def _options_for_focus(focus: str) -> list[str]:
        base = TARGETS_BY_FOCUS.get(focus, TARGETS_BY_FOCUS.get("綜合", []))

        # 把「無（僅記錄）」放最後，確保不重複
        base2 = [x for x in base if x != "無（僅記錄）"]
        return base2 + ["其他（自行輸入）", "無（僅記錄）"]


    if sessions.empty or players.empty:
        st.info("先新增場次、球員。")
    else:
        # =========================
        # ❶ 控制器放在 form 外面：改了就會 rerun → 達成真正連動
        # =========================
        top1, top2, top3 = st.columns([1.4, 1.3, 1.3])

        with top1:
            session_map = {int(r.session_id): _session_label(r) for r in sessions.itertuples(index=False)}
            session_id = st.selectbox(
                "場次",
                options=list(session_map.keys()),
                format_func=lambda sid: session_map[sid],
                key="t4_session",
            )

        with top2:
            player_map = {int(r.player_id): _player_label(r) for r in players.itertuples(index=False)}
            player_id = st.selectbox(
                "球員",
                options=list(player_map.keys()),
                format_func=lambda pid: player_map[pid],
                key="t4_player",
            )

        # 推斷預設面向，並允許你手動「點選攻擊」
        inferred_focus = _infer_focus_from_session(int(session_id))
        with top3:
            focus = st.selectbox(
                "類別",
                options=["攻擊", "接發", "防守", "發球", "舉球", "攔網", "綜合"],
                index=["攻擊", "接發", "防守", "發球", "舉球", "攔網", "綜合"].index(inferred_focus),
                key="t4_focus",
            )

        # 依面向建立選項（主要/次要都用同一組）
        primary_options = _options_for_focus(focus)
        secondary_options = [x for x in primary_options if x not in ("無（僅紀錄）")]  # 次要不需要「無」

        # =========================
        # ❷ 提交區放在 form 內：避免重跑造成流程亂
        # =========================
        with st.form("t4_submit_form", clear_on_submit=False):
            c1, c2 = st.columns([1.3, 1.3])

            with c1:
                primary_choice = st.selectbox("主要修正目標（可選）", options=primary_options, key="t4_primary")

                primary_other = ""
                if primary_choice == "其他（自行輸入）":
                    primary_other = st.text_input("主要修正目標：其他（請輸入）", key="t4_primary_other")

            with c2:
                pass


            success_count = st.number_input("成功次數（可選）", min_value=0, value=0, step=1, key="t4_success")
            total_count   = st.number_input("總次數（可選）",   min_value=0, value=0, step=1, key="t4_total")

            # ✅ 成功率即時顯示（填完立刻看得懂）
            if total_count and total_count > 0:
                rate = success_count / total_count
                st.metric("成功率", f"{rate:.1%}", help=f"{success_count}/{total_count}")

            else:
                st.caption("成功率：—（請先填總次數 > 0）")

            # 次要修正目標：放在總次數之下、備註之上（照你要求）
            secondary_sel = st.multiselect(
                "次要修正目標（可複選）",
                options=secondary_options,
                default=[],
                key="t4_secondary",
            )

            secondary_other = ""
            if "其他（自行輸入）" in secondary_sel:
                secondary_other = st.text_input(
                    "次要修正目標：其他（可用逗號或頓號分隔）",
                    key="t4_secondary_other",
                )

            notes = st.text_area("備註（可選）", height=90, key="t4_notes")

            submitted = st.form_submit_button("新增成效記錄")

            if submitted:
                # 防呆：若總次>0 才檢查 success<=total；總次=0 代表純質性記錄，允許
                if total_count > 0 and success_count > total_count:
                    st.error("成功次數不能大於總次數。")
                else:
                    # 主要目標 resolve
                    if primary_choice == "無（僅紀錄）":
                        main_target = ""
                    elif primary_choice == "其他（自行輸入）":
                        main_target = (primary_other or "").strip()
                    else:
                        main_target = (primary_choice or "").strip()

                    # 次要目標 resolve（去掉占位「其他」並合併自由輸入）
                    sec_targets = [x for x in secondary_sel if x != "其他（自行輸入）"]
                    if (secondary_other or "").strip():
                        raw = secondary_other.replace("，", ",").replace("、", ",")
                        sec_targets += [t.strip() for t in raw.split(",") if t.strip()]

                    # 去重保序
                    seen = set()
                    uniq = []
                    for t in sec_targets:
                        if t and t not in seen:
                            uniq.append(t)
                            seen.add(t)

                    sec_prefix = f"[次要修正目標] {'、'.join(uniq)}" if uniq else ""
                    final_notes = (notes or "").strip()
                    if sec_prefix:
                        final_notes = sec_prefix if not final_notes else (sec_prefix + "\n" + final_notes)

                    exec_one(
                        con,
                        """
                        INSERT INTO drill_results
                        (session_id, drill_id, player_id, success_count, total_count, error_type, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            int(session_id),
                            int(summary_drill_id),
                            int(player_id),
                            int(success_count),
                            int(total_count),
                            main_target,      # 主修正目標 -> error_type
                            final_notes,      # 次要目標前綴 + 備註
                        ),
                    )
                    st.success("已新增。")
                    st.rerun()

    st.markdown("---")
    st.markdown("#### 成效記錄列表（最近 200 筆）")
    st.dataframe(
    df(con, """
        SELECT
            s.session_date AS 日期,
            s.theme        AS 場次主題,
            d.drill_name   AS 訓練項目,
            p.name         AS 球員,
            p.position     AS 位置,
            p.grade_year   AS 年級,
            r.success_count AS 成功次數,
            r.total_count   AS 總次數,
            CASE
                WHEN r.total_count=0 THEN NULL
                ELSE printf('%.1f%%', 100.0*r.success_count/r.total_count)
            END AS 成功率,
            r.error_type AS 主要修正目標,
            CASE
                WHEN r.notes LIKE '[次要修正目標] %' THEN
                    CASE
                        WHEN instr(r.notes, char(10)) > 0 THEN
                            substr(
                                r.notes,
                                length('[次要修正目標] ') + 1,
                                instr(r.notes, char(10)) - (length('[次要修正目標] ') + 1)
                            )
                        ELSE
                            substr(r.notes, length('[次要修正目標] ') + 1)
                    END
                ELSE NULL
            END AS 次要修正目標,
            r.recorded_at AS 記錄時間,
            r.notes       AS 備註
        FROM drill_results r
        JOIN sessions s ON s.session_id = r.session_id
        JOIN drills   d ON d.drill_id   = r.drill_id
        JOIN players  p ON p.player_id  = r.player_id
        ORDER BY r.recorded_at DESC
        LIMIT 200;
    """),
    use_container_width=True,
    hide_index=True,
)


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


 
