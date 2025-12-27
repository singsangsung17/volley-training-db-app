
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS players (
  player_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT NOT NULL,
  position      TEXT,
  grade_year    TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  session_date  TEXT NOT NULL, -- YYYY-MM-DD
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
  difficulty    INTEGER, -- 1-5
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- A training session can have multiple drills; a drill can appear in multiple sessions.
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

-- Records performance for a player in a drill during a session.
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

CREATE INDEX IF NOT EXISTS idx_results_session ON drill_results(session_id);
CREATE INDEX IF NOT EXISTS idx_results_player  ON drill_results(player_id);
CREATE INDEX IF NOT EXISTS idx_results_drill   ON drill_results(drill_id);
