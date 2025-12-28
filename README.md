# VolleyData | 排球訓練科學化管理與數據分析系統

以 **Streamlit + SQLite** 實作的排球訓練管理與數據分析系統：支援球員/訓練項目/訓練場次管理，並可在場邊用「成功/失誤」按鈕快速記錄訓練成效，最後以儀表板呈現全隊與個人表現指標，協助訓練科學化與可追蹤化。

---

## Features
- **球員管理**：新增球員（姓名/位置/年級）並查看列表
- **訓練項目管理**：新增訓練項目（分類/難度/建議人數）並查看列表
- **訓練場次管理**：新增場次（日期/主題），為該場次建立訓練流程（順序/分鐘/組次）
- **現場成效紀錄**：選擇場次+球員+訓練項目，用大按鈕即時計數成功/失誤，顯示成功率並可寫入資料庫
- **分析儀表板（SQL）**：全隊 KPI、個人技術雷達圖、趨勢圖、訓練佔比與失誤主因分析

---

## Tech Stack
- Python
- Streamlit（Web UI）
- SQLite（本機資料庫）
- Pandas（資料處理）
- Plotly Express（視覺化）

---

## Project Structure (expected)
> 專案會使用 `schema.sql` 建表、`seed_data.sql` 灌入示例資料，並建立 `volley_training.db` 作為 SQLite 資料庫檔案。

.
├─ app.py # Streamlit 主程式（若你的檔名不同，請以實際檔名為準）
├─ schema.sql # 建表 SQL（必備）
├─ seed_data.sql # 示例資料 SQL（必備）
├─ volley_training.db # SQLite DB（首跑自動生成；可重置）
└─ README.md

---

## Quick Start

### 1) Create venv (recommended)
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

2) Install dependencies
pip install streamlit pandas plotly
3) Run
streamlit run app.py
Database Initialization & Reset

首次啟動：若 volley_training.db 不存在，系統會自動建立資料庫並灌入 seed_data.sql。

每次啟動：系統會確保 schema.sql 已套用（避免缺表）。

側邊欄重置為示例資料：會刪除現有 volley_training.db，重新建表並灌入 seed。

Notes

本專案為 單機 SQLite 模式：資料儲存在 volley_training.db。

若部署在部分雲端環境（檔案系統可能不持久化），建議改用外部資料庫或加入匯出/備份機制。

drills 表描述欄位支援 purpose 或 objective 其一（程式會自動偵測），若兩者皆無可能導致頁面中止。

Roadmap (optional)

帳號/權限（隊長、教練、球員）與多隊伍資料分區

CSV 匯出/匯入與自動週報

更完整的技術鏈路（如接發/攻擊鏈）資料模型與儀表板
