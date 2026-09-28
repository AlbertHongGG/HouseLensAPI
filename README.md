# HouseLens - 台灣全網房產數據終端 (CLI Engine)

HouseLens 是一個以 CLI 為核心的非同步房產數據聚合引擎，以實體與刊登解耦、自動消歧去重為基礎，整合各大房產平台（首發 591）提供標準化資料管理與終端檢索。

---

## 快速開始

### 1. 安裝與環境同步
專案基於 Python 3.12+ 與 `uv` 工具鏈：
```bash
uv sync
```

### 2. 執行自動化測試
全套 40 項單元與整合測試：
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

從外部平台擷取資料，自動執行四維消歧去重並入庫。支援 Rich 進度條、速率計算與增量更新。

#### 參數選項

| 適用子指令 | 選項 | 簡寫 | 類型 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 全部 | `--provider` | `-p` | string | `591` | 來源外掛代碼 |
| 全部 | `--region-id` | `-r` | int | `1` | 縣市代碼（1: 台北市, 3: 新北市...） |
| 全部 | `--details` | `-d` | flag | `False` | 深入爬取規格詳情（公設、主建坪拆解、建商團隊） |
| 全部 | `--limit` | `-l` | int | None | 同步筆數上限 |
| 全部 | `--format` | `-f` | string | `text` | 輸出格式：`text` 或 `json` |
| `community`, `sale`, `newhouse` | `--keyword` | `-k` | string | None | 名稱、社區或路名關鍵字 |
| `sale` | `--min-price` | - | int | None | 最低總價（萬元） |
| `sale` | `--max-price` | - | int | None | 最高總價（萬元） |
| `sale` | `--min-age` | - | int | None | 最小屋齡（年） |
| `sale` | `--max-age` | - | int | None | 最大屋齡（年） |
| `newhouse` | `--status` | `-s` | string | `1,2` | 銷售狀態（1: 預售屋, 2: 新成屋） |

子指令涵蓋：`community`（社區）、`sale`（中古屋）、`newhouse`（新建案）、`all`（一鍵同步全領域）。

#### 常用範例

```bash
# 依總價與屋齡區間（10年以下）同步台北市中古屋（自動去重合併，並深入拆解產權坪數）
uv run houselens sync sale -r 1 --max-age 10 --min-price 2000 --max-price 5000 --details -l 20

# 關鍵字搜尋特定社區並同步完整公設清單與建商詳情
uv run houselens sync community -r 1 -k "鳴森大苑" --details

# 同步預售屋建案及其 layout_v2 房型規劃矩陣
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
| `sale` | `--min-price` | - | int | None | 最低總價（萬元） |
| `sale` | `--max-price` | - | int | None | 最高總價（萬元） |
| `sale` | `--min-age` | - | int | None | 最小屋齡（年） |
| `sale` | `--max-age` | - | int | None | 最大屋齡（年） |

子指令涵蓋：`community`（社區節點）、`sale`（中古屋實體）、`newhouse`（新建案清單）。

#### 常用範例

```bash
# 依行政區檢索社區節點
uv run houselens list community -r 台北市 -s 松山區

# 依總價與屋齡篩選中古屋（顯示刊登數與聚合比價徽章）
uv run houselens list sale -r 台北市 --min-age 0 --max-age 5 --min-price 2000 --max-price 5000

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
| `houselens get sale <id>` | 房屋實體 UUID、UUID 前綴、或各平台刊登編號（如 `S20912908`） | `-f, --format <text\|json>` | 檢視客觀物理規格，並列出跨平台來源刊登比價明細卡片 |
| `houselens get newhouse <id>` | 建案內部 UUID、UUID 前綴、或建案 HID（如 `134497`） | `-f, --format <text\|json>` | 檢視建案建材、團隊與 layout_v2 房型坪數規劃矩陣 |

#### 常用範例

```bash
# 依 591 社區編號檢視社區規格卡片
uv run houselens get community 5855864

# 依外部刊登編號反查房屋實體與跨平台比價明細
uv run houselens get sale S20912908

# 依 UUID 前綴以 JSON 格式輸出新建案詳情
uv run houselens get newhouse 134497 --format json
```

---

## 核心數據模型與去重機制

* 實體與刊登解耦（1:N）：
  * `PropertyTable`：代表現實物理房屋（客觀總價、主建坪、格局、樓層）。
  * `PropertyListingTable`：代表各房仲刊登廣告（平台來源、外部 ID、該刊登開價、封面圖）。
* 四維消歧去重規則：
  1. 社區名稱：同社區判定。
  2. 樓層正規化：統一提取主樓層（`2F/24F`、`2樓`、`2` 皆正規化為 `2`）。
  3. 權狀總坪數：容許 +-2% 浮點四捨五入誤差。
  4. 格局相容性：相容相符房數（`3房2廳2衛` 與 `3房2廳` 判定相容）。
  符合上述規則之新刊登，自動歸戶至同一物理實體，不重複膨脹房屋數量。
