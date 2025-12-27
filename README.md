# 排球訓練知識庫（最小可用版｜SQLite × Streamlit）

這是一個**可運行的資料系統作品**：以關聯式資料庫（SQLite）將排球訓練資料結構化，並透過 Streamlit 提供可操作的新增/查詢/分析介面。  
重點不是概念，而是把 **ERD → schema → 可操作系統 → SQL 分析**完整落地。

> Demo（雲端）：（部署後補上 Streamlit Cloud 連結）  
> 證據建議：README 下方的 **「書審截圖建議」** 兩張圖即可快速驗證

---

## 作品亮點（審查重點）
- **資料庫落地**：ERD 對應 schema（外鍵/關聯表/正規化概念可驗證）
- **可操作系統**：不只設計圖，提供可輸入資料的 UI（新增球員/場次/訓練/成效）
- **可驗證分析**：內建多個 SQL 查詢頁，能輸出訓練量、瓶頸、趨勢與失誤統計

---

## 資料模型（ERD 對應）
主要表（以關聯式模型實作）：
- `players`：球員資料  
- `sessions`：訓練場次（日期、主題、時長）  
- `drills`：訓練項目（分類、難度、目的）  
- `session_drills`：場次與訓練項目的多對多關聯  
- `drill_results`：每位球員在某次場次、某個訓練項目的成效紀錄  

---

## 專案檔案結構
- `app.py`：Streamlit 操作介面（新增/列表/分析）
- `schema.sql`：資料庫建表與索引（ERD 落地）
- `seed_data.sql`：示例資料（第一次啟動自動灌入）
- `requirements.txt`：Python 套件需求

---

## 本機啟動（Windows / macOS）
1) 安裝 Python：建議 Python 3.11+（3.10 以上可用）

2) 安裝套件（在專案資料夾內）
```bash
pip install -r requirements.txt
