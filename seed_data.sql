
PRAGMA foreign_keys = ON;

-- Seed players
INSERT INTO players (name, position, grade_year) VALUES
('A 球員','主攻','大二'),
('B 球員','舉球','大二'),
('C 球員','自由','大一'),
('D 球員','副攻','大三'),
('E 球員','主攻','大一');

-- Seed drills
INSERT INTO drills (drill_name, objective, category, difficulty) VALUES
('接發到位訓練','提升接發到位率','serve_receive',3),
('防守落點反應','提升防守反應與移動','defense',4),
('攻擊鏈串連','提升一傳→舉球→攻擊連貫','attack_chain',4),
('發球穩定度','降低發球失誤','serve',2);

-- Seed sessions
INSERT INTO sessions (session_date, duration_min, theme, notes) VALUES
(date('now','-14 day'), 120, '接發與防守', '週中基礎強化'),
(date('now','-7 day'),  120, '攻擊鏈',     '攻擊節奏與配合'),
(date('now'),          120, '整合回合',     '串連與情境演練');

-- Link session drills (sequence_no)
INSERT INTO session_drills (session_id, drill_id, sequence_no, planned_minutes, planned_reps) VALUES
(1, 1, 1, 25, 60),
(1, 2, 2, 30, 50),
(1, 4, 3, 20, 40),

(2, 1, 1, 20, 50),
(2, 3, 2, 35, 60),
(2, 4, 3, 15, 30),

(3, 2, 1, 25, 50),
(3, 3, 2, 35, 70),
(3, 4, 3, 15, 30);

-- Seed some results (session_id, drill_id, player_id, success_count, total_count, error_type)
INSERT INTO drill_results (session_id, drill_id, player_id, success_count, total_count, error_type, notes) VALUES
(1, 1, 1, 42, 60, '接球不到位', '一傳偏飄'),
(1, 1, 2, 50, 60, '判斷慢',     ''),
(1, 1, 3, 55, 60, '',           '穩定'),
(1, 2, 1, 30, 50, '腳步不到位', ''),
(1, 2, 3, 38, 50, '判斷慢',     ''),
(1, 4, 2, 34, 40, '發球失誤',   ''),

(2, 3, 1, 40, 60, '揮臂時機',   ''),
(2, 3, 2, 45, 60, '托球高度',   ''),
(2, 3, 4, 35, 60, '起跳節奏',   ''),
(2, 4, 5, 22, 30, '發球失誤',   ''),

(3, 3, 1, 48, 70, '揮臂時機',   ''),
(3, 3, 2, 52, 70, '托球高度',   ''),
(3, 2, 3, 40, 50, '判斷慢',     ''),
(3, 4, 4, 26, 30, '發球失誤',   '');
