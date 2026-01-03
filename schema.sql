PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS players (
  player_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT NOT NULL,
  jersey_number INTEGER, -- 背號
  position      TEXT,
  grade_year    TEXT,
  notes         TEXT,    -- 備註
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  session_date  TEXT NOT NULL, 
  theme         TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS drills (
  drill_id           INTEGER PRIMARY KEY AUTOINCREMENT,
  drill_name         TEXT NOT NULL,
  category           TEXT,
  min_players        INTEGER,
  neuromuscular_load INTEGER, -- 替換原本的 difficulty
  is_hidden          INTEGER DEFAULT 0,
  objective          TEXT,
  notes              TEXT,
  created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS attendance (
    session_id  INTEGER NOT NULL,
    player_id   INTEGER NOT NULL,
    status      TEXT NOT NULL, -- 出席, 請假, 遲到, 缺席
    PRIMARY KEY (session_id, player_id),
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE,
    FOREIGN KEY (player_id)  REFERENCES players (player_id)  ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS session_drills (
  session_id      INTEGER NOT NULL,
  drill_id        INTEGER NOT NULL,
  sequence_no     INTEGER NOT NULL,
  planned_minutes INTEGER,
  planned_reps    TEXT,
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
  notes          TEXT,
  recorded_at    TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
  FOREIGN KEY (drill_id)   REFERENCES drills(drill_id)     ON DELETE CASCADE,
  FOREIGN KEY (player_id)  REFERENCES players(player_id)   ON DELETE CASCADE
);
