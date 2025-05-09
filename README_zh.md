# Telemetry Dashboard — 即時 CAN 數據儀表板（中文版）

## 專案簡介

本專案提供一個即時網頁儀表板，用於監控 ESP32 透過 UDP 傳送的 CAN 匯流排數據。系統使用 Flask 與 Flask-SocketIO 來接收、解碼並即時顯示數據，支援彈性的 JSON 訊號對應設定，並可用內建模擬器進行測試。

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
ESP32 (CAN → UDP) ──> [UDP 監聽執行緒] ──> [Flask + SocketIO] ──> [瀏覽器儀表板]
```

- ESP32 讀取 CAN 訊息並透過 UDP 傳送。
- Flask 執行緒負責監聽 UDP 封包。
- 解析後的數值透過 WebSocket (Socket.IO) 即時推送到前端。
- 儀表板 UI 會即時更新。

---

## 2. 主要功能

- **即時更新**：WebSocket 無需輪詢。
- **彈性訊號解析**：可自訂 `can_map.json`。
- **內建模擬器**：方便離線測試。
- **依賴簡單**：Flask、Flask-SocketIO、Eventlet。
- **行動裝置友善**。

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
    └── style.css          # 樣式表
```

---

## 4. 安裝說明

### 需求
- Python 3.7+
- pip

### 安裝步驟

```bash
cd telemetry-dashboard
python3 -m venv venv
source venv/bin/activate
pip install flask flask-socketio eventlet
```

---

## 5. 執行方式

### 啟動 Flask 伺服器
```bash
python app.py
```

### 開啟瀏覽器
```
http://localhost:5000
```

### （可選）啟動模擬器
```bash
python udp_can_sender.py
```

---

## 6. CAN 訊號對應設定 (`can_map.json`)

`can_map.json` 允許你自訂 CAN ID 與資料格式。例如：

```json
{
  "0x100": {
    "signals": [
      { "name": "highest_temp", "start": 0, "length": 2, "scale": 0.1, "unit": "°C" },
      { "name": "lowest_temp",  "start": 2, "length": 2, "scale": 0.1, "unit": "°C" }
    ]
  }
}
```

---

## 7. 虛擬 CAN 發送器

`udp_can_sender.py` 會隨機產生數據並以 UDP 格式發送，方便測試。

---

## 8. 擴充儀表板

1. 編輯 `can_map.json` 新增訊號。
2. 在 `index.html` 增加對應欄位。
3. 重新啟動伺服器。

---

## 9. 常見問題

| 問題 | 解決方式 |
|------|----------|
| 1234 埠被佔用 | 修改 `app.py` 的 UDP 埠 |
| 儀表板無數據 | 確認 ESP32 或模擬器有發送資料 |
| 前端無即時更新 | 檢查瀏覽器 Console 是否有錯誤 |
| 啟動時缺少模組 | 請先啟動虛擬環境並安裝依賴 |

---

## 聯絡方式

開發者：[你的名字/團隊]  
聯絡信箱：[your.email@example.com] 