# HouseLens - 台灣全網房產數據終端 (CLI Engine)

HouseLens 是一個以 CLI 為核心的非同步房產數據聚合引擎，以實體與刊登解耦、模組自主數據正規化（Anti-Corruption Layer）、純數值消歧去重為架構基礎，整合各大房產平台（首發 591）提供標準化強型別資料管理與終端檢索。

---

## 快速開始

### 1. 安裝與環境同步
專案基於 Python 3.12+ 與 `uv` 工具鏈：
```bash
uv sync
```

### 2. 執行自動化測試
全套 44 項單元與整合測試（含 591 即時 API 整合測試）：
```bash
uv run pytest tests/ -v
```

---

## 全域旗標 (Global Options)

全域旗標可搭配任意指令使用：

| 選項 | 簡寫 | 類型 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- | :--- |
| `--db-path` | - | Path | `./houselens.db` | 自訂 SQLite 資料庫路徑（支援環境變數 `HOUSELENS_DB_PATH`） |
| `--debug` | - | Flag | `False` | 啟用除錯模式，印出完整例外追蹤堆疊 |
| `--version` | `-v` | Flag | - | 顯示 CLI 版本資訊 |
| `--help` | - | Flag | - | 顯示說明手冊 |

---

## CLI 指令手冊

### 1. 來源外掛模組 (provider)

管理與檢測各房產平台來源外掛。

#### 參數選項

| 指令 | 參數 / 選項 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- |
| `houselens provider list` | `-f, --format <text\|json>` | `text` | 輸出格式：彩色終端表格或 JSON 格式 |
| `houselens provider check [PROVIDER_ID]` | `PROVIDER_ID` (可選) | `591` | 即時發送測試封包量測連線延遲毫秒數（Latency） |

#### 常用範例

```bash
# 檢視已安裝來源外掛
uv run houselens provider list

# 量測指定來源連線延遲
uv run houselens provider check 591
```

---

### 2. 資料庫維護 (db)

本機 SQLite 資料庫結構維護與狀態檢測。

#### 參數選項

| 指令 | 參數 / 選項 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- |
| `houselens db init` | - | - | 初始化資料庫結構，建立所有實體資料表 |
| `houselens db stats` | `-f, --format <text\|json>` | `text` | 檢視庫存數量、刊登歸戶數與去重比例儀表板 |
| `houselens db vacuum` | - | - | 執行 SQLite 磁碟空間重整與最佳化 |

#### 常用範例

```bash
uv run houselens db init
uv run houselens db stats
uv run houselens db vacuum
```

---

### 3. 數據同步流水線 (sync)

從外部平台擷取資料，各來源模組自主將封包清洗為標準強型別數值，由核心流水線執行純數值消歧去重並入庫。支援進度指示、速率計算與增量更新。

#### 參數選項

| 適用子指令 | 選項 | 簡寫 | 類型 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 全部 | `--provider` | `-p` | string | `591` | 來源外掛代碼 |
| 全部 | `--region-id` | `-r` | int | `1` | 縣市代碼（1: 台北市, 3: 新北市...） |
| 全部 | `--details` | `-d` | flag | `False` | 深入爬取規格詳情（公設、主建坪拆解、建商團隊） |
| 全部 | `--limit` | `-l` | int | None | 同步筆數上限 |
| 全部 | `--format` | `-f` | string | `text` | 輸出格式：`text` 或 `json` |
| `community`, `sale`, `newhouse` | `--keyword` | `-k` | string | None | 名稱、社區或路名關鍵字 |
| `community`, `sale` | `--min-age` | - | float | None | 最小屋齡（年） |
| `community`, `sale` | `--max-age` | - | float | None | 最大屋齡（年） |
| `sale` | `--min-price` | - | int | None | 最低總價（萬元） |
| `sale` | `--max-price` | - | int | None | 最高總價（萬元） |
| `sale` | `--rooms` | - | int | None | 格局房數篩選（純整數） |
| `newhouse` | `--status` | `-s` | string | `1,2` | 銷售狀態（1: 預售屋, 2: 新成屋） |

子指令涵蓋：`community`（社區）、`sale`（中古屋）、`newhouse`（新建案）、`all`（一鍵同步全領域）。

#### 常用範例

```bash
# 依總價、屋齡（10年以下）與房數（3房）同步台北市中古屋（自動去重合併，並深入拆解產權坪數）
uv run houselens sync sale -r 1 --max-age 10 --rooms 3 --min-price 2000 --max-price 5000 --details -l 20

# 依屋齡區間與關鍵字搜尋社區並同步完整公設清單與建商詳情
uv run houselens sync community -r 1 -k "鳴森大苑" --max-age 5 --details

# 同步預售屋建案及其 layout_v2 結構化房型坪數規劃
uv run houselens sync newhouse -r 1 -s 1 --details -l 10

# 一鍵同步指定縣市三大領域資料
uv run houselens sync all -r 1 -l 10 --details
```

---

### 4. 本地庫存檢索 (list)

檢索本機資料庫庫存實體與刊登記錄。

#### 參數選項

| 適用子指令 | 選項 | 簡寫 | 類型 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 全部 | `--region` | `-r` | string | None | 縣市名稱（例：台北市） |
| 全部 | `--section` | `-s` | string | None | 行政區名稱（例：松山區） |
| 全部 | `--keyword` | `-k` | string | None | 標題、社區或建案名稱關鍵字 |
| 全部 | `--limit` | `-l` | int | `20` | 每頁筆數上限 |
| 全部 | `--offset` | - | int | `0` | 分頁偏移量 |
| 全部 | `--format` | `-f` | string | `text` | 輸出格式：彩色終端表格或 JSON 格式 |
| `community`, `sale` | `--min-age` | - | float | None | 最小屋齡（年） |
| `community`, `sale` | `--max-age` | - | float | None | 最大屋齡（年） |
| `sale` | `--min-price` | - | int | None | 最低總價（萬元） |
| `sale` | `--max-price` | - | int | None | 最高總價（萬元） |
| `sale` | `--rooms` | - | int | None | 格局房數篩選（純整數） |

子指令涵蓋：`community`（社區節點）、`sale`（中古屋實體）、`newhouse`（新建案清單）。

#### 常用範例

```bash
# 依行政區與屋齡檢索社區節點
uv run houselens list community -r 台北市 -s 松山區 --max-age 10

# 依總價、屋齡與房數篩選中古屋（顯示刊登數與聚合比價標記）
uv run houselens list sale -r 台北市 --min-age 0 --max-age 5 --rooms 3 --min-price 2000 --max-price 5000

# JSON 輸出模式（供管道管線處理或自動化腳本串接）
uv run houselens list sale --format json | jq '.[0]'
```

---

### 5. 物件規格與比價檢視 (get)

深入檢視單一實體完整規格、建築規劃與跨平台刊登比價明細。

#### 參數選項

| 指令 | 識別碼參數 (IDENTIFIER) | 選項 | 說明 |
| :--- | :--- | :--- | :--- |
| `houselens get community <id>` | 社區內部 UUID、UUID 前綴、或 591 社區編號（如 `5855864`） | `-f, --format <text\|json>` | 檢視建築規劃、車位比、座向規則、公設清單與管理費 |
| `houselens get sale <id>` | 房屋實體 UUID、UUID 前綴、或各平台刊登編號（如 `S20604856`） | `-f, --format <text\|json>` | 檢視客觀物理規格，並列出跨平台來源刊登比價明細 |
| `houselens get newhouse <id>` | 建案內部 UUID、UUID 前綴、或建案 HID（如 `138045`） | `-f, --format <text\|json>` | 檢視建案建材、團隊與 layout_v2 房型坪數規劃矩陣 |

#### 常用範例

```bash
# 依 591 社區編號檢視社區規格面板
uv run houselens get community 5855864

# 依外部刊登編號反查房屋實體與跨平台比價明細
uv run houselens get sale S20604856

# 依 HID 以 JSON 格式輸出新建案詳情
uv run houselens get newhouse 138045 --format json
```

---

## 核心架構與消歧去重機制

* 外掛自主正規化（Anti-Corruption Layer）：
  * 各平台外掛模組（如 591）負責完全清洗其特化字串（如 `"5,258萬元"`, `"2F/24F"`, `"3房2廳2衛"`, `"1年"`, `"30%"`, `"4200元/月"`）。
  * 核心層契約與領域規格僅流通純強型別數值（`int`, `float`, `bool`），絕不允許非結構化雜質溢出模組外。
* 實體與刊登解耦（1:N）：
  * `PropertyTable`：代表現實客觀物理房屋（純數值總價 `price_wan`、單價 `unit_price_wan`、總坪數 `total_area_pin`、所在樓層 `floor_current`、總樓層 `floor_total`、房數 `rooms`、屋齡 `building_age_years`）。
  * `PropertyListingTable`：代表各房仲刊登廣告（來源平台、外部 ID、該刊登開價、封面圖）。
* 純數學消歧去重規則：
  1. 社區名稱：同社區字串相符。
  2. 所在樓層：純整數 O(1) 相等性比對（例如地下室以負整數 `-1` 代表 B1）。
  3. 權狀總坪數：純浮點數容差比對（預設 `+-2%` 容許誤差）。
  4. 格局房數：純整數 O(1) 相等性比對。
  符合上述規則之新刊登，自動歸戶合併至同一客觀物理實體，杜絕重複膨脹。
