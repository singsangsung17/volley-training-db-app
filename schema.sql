-- 開啟外鍵約束
PRAGMA foreign_keys = ON;

-- 1. 球員名單 (Players)
CREATE TABLE IF NOT EXISTS players (
    player_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    jersey_number INTEGER, -- 背號
    position      TEXT,    -- 位置 (主攻/舉球/攔中等)
    grade_year    TEXT,    -- 年級
    notes         TEXT,    -- 個人備註 (傷病史、特質)
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 2. 訓練場次 (Sessions)
-- 增加 phase 欄位以支援週期化規劃 (基礎/強化/巔峰/恢復)
CREATE TABLE IF NOT EXISTS sessions (
    session_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    session_date  TEXT NOT NULL, 
    theme         TEXT, -- 訓練主題
    phase         TEXT DEFAULT '基礎期', -- 賽季相位 (週期化理論核心)
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 3. 訓練項目庫 (Drills)
-- 欄位名稱由 difficulty 替換為 neuromuscular_load (神經負荷)
CREATE TABLE IF NOT EXISTS drills (
    drill_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    drill_name         TEXT NOT NULL,
    category           TEXT,    -- 技術類別 (發球/接球/攻擊等)
    min_players        INTEGER, -- 最少需求人數
    neuromuscular_load INTEGER, -- 神經負荷評分 (1-5)
    is_hidden          INTEGER DEFAULT 0, -- 0:顯示, 1:隱藏
    objective          TEXT,    -- 訓練重點 (神經募集、技術修正等)
    notes              TEXT,    -- 操作說明或備註
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 4. 出缺席紀錄 (Attendance)
CREATE TABLE IF NOT EXISTS attendance (
    session_id INTEGER NOT NULL,
    player_id  INTEGER NOT NULL,
    status     TEXT NOT NULL, -- 出席, 請假, 遲到, 缺席
    PRIMARY KEY (session_id, player_id),
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE,
    FOREIGN KEY (player_id)  REFERENCES players (player_id)  ON DELETE CASCADE
);

-- 5. 場次流程排程 (Session Drills)
CREATE TABLE IF NOT EXISTS session_drills (
    session_id      INTEGER NOT NULL,
    drill_id        INTEGER NOT NULL,
    sequence_no     INTEGER NOT NULL, -- 練習順序
    planned_minutes INTEGER, -- 預計分鐘
    planned_reps    TEXT,    -- 預計組次/量
    PRIMARY KEY (session_id, drill_id, sequence_no),
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE,
    FOREIGN KEY (drill_id)   REFERENCES drills (drill_id)   ON DELETE CASCADE
);

-- 6. 訓練成效紀錄 (Drill Results)
CREATE TABLE IF NOT EXISTS drill_results (
    result_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    INTEGER NOT NULL,
    drill_id      INTEGER NOT NULL,
    player_id     INTEGER NOT NULL,
    success_count INTEGER NOT NULL DEFAULT 0,
    total_count   INTEGER NOT NULL DEFAULT 0,
    error_type    TEXT, -- 主要失誤原因
    notes         TEXT, -- 教練即時觀察
    recorded_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE,
    FOREIGN KEY (drill_id)   REFERENCES drills (drill_id)   ON DELETE CASCADE,
    FOREIGN KEY (player_id)  REFERENCES players (player_id)  ON DELETE CASCADE
);
