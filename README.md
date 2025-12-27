# 排球訓練知識庫（最小可用版）

這是一個示範用的「可運行」作品：SQLite + Streamlit。

## 你會得到什麼
- ERD/SQL 對應的資料庫 schema（schema.sql）
- 示例資料（seed_data.sql）
- 可操作介面（app.py）：新增球員/訓練/訓練項目/成效紀錄，並提供常見分析查詢

## 如何在本機跑起來（Windows / macOS 都可）
1) 安裝 Python 3.10+（已安裝可略）
2) 進到此資料夾後安裝套件：
   ```bash
   pip install -r requirements.txt
   ```
3) 啟動：
   ```bash
   streamlit run app.py
   ```

第一次啟動會自動建立 `volley_training.db` 並灌入示例資料。

## 書審用法（建議）
- 跑起來後截圖：新增資料畫面 + 分析頁（SQL 結果）
- 放到「其他有利審查資料」：證明你不只做設計圖，而是能把系統跑起來
