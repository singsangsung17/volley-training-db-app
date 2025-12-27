PRAGMA foreign_keys = ON;

-- Seed players
INSERT INTO players (name, position, grade_year) VALUES
('A 球員','主攻','大二'),
('B 球員','舉球','大二'),
('C 球員','自由','大一'),
('D 球員','副攻','大三'),
('E 球員','攔中','大一'),
('F 球員','主攻','大一');

-- Seed drills
INSERT INTO drills (drill_name, objective, category, difficulty) VALUES
('接發到位訓練','提升接發到位率','serve_receive',3),
('防守落點反應','提升防守反應與移動','defense',4),
('攻擊鏈串連','提升一傳→舉球→攻擊連貫','attack_chain',4),
('發球穩定度','降低發球失誤、提升壓迫性','serve',3);

-- Seed sessions
INSERT INTO sessions (session_date, duration_min, theme, notes) VALUES
('2025-12-01', 90, '接發與防守', '以接發到位與防守反應為主'),
('2025-12-08', 95, '攻擊鏈串連', '提升攻擊鏈連貫與發球壓迫'),
('2025-12-15', 85, '綜合訓練', '綜合強化與小對抗');

-- Map drills into sessions
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

-- Seed some results (session_id, drill_id, player_id, success_count, total_count, error_type, notes)
INSERT INTO drill_results (session_id, drill_id, player_id, success_count, total_count, error_type, notes) VALUES
(1, 1, 1, 48, 60, '接發不到位', '需提升穩定度'),
(1, 1, 2, 50, 60, '',           '穩定'),
(1, 2, 1, 30, 50, '腳步不到位', ''),
(1, 2, 3, 35, 50, '判斷慢',     ''),

(2, 3, 1, 40, 60, '攻擊點選擇', ''),
(2, 3, 2, 45, 60, '',           '配合佳'),
(2, 4, 4, 24, 30, '發球失誤',   ''),

(3, 2, 1, 32, 50, '腳步不到位', ''),
(3, 3, 2, 50, 70, '舉球高度',   ''),
(3, 4, 4, 26, 30, '發球失誤',   '');
