with colL:
st.markdown("#### 新增球員")
name = st.text_input("姓名", key="p_name")
        position = st.text_input("位置（例：主攻/舉球/自由/副攻/攔中）", key="p_pos")
        grade_year = st.text_input("年級（例：大一/大二）", key="p_grade")
        if st.button("新增球員", key="p_add"):
            if not name.strip():
                st.error("姓名必填。")
            else:
                exec_one(con, "INSERT INTO players (name, position, grade_year) VALUES (?, ?, ?);",
                         (name.strip(), position.strip(), grade_year.strip()))
                st.success("已新增。")

# 位置改成下拉選單（書審展示更專業、也防止亂填）
POS_OPTIONS = ["主攻", "副攻", "攔中", "舉球", "自由"]
position = st.selectbox("位置", POS_OPTIONS, index=0, key="p_pos")

grade_year = st.text_input("年級（例：大一/大二）", key="p_grade")

if st.button("新增球員", key="p_add"):
    if not name.strip():
        st.error("姓名必填。")
    else:
        exec_one(
            con,
            "INSERT INTO players (name, position, grade_year) VALUES (?, ?, ?);",
            (name.strip(), position, grade_year.strip())
        )
        st.success("已新增。")
        st.rerun()

with colR:
st.markdown("#### 球員列表")
st.dataframe(df(con, "SELECT player_id, name, position, grade_year, created_at FROM players ORDER BY player_id DESC;"),
@@ -146,10 +156,28 @@ def reset_to_seed():
if sessions.empty or drills.empty:
st.info("先新增至少一個場次與一個訓練項目。")
else:
            session_id = st.selectbox("選擇場次", sessions.apply(lambda r: f"{r.session_id}｜{r.session_date}｜{r.theme}", axis=1))
            session_id = int(session_id.split("｜")[0])
            drill_id = st.selectbox("選擇訓練項目", drills.apply(lambda r: f"{r.drill_id}｜{r.drill_name}", axis=1))
            drill_id = int(drill_id.split("｜")[0])
         session_map = {
    int(r.session_id): f"{r.session_date}｜{(r.theme or '（無主題）')}"
    for r in sessions.itertuples(index=False)
}
drill_map = {int(r.drill_id): f"{r.drill_name}" for r in drills.itertuples(index=False)}

session_id = st.selectbox(
    "選擇場次",
    options=list(session_map.keys()),
    format_func=lambda sid: f"{sid}｜{session_map[sid]}",
)

drill_id = st.selectbox(
    "選擇訓練項目",
    options=list(drill_map.keys()),
    format_func=lambda did: f"{did}｜{drill_map[did]}",
)

format_func=lambda sid: session_map[sid]
format_func=lambda did: drill_map[did]


sequence_no = st.number_input("順序（sequence_no）", min_value=1, value=1, step=1)
planned_minutes = st.number_input("預計分鐘（可選）", min_value=0, value=20, step=5)
planned_reps = st.number_input("預計次數（可選）", min_value=0, value=50, step=5)
