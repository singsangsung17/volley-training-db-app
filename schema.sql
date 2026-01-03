PRAGMA foreign_keys = ON;

-- 1. 基礎資料表 (Independent Tables)
CREATE TABLE IF NOT EXISTS players (
  player_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT NOT NULL,
  jersey_number INTEGER,
  position      TEXT,
  grade_year    TEXT,
  notes         TEXT,    -- 新增：備註欄位
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  session_date  TEXT NOT NULL, 
  duration_min  INTEGER,
  theme         TEXT,
  notes         TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS drills (
  drill_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  drill_name    TEXT NOT NULL,
  objective     TEXT,
  category      TEXT,
  difficulty    INTEGER, 
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 2. 關聯與紀錄表 (Dependent / Junction Tables)
CREATE TABLE IF NOT EXISTS session_drills (
  session_id      INTEGER NOT NULL,
  drill_id        INTEGER NOT NULL,
  sequence_no     INTEGER NOT NULL,
  planned_minutes INTEGER,
  planned_reps    INTEGER,
  PRIMARY KEY (session_id, drill_id, sequence_no),
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
  FOREIGN KEY (drill_id)   REFERENCES drills(drill_id)   ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS drill_results (
  result_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id     INTEGER NOT NULL,
  drill_id       INTEGER NOT NULL,
  player_id      INTEGER NOT NULL,
  success_count  INTEGER NOT NULL DEFAULT 0,
  total_count    INTEGER NOT NULL DEFAULT 0,
  error_type     TEXT,
  recorded_at    TEXT NOT NULL DEFAULT (datetime('now')),
  notes          TEXT,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
  FOREIGN KEY (drill_id)   REFERENCES drills(drill_id)     ON DELETE CASCADE,
  FOREIGN KEY (player_id)  REFERENCES players(player_id)   ON DELETE CASCADE
);

-- 【新加入的位置】
CREATE TABLE IF NOT EXISTS attendance (
    session_id  INTEGER NOT NULL,
    player_id   INTEGER NOT NULL,
    status      TEXT NOT NULL, -- 出席, 請假, 遲到, 缺席
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (session_id, player_id),
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE,
    FOREIGN KEY (player_id)  REFERENCES players (player_id)  ON DELETE CASCADE
);

-- 3. 索引 (Indexes)
CREATE INDEX IF NOT EXISTS idx_results_session ON drill_results(session_id);
CREATE INDEX IF NOT EXISTS idx_results_player  ON drill_results(player_id);
CREATE INDEX IF NOT EXISTS idx_results_drill   ON drill_results(drill_id);
-- 如果你之後常查詢出席率，也可以考慮加這個索引
CREATE INDEX IF NOT EXISTS idx_attendance_session ON attendance(session_id);
