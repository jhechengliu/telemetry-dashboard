# 電池組監控儀表板 — 即時 CAN 數據顯示（中文版）

## 專案簡介

本專案提供一個即時網頁儀表板，用於監控電池組數據。系統使用 Flask 與 Flask-SocketIO 來接收、解碼並即時顯示數據，支援監控 10 個電池組，每個電池組包含 12 個電壓讀數和 5 個溫度感測器，並提供可折疊的 UI 介面以更好地組織數據。

---

## 目錄

1. [系統架構](#系統架構)  
2. [主要功能](#主要功能)  
3. [專案結構](#專案結構)  
4. [安裝說明](#安裝說明)  
5. [執行方式](#執行方式)  
6. [CAN 訊號對應設定 (`can_map.json`)](#can-訊號對應設定-can_mapjson)  
7. [虛擬 CAN 發送器](#虛擬-can-發送器)  
8. [擴充儀表板](#擴充儀表板)  
9. [常見問題](#常見問題)  

---

## 1. 系統架構

```
[UDP 監聽執行緒] ──> [Flask + SocketIO] ──> [瀏覽器儀表板]
```

- UDP 封包包含電池組的 CAN 訊息
- Flask 執行緒負責監聽 UDP 封包
- 解析後的數值透過 WebSocket (Socket.IO) 即時推送到前端
- 儀表板 UI 會即時更新
- 數據以可折疊的電池組形式組織

---

## 2. 主要功能

- **電池組監控**：10 個電池組，每組 12 個電壓和 5 個溫度讀數
- **可折疊介面**：可展開/收合電池組以更好地組織數據
- **即時更新**：WebSocket 無需輪詢
- **彈性訊號解析**：可自訂 `can_map.json`
- **內建模擬器**：方便離線測試
- **依賴簡單**：Flask、Flask-SocketIO、Eventlet
- **行動裝置友善**：響應式設計

---

## 3. 專案結構

```
telemetry-dashboard/
│
├── app.py                 # 主程式
├── can_map.json           # CAN 訊號對應設定
├── udp_can_sender.py      # 虛擬 CAN 發送器
│
├── templates/
│   └── index.html         # 前端 UI
│
└── static/
    ├── css/
    │   └── style.css      # 樣式表
    └── js/
        └── main.js        # 前端 JavaScript 程式碼
```

---

## 4. 安裝說明

### 需求
- Python 3.7+
- pip

### 安裝步驟

```bash
# 複製或解壓縮專案資料夾
cd telemetry-dashboard

# (選擇性) 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安裝必要套件
pip install flask flask-socketio eventlet
```

---

## 5. 執行方式

### 啟動 Flask 伺服器
```bash
python3 app.py
```

### 開啟瀏覽器
```
http://localhost:5001
```

您將看到一個包含以下內容的儀表板：
- 10 個可折疊的電池組
- 每組 12 個電壓讀數
- 每組 5 個溫度讀數
- 連接狀態和統計資訊

### （可選）啟動模擬器
```bash
python3 udp_can_sender.py
```

---

## 6. CAN 訊號對應設定 (`can_map.json`)

`can_map.json` 定義了電池數據的 CAN 訊息結構。例如：

```json
{
  "0x12905301": {
    "name": "CV1",
    "description": "Cell Voltages 1-3",
    "signals": [
      {
        "name": "pack_id",
        "start": 0,
        "length": 1
      },
      {
        "name": "cell_1",
        "start": 2,
        "length": 2,
        "unit": "mV"
      }
    ]
  }
}
```

### 欄位說明：
| 欄位      | 說明                                      |
|-----------|------------------------------------------|
| `name`    | 訊號名稱（用於 HTML 元素 ID）             |
| `start`   | CAN 資料中的位元組偏移量                  |
| `length`  | 此訊號使用的位元組數                      |
| `scale`   | 原始值的乘數                              |
| `unit`    | 儀表板顯示的單位                          |

**注意**：所有值都假設為小端序的無符號整數。

---

## 7. 虛擬 CAN 發送器

`udp_can_sender.py` 用於模擬電池數據進行測試：
- 產生真實的電壓和溫度值
- 模擬 10 個電池組
- 可設定發送速率
- 支援命令列配置

使用方式：
```bash
python3 udp_can_sender.py [--ip IP] [--port PORT] [--rate RATE] [--boards BOARD_IDS]
```

---

## 8. 擴充儀表板

### 新增訊號：
1. 編輯 `can_map.json` 新增 CAN ID 和訊號
2. 更新 `static/js/main.js` 中的前端 JavaScript
3. 在 `templates/index.html` 中新增對應的 UI 元素
4. 重新啟動伺服器：
```bash
python3 app.py
```

---

## 9. 常見問題

| 問題 | 解決方式 |
|------|----------|
| 1234 埠被佔用 | 修改 `