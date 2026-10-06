# HouseLens - 台灣全網房產數據終端 (CLI Engine)

HouseLens 是一個以 CLI 為核心的非同步房產數據聚合引擎，以實體與刊登解耦、模組自主數據正規化（Anti-Corruption Layer）、全領域外部身分統一命名、主表原始房源固化與純數值消歧去重為架構基礎，整合各大房產平台（首發 591）提供標準化強型別資料管理與終端檢索。

---

## 快速開始

### 1. 安裝與環境同步
專案基於 Python 3.12+ 與 `uv` 工具鏈：
```bash
uv sync
```

### 2. 執行自動化測試
全套 120 項自動化測試（涵蓋領域模型規格、591 封包正規化轉換、倉儲層、消歧去重服務、領域不變量、單端點參數化探針與串流同步管線）：
```bash
uv run pytest
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
| 全部 | `--concurrency` | `-c` | int | `3` | 併發詳情補齊請求數 (Semaphore 控制) |
| 全部 | `--limit` | `-l` | int | None | 同步筆數上限 |
| 全部 | `--format` | `-f` | string | `text` | 輸出格式：`text` 或 `json` |
| `community`, `sale`, `newhouse` | `--keyword` | `-k` | string | None | 名稱、社區或路名關鍵字 |
| `community`, `sale` | `--min-age` | - | float | None | 最小屋齡（年） |
| `community`, `sale` | `--max-age` | - | float | None | 最大屋齡（年） |
| `sale` | `--min-price` | - | int | None | 最低總價（萬元） |
| `sale` | `--max-price` | - | int | None | 最高總價（萬元） |
| `newhouse` | `--status` | `-s` | string | `1,2` | 銷售狀態（1: 預售屋, 2: 新成屋） |

子指令涵蓋：`community`（社區）、`sale`（中古屋）、`newhouse`（新建案）、`all`（一鍵同步全領域）。本專案預設採用兩階段完整同步（清單探索 + 併發詳情補齊 + 消歧入庫）。

#### 常用範例

```bash
# 依總價與屋齡（10年以下）同步台北市中古屋（自動去重合併，並自動拆解產權五大面積與原始物件網址）
uv run houselens sync sale -r 1 --max-age 10 --min-price 2000 --max-price 5000 -l 20

# 依屋齡區間與關鍵字搜尋社區並同步完整公設清單與建商團隊
uv run houselens sync community -r 1 -k "鳴森大苑" --max-age 5

# 同步預售屋建案及其結構化房型坪數規劃
uv run houselens sync newhouse -r 1 -s 1 -l 10

# 一鍵兩階段同步指定縣市三大領域資料 (併發數 5)
uv run houselens sync all -r 1 -l 10 -c 5
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

子指令涵蓋：`community`（社區節點）、`sale`（中古屋實體）、`newhouse`（新建案清單）。中古屋清單首欄顯示 `[來源] 外部代碼`，方便對照原始房源。

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
| `houselens get community <id>` | 社區內部 UUID、UUID 前綴、或來源平台社區代號（如 `5868278`） | `-f, --format <text\|json>` | 檢視建築規劃、車位比、座向規則、公設清單、管理費與原始網址 |
| `houselens get sale <id>` | 房屋實體 UUID、UUID 前綴、或主表外部房源代號/各平台刊登編號（如 `S20604856`） | `-f, --format <text\|json>` | 檢視客觀物理規格、相簿照片數量、封面圖，並列出跨平台來源刊登比價明細與原始網址 |
| `houselens get newhouse <id>` | 建案內部 UUID、UUID 前綴、或外部建案專案代號（如 `128292` 或 `138045`） | `-f, --format <text\|json>` | 檢視建案建材、團隊、房型坪數規劃矩陣與原始網址 |

#### 常用範例

```bash
# 依 591 外部社區編號檢視社區規格面板
uv run houselens get community 5868278

# 依外部房屋代號反查房屋客觀實體與跨平台比價明細
uv run houselens get sale S20604856

# 依外部建案專案代碼輸出新建案詳情
uv run houselens get newhouse 128292
```

---

### 6. 來源 API 診斷與全流量錄製 (test)

提供 API 端點功能性測試、流量封包錄製與全端點套件健康度檢測。非侵入式雙向攔截 HTTP 請求與回應封包，並將完整快照（包含 Request、Response 與 Metadata）結構化持久化至專案根目錄 `.tmp/` 資料夾中。

`test` 指令採用三層級子命令設計：

```text
houselens test
|-- endpoint  : 測試單一指定端點功能回傳，支援自訂 target_id 與額外參數，並錄製原始封包
|-- suite     : 依序執行目標 Provider 之探針套件健康檢測與批次流量錄製
`-- list      : 列出指定來源 (或所有來源) 支援之診斷探針端點規格與參數需求
```

#### 子指令詳細規格

##### 6.1 `houselens test endpoint` (單端點功能測試)
針對特定來源之單一端點發送請求，支援指定目標物件 ID（如中古屋代號 `S20846137`）、自訂 Query 參數，並於終端即時渲染 ANSI 封包快照與語法高亮 Response Body。

| 參數 / 選項 | 簡寫 | 類型 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- | :--- |
| `provider_id` | - | Argument | 必要 | 目標來源外掛代碼（例如 `591`） |
| `endpoint_id` | - | Argument | 必要 | 目標端點代碼（例如 `sale_detail`, `sale_photos`, `sale_community_entry`, `community_detail`, `new_house_detail`） |
| `--target-id` | `-i` | Option | None | 目標物件/實體 ID（例如中古屋 `S20846137`、社區 `5855864`、建案 `138045`）。未提供時回退至預設種子 ID |
| `--params` | `-p` | Option | None | 自訂追加或覆蓋之 Query 參數（JSON 字串，例如 `'{"regionid": 1}'`） |
| `--output-file` | `-o` | Option | None | 自訂完整封包 JSON 落盤檔案路徑 |
| `--format` | `-f` | Option | `text` | 輸出格式：彩色終端表格 (`text`) 或 JSON 總結 (`json`) |
| `--show-body` / `--no-show-body` | - | Flag | `True` | 在 text 模式下是否於終端顯示 Response Body 預覽 |

##### 6.2 `houselens test suite` (套件健康檢測)
依序執行指定來源之全體端點探針，並產生批次總結報告與連線延遲面板。

| 參數 / 選項 | 簡寫 | 類型 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- | :--- |
| `provider_id` | - | Argument | None | 目標來源代碼（例如 `591`），留空則測試所有已註冊來源 |
| `--domain` | `-d` | Option | None | 業務領域過濾：`community`, `sale`, `newhouse`, `system` |
| `--delay` | - | Option | `1.0` | 各端點調用間冷卻秒數（0.0 至 30.0，防止觸發風控） |
| `--format` | `-f` | Option | `text` | 輸出格式：彩色終端表格 (`text`) 或 JSON 總結 (`json`) |

##### 6.3 `houselens test list` (探針清單規格)
即時查詢指定來源（或所有來源）支援的所有測試端點清單、領域、是否支援 Target ID、預設測試 ID 與功能說明。

| 參數 / 選項 | 簡寫 | 類型 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- | :--- |
| `provider_id` | - | Argument | None | 目標來源代碼（例如 `591`），留空則列出所有來源 |
| `--domain` | `-d` | Option | None | 業務領域過濾：`community`, `sale`, `newhouse`, `system` |
| `--format` | `-f` | Option | `text` | 輸出格式：彩色終端表格 (`text`) 或 JSON 總結 (`json`) |

#### 落盤目錄架構

測試執行時會自動於專案根目錄建立如下結構之 JSON 檔案（已納入 `.gitignore`）：
```
.tmp/
└── api_diagnostics/
    └── 591/
        ├── 2026-10-07T03-30-00_08-00/           # 批次 test suite 執行目錄
        │   ├── summary.json                     # 批次執行總結報告
        │   ├── health_ping.json                  # 平台連線檢測快照
        │   ├── community_list.json               # 社區清單 API 快照
        │   ├── community_detail.json             # 社區詳情 API 快照
        │   ├── sale_list.json                    # 中古屋清單 API 快照
        │   ├── sale_detail.json                  # 中古屋詳情 API 快照
        │   ├── sale_community_entry.json         # 中古屋社區入口卡片微服務快照
        │   ├── sale_photos.json                  # 中古屋相簿圖片微服務快照
        │   ├── new_house_list.json               # 新建案清單 API 快照
        │   └── new_house_detail.json             # 新建案詳情 API 快照
        └── single_probes/                       # 單端點 test endpoint 執行目錄
            ├── sale_detail_2026-10-07T03-13-13.json
            ├── sale_photos_2026-10-07T05-08-17.json
            └── community_detail_2026-10-07T03-15-20.json
```

#### 常用範例

```bash
# 測試 591 中古屋相簿圖片 API，指定測試特定物件代碼 S20846137 並錄製完整相簿封包
uv run houselens test endpoint 591 sale_photos -i S20846137

# 測試 591 中古屋詳情 API，指定測試特定物件代碼 S20846137 並錄製完整封包
uv run houselens test endpoint 591 sale_detail -i S20846137

# 測試 591 中古屋社區卡片入口微服務 API
uv run houselens test endpoint 591 sale_community_entry -i S20846137

# 測試 591 社區詳情 API，指定社區代碼 5855864 並另存至指定檔案
uv run houselens test endpoint 591 community_detail -i 5855864 -o ./debug_community.json

# 測試 591 中古屋清單 API 並傳入自訂 Query 篩選參數
uv run houselens test endpoint 591 sale_list -p '{"regionid": 3, "p": 2}'

# 單端點測試並輸出純 JSON 封包結構（供 jq 管線處理）
uv run houselens test endpoint 591 sale_detail -i S20846137 -f json | jq '.response.body'

# 查詢 591 支援的所有可用端點規格清單
uv run houselens test list 591

# 執行 591 來源之全體套件健康檢測
uv run houselens test suite 591

# 僅針對中古屋領域執行套件檢測（間隔 0.5 秒）
uv run houselens test suite 591 -d sale --delay 0.5
```

---

### 7. 中古屋社區消歧與外鍵補齊 (link-communities)

掃描庫存尚未建立社區外鍵 (`community_uuid IS NULL`) 之中古屋物件，以記憶體 DISTINCT 聚合最小化請求池，透過兩階段消歧比對與兩層式 SSOT 規範探索補齊社區實體並回填外鍵關聯。

#### 設計原理與架構規範
* **兩層式 SSOT 入庫保證**：社區的經緯度坐標 `lat/lng`、標準地址與封面圖等第一層屬性 100% 來自清單 API。遠端補齊時，系統強制先透過清單端點探索取得第一層 `NormalizedCommunitySummary` 快照，再呼叫詳情端點補齊第二層規格入庫，保證資料庫 `communities` 節點 100% 完整無遺漏。
* **第一階段 (本地快速對齊)**：優先以 `external_community_id` 或同縣市/同行政區完全吻合之名稱反查本地庫存，0 次 HTTP 請求極速綁定。
* **第二階段 (遠端探索與嚴格消歧)**：對本地無記錄者，調用來源端點檢索社區清單。嚴格比對行政區相符性與名稱完全一致性；同區出現 2 個以上相似社區時主動標記為歧義並略過，客觀無社區實體（如獨立透天、老公寓）自動跳過，絕不硬猜或誤配髒資料。

#### 參數選項

| 參數 / 選項 | 簡寫 | 類型 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- | :--- |
| `--provider` | `-p` | Option | `591` | 來源平台代碼 |
| `--region` | `-r` | Option | None | 限定特定行政縣市 (如「台北市」、「新北市」) |
| `--limit` | `-l` | Option | None | 掃描處理之中古屋筆數上限 |
| `--dry-run` | - | Option | `False` | 乾跑預演模式 (僅分析比對與輸出報表，不寫入資料庫) |
| `--format` | `-f` | Option | `text` | 輸出格式：彩色終端表格 (`text`) 或 JSON 總結 (`json`) |

#### 常用範例

```bash
# 預先乾跑預演：檢視台北市未綁社區之房屋消歧比對報表 (零資料庫寫入)
uv run houselens link-communities -r 台北市 --dry-run

# 正式執行全庫未關聯房屋之社區補齊與外鍵綁定
uv run houselens link-communities

# 限定處理前 50 筆房屋並輸出 JSON 格式報告
uv run houselens link-communities -l 50 --format json
```

---

## 核心架構與消歧去重機制

* **全領域外部身分統一命名規範 (Canonical External Identity)**：
  * 提供者代碼：跨領域 100% 統一為 `provider_id: str`。
  * 外部識別代碼：字串強型別，社區為 `external_community_id`、新建案為 `external_project_id`、中古屋為 `external_house_id`。徹底廢除舊有割裂之命名。
* **客觀實體首要來源固化與刊登聚合解耦 (Primary Source Solidification & Decoupling)**：
  * `PropertyTable`（中古屋客觀實體主表）：
    * 建立實體時直接固化代表性來源二元組 `provider_id` 與 `external_house_id`，設有複合索引 `ix_property_provider_house`。使用者直視主表即可清楚辨識該房屋由哪家平台何種代碼建立。
    * 保留內部外鍵 `community_uuid`（指向 `communities.id`）與外部社區代碼 `external_community_id`。即便本地庫存未建檔該社區，客觀外部社區識別碼永不遺失。
  * `PropertyListingTable`（來源刊登副表）：
    * 代表各平台房仲廣告，以 1:N 關聯掛載於客觀房屋實體，支援跨平台比價、價差追蹤與更新監控。
* **多層級純數值消歧去重機制 (Multi-Level Mathematical Deduplication)**：
  1. **第 1 級（具備社區者）**：依外部社區代碼 `external_community_id` 或社區名稱比對。
  2. **第 2 級（無社區物件，如透天、公寓、獨立別墅）**：依行政區、路街、同樓層/總樓層比對。路名地址絕不污染社區名稱欄位。
  3. **所在樓層純數值化**：地下室轉為負整數（如 B1 為 `-1`）；整棟銷售標記 `is_whole_building=True`，所在樓層記錄為 `None`（杜絕平台魔術數字 99 誤判為 99 樓）。
  4. **權狀總坪數容差比對**：純浮點數比對，預設 $\pm 2\%$ 容許誤差。
  5. **格局房數比對**：純整數相等性比對。
  * 符合規則之新刊登，自動合併掛載至既有客觀物理實體，杜絕資料庫重複膨脹。
* **原始房源追溯鏈接 (Original Object URL Tracking)**：
  * 所有客觀實體與刊登記錄皆原生維護 `url` 欄位，記錄來源平台對應之物件原始展示網址，支援一鍵直接連結至來源平台。
* **數值區間統一拆解規範 (Min/Max Numerical Range Unification)**：
  * 所有具有範圍屬性之數值欄位（開價單價、規劃坪數、車位價格等）一律拆分為強型別純數值 `min_xxx` 與 `max_xxx`，支援直接 SQL 數值區間比較與索引檢索。
* **領域防腐層與權威快照不變量 (Anti-Corruption Layer & Snapshot Overrides)**：
  * 各平台外掛模組（如 591）負責完全清洗其特化字串（如 `"5,258萬元"`, `"2F/24F"`, `"3房2廳2衛"`, `"1年"`, `"30%"`）。
  * CleanStr 自動防護：空字串 `""`、空白 `\s+`、破折號 `"-"`、中文佔位符 `"未提供"` 等於領域模型實例化瞬間昇華為 `None`。
  * 權威快照覆蓋語意（Authoritative Snapshot Override）：當以 Detail 詳情覆蓋更新既有實體時，Detail 中的 `None` 具備權威清空髒資料之能力，使舊有未清洗欄位能正確被覆蓋清空。
* **BFF 三端點並行非同步聚合與相簿微服務整合 (BFF Tri-Endpoint Parallel Aggregation)**：
  * 針對 591 平台中古屋資料破碎割裂現象（主詳情 API 無相簿與無社區真實名稱），採用 BFF (Backend-For-Frontend) 三端點非同步並行聚合架構：
    1. 主詳情端點：`/v1/app/gateway/sale/detail`（負責深層建築規格、價格格局與坐標）。
    2. 社區入口卡片端點：`/v1/sale/detail/community/entry`（負責突破房仲未綁官方庫之限制，補齊真實社區名稱）。
    3. 相簿圖片微服務端點：`/v1/ware/photos?id={id}&type=2`（負責取得房屋分組相簿與實景高畫質大圖）。
  * 透過 `asyncio.gather` 並行調用，總耗時與單一請求相當（0 額外耗時），且輔助微服務具備安全降級與容錯隔離，確保主資料流程堅不可摧。
* **相簿防腐層 ACL 與封面排序置頂不變量 (Photos ACL & Cover First Invariant)**：
  * 相簿防腐 DTO 自動排除影片群組（`key == "video"`），專注提取真實房屋實景相簿與格局圖。
  * 封面排序保證：標記為 `isCover == 1` 的照片強制置頂至第一順位（index 0），同時作為客觀實體之 `cover_image_url`。
  * 清洗萃取 1000px 高畫質圖並自動去除重複 URL，以標準字串陣列 `image_urls: List[str]` 持久化儲存。
* **資料庫結構自動增補遷移機制 (SQLite Lightweight Auto-Migration)**：
  * 本地 SQLite 引擎具備自我修復機制，在 `init_db()` 及 Session 連線建立時自動檢查現有資料表結構。
  * 若偵測到新版欄位（如 `cover_image_url`、`image_urls`）缺失，自動執行安全的 `ALTER TABLE ... ADD COLUMN` 動態增補，徹底免疫「no such column」問題，平滑相容既有資料庫。
* **串流微批次同步管線 (Streaming Micro-batch Pipeline)**：
  * 逐頁探索、快篩已入庫、併發取得自足規格、即時微批次持久化入庫，兼顧記憶體控制、失敗重試隔離與目標筆數跨頁累加。

---

## 資料庫資料表與 API 欄位對照 (Database Schema & API Mapping)

資料庫共有 **4 張資料表**，所有數值欄位皆已清洗為純數字型別（`int` / `float`）。  
系統全面貫徹**「兩層式跨領域統一架構 (Unified Two-Tier SSOT Architecture)」**，徹底杜絕同一個欄位跨 API 雙重抓取與 Fallback 混用：
* **第一層：身分與地理空間標識層**（`external_xxx_id`、名稱/標題、`region_name`、`section_name`、`street`、`address`、`cover_image_url`、關聯外部社區代碼/名稱、社區 `lat/lng`）：**100% 統一自清單 API 取得**。
* **第二層：深層建築、硬體規格與時程層**（價格/單價、產權坪數拆解、樓層、格局、陽台、車位規格值物件、完工/銷售時程、分區、工法、團隊代銷、結構化房型矩陣、中古屋與新建案基地坐標 `lat/lng`、原始物件 `url`）：**100% 統一自詳情 API 取得**。

---

### 1. `communities` (社區)

對應來源：591 社區清單 API (`/v1/search/list`) & 社區詳情 API (`/v1/app/gateway/community/info`)  
*架構原則：劃分單一事實來源（Single Source of Truth），第一層身分地理、坐標與成交均價 100% 來自「清單」API；第二層建築硬體規格 100% 來自「詳情」API 的 `build_info` 單一區塊。全文字欄位空字串與佔位雜質一律在防腐層正規化為 SQL `NULL`。*

| 欄位 | 型別 | 說明 | 591 API Body 路徑 | 架構層級 / 轉換規則 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | String(36) | 主鍵 (PK) | - | 系統產生 UUID v4 |
| `provider_id` | String(32) | 來源平台代碼 | - | 固定 `"591"`，索引 |
| `external_community_id` | String(64) | 外部社區 ID | 清單 `items[].id` | 【第一層：清單】轉字串，與 `provider_id` 構成複合唯一約束 `uq_community_source` |
| `name` | String(128) | 社區名稱 | 清單 `items[].name` | 【第一層：清單】去前後空白，索引 |
| `region_name` | String(32) | 縣市 | 清單 `items[].region` | 【第一層：清單】如「台北市」，索引 |
| `section_name` | String(32) | 行政區 | 清單 `items[].section` | 【第一層：清單】如「松山區」，索引 |
| `address` | String(256) | 地址 | 清單 `items[].simple_address` 組合 | 【第一層：清單】組合縣市與行政區 |
| `lat` / `lng` | Float | 經緯度坐標 | 清單 `items[].lat`, `items[].lng` | 【第一層：清單】清單直取，轉 float (社區詳情無坐標，清單為唯一來源) |
| `avg_unit_price_wan` | Float | 成交均價 (萬/坪) | 清單 `items[].price` | 【第一層：清單】清單直取實價登錄成交均價，轉 float |
| `shopping_district` | String(64) | 所屬商圈 | 清單 `items[].shop_name` | 【第一層：清單】清單直取商圈字串 |
| `transport` | String(128) | 鄰近站點 | 清單 `items[].station_name` | 【第一層：清單】清單直取交通站點字串 |
| `cover_image_url` | String(512) | 封面圖 URL | 清單 `items[].photo_src.src` | 【第一層：清單】清單直取外觀縮圖 URL |
| `url` | String(512) | 原始社區網址 | 詳情 `share_info.url` | 【第二層：詳情】來源平台社區對應完整網址 |
| `housing_status` | String(32) | 成屋/建案狀態 | 詳情 `build_info.build_type` / `build_type_str` | 【第二層：詳情】如「預售屋」、「新成屋」、「中古屋」 |
| `building_type` | String(64) | 建物實體型態 | 詳情 `build_info.purpose_str` | 【第二層：詳情】如「住宅大樓」、「華廈」、「透天」、「商辦」；空值轉 NULL |
| `purpose` | String(64) | 法定使用用途 | 詳情 `build_info.purpose_other2` | 【第二層：詳情】如「住家用」、「住商用」、「商業用」；空值轉 NULL |
| `building_age_years` | Float | 屋齡 (年) | 詳情 `build_info.age.content` | 【第二層：詳情】`1年` $\to$ `1.0`；`全新` $\to$ `0.0`，索引 |
| `total_households` | Int | 總戶數 | 詳情 `build_info.all_house_num.content` | 【第二層：詳情】轉 int |
| `base_area_pin` | Float | 基地面積 (坪) | 詳情 `build_info.base_area_num` | 【第二層：詳情】轉 float (全系統唯一統一坪數命名規範) |
| `land_division` | String(128) | 土地使用分區 | 詳情 `build_info.land_division` | 【第二層：詳情】如「第三種住宅區」；空值轉 NULL |
| `min_parking_price_wan` | Float | 車位開價下限 (萬元) | 詳情 `build_info.park_price` | 【第二層：詳情】解析下限純數值 (如 `150.0`) |
| `max_parking_price_wan` | Float | 車位開價上限 (萬元) | 詳情 `build_info.park_price` | 【第二層：詳情】解析上限純數值 (如 `320.0`) |
| `public_ratio_pct` | Float | 公設比 (%) | 詳情 `build_info.ratio` | 【第二層：詳情】如 `30%` $\to$ `30.0` |
| `parking_count` | Int | 車位總數 | 詳情 `build_info.all_park_num` | 【第二層：詳情】轉 int；平台未登錄之假性 0 轉 NULL |
| `parking_ratio` | Float | 車位配比率 | 詳情 `build_info.park_rate` | 【第二層：詳情】如 `1:1.07` $\to$ `1.07` |
| `manage_fee_per_pin` | Int | 管理費 (元/坪/月) | 詳情 `build_info.manage_cost.price` | 【第二層：詳情】轉 int |
| `floor_plan` | String(64) | 樓層規劃 | 詳情 `build_info.floor` | 【第二層：詳情】如「地上24層,地下4層」 |
| `structure` | String(64) | 結構工法 | 詳情 `build_info.structural_engine` | 【第二層：詳情】如「SRC造」；空值轉 NULL |
| `parking_type` | String(64) | 車位型態 | 詳情 `build_info.park_type_str` | 【第二層：詳情】如「坡道平面」；空值轉 NULL |
| `orientation` | String(64) | 座向規劃 | 詳情 `build_info.direction_rule` | 【第二層：詳情】如「朝北、朝南」 |
| `landscape_designer` | String(128) | 景觀設計 | 詳情 `build_info.landscape_name` | 【第二層：詳情】詳情 build_info 直取 |
| `public_facility_designer` | String(128) | 公設設計 | 詳情 `build_info.postulate_name` | 【第二層：詳情】詳情 build_info 直取 |
| `facilities` | JSON | 公設清單 | 詳情 `build_info.facility` | 【第二層：詳情】字串陣列 `["健身房", ...]` |
| `developer_company` | String(128) | 建商 | 詳情 `build_info.company` | 【第二層：詳情】建設公司名稱 |
| `builder_company` | String(128) | 營造廠 | 詳情 `build_info.build_company` | 【第二層：詳情】營造公司名稱 |
| `architect_company` | String(128) | 建築師 | 詳情 `build_info.construction_company` | 【第二層：詳情】事務所名稱 |
| `created_at` / `updated_at` | DateTime | 建立/更新時間 | - | 系統自動產生 |

---

### 2. `properties` (中古屋客觀實體主檔)

對應來源：591 中古屋清單 API (`/v1/app/gateway/sale/list`) & 詳情 API (`/v1/app/gateway/sale/detail`)  
*消歧去重規則：同社區（或無社區者同路街樓層）+ 樓層相等 + 房數相等 + 坪數誤差 $\pm 2\%$ 內自動合併。主表固化建立來源身分二元組。*

| 欄位 | 型別 | 說明 | 591 API Body 路徑 | 架構層級 / 轉換規則 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | String(36) | 實體主鍵 (PK) | - | 系統產生 UUID v4 |
| `provider_id` | String(32) | 首要來源平台代碼 | - | 建立該房屋實體之代表來源（如 `"591"`），索引 |
| `external_house_id` | String(64) | 首要來源外部房屋代碼 | 清單 `items[].houseid` | 【第一層：清單】代表代號（如 `"S20604856"`），索引 |
| `community_uuid` | String(36) | 所屬社區內部 UUID (FK) | - | 關聯至 `communities.id` (外鍵，ondelete="SET NULL") |
| `external_community_id` | String(64) | 外部平台社區識別碼 | 清單 `items[].community_info.community_id` | 【第一層：清單】如 `"5855864"`，保留客觀身分代碼，索引 |
| `community_name` | String(128) | 社區名稱 | 清單 `items[].community_info.community_name` | 【第一層：清單】去重比對鍵，索引 |
| `title` | String(256) | 物件標題 | 清單 `items[].title` | 【第一層：清單】保留來源最新刊登標題 |
| `region_name` | String(32) | 縣市 | 清單 `items[].region` | 【第一層：清單】如「台北市」，索引 |
| `section_name` | String(32) | 行政區 | 清單 `items[].section` | 【第一層：清單】如「松山區」，索引 |
| `street` | String(64) | 街道 | 清單 `items[].street_name` | 【第一層：清單】如「三民路」，索引 |
| `address` | String(256) | 完整地址 | 清單 `items[].address` | 【第一層：清單】清單規範地址 |
| `url` | String(512) | 原始物件網址 | 詳情 `otherInfo.shareInfo.url` | 【第二層：詳情】來源平台房屋物件原始展示網址 |
| `is_whole_building` | Bool | 是否整棟銷售 | 詳情 `baseInfo.info[樓層].value` | 【第二層：詳情】整棟銷售標記（如透天、別墅），索引 |
| `price_wan` | Int | 總價 (萬元) | 詳情 `baseInfo.price` | 【第二層：詳情】轉 int (如 `5258`)，索引 |
| `unit_price_wan` | Float | 單價 (萬/坪) | 詳情 `baseInfo.unitPrice` | 【第二層：詳情】轉 float (如 `132.2`) |
| `total_area_pin` | Float | 登記總坪數 (坪) | 詳情 `baseInfo.area` | 【第二層：詳情】轉 float (去重容差 $\pm 2\%$)，索引 |
| `rooms` | Int | 格局：房數 | 詳情 `baseInfo.layout` | 【第二層：詳情】解析純整數 (如 `3`)，索引 |
| `living_rooms` | Int | 格局：廳數 | 詳情 `baseInfo.layout` | 【第二層：詳情】解析純整數 (如 `2`) |
| `bathrooms` | Int | 格局：衛數 | 詳情 `baseInfo.layout` | 【第二層：詳情】解析純整數 (如 `2`) |
| `balconies` | Int | 格局：陽台數 | 詳情 `baseInfo.info[陽台].value` | 【第二層：詳情】解析純整數 (如 `1`) |
| `floor_current` | Int | 所在樓層 | 詳情 `baseInfo.info[樓層].value` | 【第二層：詳情】轉 int (如 `2`；B1 記為 `-1`；整棟為 NULL)，索引 |
| `floor_total` | Int | 總樓層 | 詳情 `baseInfo.info[樓層].value` | 【第二層：詳情】轉 int (如 `24`)，索引 |
| `building_age_years` | Float | 屋齡 (年) | 詳情 `baseInfo.info[屋齡].value` | 【第二層：詳情】`1年` $\to$ `1.0`，索引 |
| `management_fee_monthly` | Int | 管理費 (元/月) | 詳情 `baseInfo.info[管理費].value` | 【第二層：詳情】轉 int (如 `4200`) |
| `public_ratio_pct` | Float | 公設比 (%) | 詳情 `baseInfo.info[公設比].value` | 【第二層：詳情】如 `30%` $\to$ `30.0` |
| `has_lease` | Bool | 帶租約 | 詳情 `baseInfo.info[帶租約].value` | 【第二層：詳情】`"是"` $\to$ `True`, `"否"` $\to$ `False` |
| `building_type` | String(64) | 建物型態 | 詳情 `kindStr` | 【第二層：詳情】如「住宅」 |
| `structure` | String(64) | 建築型態 | 詳情 `baseInfo.info[型態].value` | 【第二層：詳情】如「電梯大樓」 |
| `orientation` | String(32) | 朝向 | 詳情 `baseInfo.info[朝向].value` | 【第二層：詳情】如「坐南朝北」 |
| `purpose` | String(64) | 法定用途 | 詳情 `baseInfo.info[用途].value` | 【第二層：詳情】如「住家用」 |
| `current_state` | String(64) | 現況 | 詳情 `baseInfo.info[現況].value` | 【第二層：詳情】如「住宅」 |
| `parking_desc` | String(256) | 車位說明 | 詳情 `baseInfo.parking` | 【第二層：詳情】車位文字規格說明 |
| `main_area_pin` | Float | 主建物 (坪) | 詳情 `baseInfo.areaIntro[主建物].value` | 【第二層：詳情】轉 float |
| `auxiliary_area_pin` | Float | 附屬建物 (坪) | 詳情 `baseInfo.areaIntro[附屬建物].value` | 【第二層：詳情】轉 float |
| `common_area_pin` | Float | 共有部分 (坪) | 詳情 `baseInfo.areaIntro[共有部分].value` | 【第二層：詳情】轉 float |
| `land_area_pin` | Float | 土地持分 (坪) | 詳情 `baseInfo.areaIntro[土地持分坪數].value` | 【第二層：詳情】轉 float |
| `parking_area_pin` | Float | 車位面積 (坪) | 詳情 `baseInfo.areaIntro[車位面積].value` | 【第二層：詳情】轉 float |
| `lat` / `lng` | Float | 經緯度坐標 | 詳情 `baseInfo.address.lat`, `lng` | 【第二層：詳情】轉 float (中古屋物理精確坐標來自詳情 API) |
| `cover_image_url` | String(512) | 封面圖 URL | 清單 `photo_src` / 相簿微服務首圖 | 【第一/二層】封面高畫質大圖/縮圖 URL |
| `image_urls` | JSON | 相簿圖片 URL 清單 | 相簿微服務 `ware/photos` | 【第二層：微服務】標準字串陣列 `["https://..."]`，首圖置頂保證 |
| `created_at` / `updated_at` | DateTime | 建立/更新時間 | - | 系統自動產生 |

---

### 3. `property_listings` (刊登廣告表)

記錄各平台發布之房源廣告，多筆刊登可歸戶至同一 `properties` 實體。  
對應來源：591 中古屋清單 API (`/v1/app/gateway/sale/list`)

| 欄位 | 型別 | 說明 | 591 API Body 路徑 | 架構層級 / 轉換規則 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | String(36) | 刊登主鍵 (PK) | - | 系統產生 UUID v4 |
| `property_id` | String(36) | 所屬實體 ID (FK) | - | 關聯 `properties.id` (CASCADE) |
| `provider_id` | String(32) | 來源平台代碼 | - | 如 `"591"`，索引 |
| `external_house_id` | String(64) | 平台房源外部代碼 | 清單 `items[].houseid` | 【第一層：清單】如 `"S20604856"`，複合唯一索引 `uq_listing_source` |
| `listing_title` | String(256) | 刊登廣告標題 | 清單 `items[].title` | 【第一層：清單】房仲自訂廣告標題 |
| `listing_price_wan` | Int | 刊登開價 (萬元) | 清單 `items[].price` | 【第一層：清單】轉 int |
| `cover_image_url` | String(512) | 封面圖 URL | 清單 `items[].photo_src` | 【第一層：清單】清單刊登縮圖 |
| `image_urls` | JSON | 來源刊登相簿圖片清單 | 相簿微服務 `ware/photos` | 【第二層：微服務】該刊登所屬之相簿圖片清單 |
| `url` | String(512) | 刊登網址 | 詳情 `otherInfo.shareInfo.url` | 【第二層：詳情】來源刊登原始網址 |
| `raw_data` | JSON | 原始封包 | - | 快照備份 (可選) |
| `created_at` / `updated_at` | DateTime | 建立/更新時間 | - | 系統自動產生 |

---

### 4. `new_houses` (新建案)

對應來源：591 新建案清單 API (`/v1/list-search`) & 詳情 API (`/v1/detail/base-info`)  
*架構原則：劃分單一事實來源（Single Source of Truth），第一層身分地理由「清單」API 提供；第二層建築規格、車位規格、時程用途、團隊代銷、關聯社區與基地經緯度 100% 來自「詳情」API 的 `housing` 區塊集中提供。*

| 欄位 | 型別 | 說明 | 591 API Body 路徑 | 架構層級 / 轉換規則 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | String(36) | 建案主鍵 (PK) | - | 系統產生 UUID v4 |
| `provider_id` | String(32) | 來源平台代碼 | - | 如 `"591"`，索引 |
| `external_project_id` | String(64) | 外部建案專案代碼 | 清單 `items[].hid` | 【第一層：清單】轉字串 (如 `"138045"`)，複合唯一約束 `uq_new_house_source` |
| `name` | String(128) | 建案名稱 | 清單 `items[].build_name` | 【第一層：清單】如「長虹MVP」，索引 |
| `housing_status` | String(64) | 期程狀態 | 清單 `items[].build_type_name` | 【第一層：清單】如「預售屋」、「新成屋」 |
| `region_name` | String(32) | 縣市 | 清單 `items[].region` | 【第一層：清單】如「台北市」，索引 |
| `section_name` | String(32) | 行政區 | 清單 `items[].section` | 【第一層：清單】如「萬華區」，索引 |
| `address` | String(256) | 基地地址 | 清單 `items[].address` | 【第一層：清單】基地詳細地址 |
| `cover_image_url` | String(512) | 封面圖 URL | 清單 `items[].photo_src` | 【第一層：清單】外觀縮圖 URL |
| `url` | String(512) | 原始物件網址 | 詳情 `meta.og_url` | 【第二層：詳情】來源平台建案原始展示網址 |
| `building_type` | String(64) | 建物型態 | 詳情 `housing.purpose_name` | 【第二層：詳情】如「住宅大樓」、「華廈」、「透天」、「電梯公寓」；空值轉 NULL |
| `purpose` | String(64) | 法定用途 | 詳情 `housing.purpose_other_name` | 【第二層：詳情】如「住商用」、「住家用」、「商業用」；空值轉 NULL |
| `land_division` | String(128) | 土地使用分區 | 詳情 `housing.land_division` | 【第二層：詳情】如「第四種商業區」、「第一種住宅區」；空值轉 NULL |
| `handover_time` | String(64) | 完工/交屋期程 | 詳情 `housing.deal_time_v2.date` (備用 `housing.deal_time.date`) | 【第二層：詳情】如「預計2028年第一季度」、「隨時交屋」；pending 轉 NULL |
| `open_sell_date` | String(32) | 公開銷售日期 | 詳情 `housing.sell_time.date_origin` | 【第二層：詳情】標準 ISO 日期如「2025-02-01」；pending 轉 NULL |
| `min_unit_price_wan` | Float | 開價下限 (萬/坪) | 詳情 `housing.price` | 【第二層：詳情】區間拆解 (如 `79.0`) |
| `max_unit_price_wan` | Float | 開價上限 (萬/坪) | 詳情 `housing.price` | 【第二層：詳情】區間拆解 (如 `90.0`) |
| `min_area_pin` | Float | 規劃坪數下限 (坪) | 詳情 `housing.area` | 【第二層：詳情】區間拆解 (如 `28.0`) |
| `max_area_pin` | Float | 規劃坪數上限 (坪) | 詳情 `housing.area` | 【第二層：詳情】區間拆解 (如 `41.0`) |
| `base_area_pin` | Float | 基地面積 (坪) | 詳情 `housing.base_area.area` | 【第二層：詳情】轉 float |
| `public_ratio_pct` | Float | 公設比 (%) | 詳情 `housing.ratio` | 【第二層：詳情】如 `34.5%` $\to$ `34.5` |
| `total_households` | Int | 規劃戶數 | 詳情 `housing.households` | 【第二層：詳情】轉 int (如 `120`) |
| `manage_fee_per_pin` | Int | 管理費 (元/坪/月) | 詳情 `housing.manage_cost.price` | 【第二層：詳情】轉 int |
| `min_parking_price_wan` | Float | 車位開價下限 (萬元) | 詳情 `housing.park_price.price` | 【第二層：詳情】轉 float (如 `155.0`)；待定轉 NULL |
| `max_parking_price_wan` | Float | 車位開價上限 (萬元) | 詳情 `housing.park_price.price` | 【第二層：詳情】轉 float (如 `320.0`)；待定轉 NULL |
| `parking_ratio_desc` | String(32) | 車位配比描述 | 詳情 `housing.park_ratio` | 【第二層：詳情】如「1:0.46」 |
| `parking_ratio` | Float | 車位配比數值比率 | 詳情 `housing.park_ratio` | 【第二層：詳情】轉 float (如 `0.46`) |
| `parking_planning_desc` | String(128) | 車位規劃描述 | 詳情 `housing.park_planning` | 【第二層：詳情】如「平面式111個、機械式41個」 |
| `plane_parking_count` | Int | 平面車位數量 | 詳情 `housing.park_planning` | 【第二層：詳情】解析純整數 (如 `111`) |
| `mechanical_parking_count` | Int | 機械車位數量 | 詳情 `housing.park_planning` | 【第二層：詳情】解析純整數 (如 `41`) |
| `charging_piles_desc` | String(64) | 充電設備規劃 | 詳情 `housing.park_piles` | 【第二層：詳情】如「有充電設備（含預留）」、「無充電設備」 |
| `has_charging_piles` | Bool | 具備充電或預留設備 | 詳情 `housing.park_piles` | 【第二層：詳情】包含有充電或預留轉 `True`，無轉 `False` |
| `parking_type` | String(64) | 車位型態風格 | 詳情 `housing.park_style` | 【第二層：詳情】透天別墅呈現「1樓停車」、「前院停車」；集合大樓「暫無」清洗為 NULL |
| `layouts` | JSON | 結構化房型坪數矩陣 | 詳情 `housing.layout_v2[]` | 【第二層：詳情】`[{"room_name":"一房","rooms_count":1,"min_area_pin":14.0,"max_area_pin":17.0}]` |
| `structure` | String(128) | 結構工法 | 詳情 `housing.structural_engine` | 【第二層：詳情】如「SRC鋼骨鋼筋混凝土」 |
| `orientation` | String(64) | 座向規劃 | 詳情 `housing.direction_rule` | 【第二層：詳情】如「朝南、朝東」 |
| `developer_company` | String(128) | 投資興建 | 詳情 `housing.company` | 【第二層：詳情】建設公司名稱 |
| `builder_company` | String(128) | 營造廠 | 詳情 `housing.build_company` | 【第二層：詳情】營造公司名稱 |
| `architect_company` | String(128) | 建築設計 | 詳情 `housing.construction_company` | 【第二層：詳情】建築師事務所名稱 |
| `sales_agency_company` | String(128) | 企劃銷售 | 詳情 `housing.sell_company` | 【第二層：詳情】代銷公司名稱 |
| `reception_address` | String(256) | 接待會館 | 詳情 `housing.reception_address` | 【第二層：詳情】接待中心地址 |
| `community_uuid` | String(36) | 關聯社區內部 UUID | - | 關聯至 `communities.id` (外鍵索引) |
| `external_community_id` | String(64) | 關聯社區外部代碼 | 詳情 `housing.community_id` | 【第二層：詳情】標準字串代碼 (如 `"5962516"`)，跨領域索引 |
| `community_name` | String(128) | 關聯社區名稱 | 詳情 `housing.community_name` | 【第二層：詳情】如「長虹MVP」 |
| `community_age` | Int | 社區屋齡 | 詳情 `housing.community_age` | 【第二層：詳情】純整數 (新建案通常為 0) |
| `lat` / `lng` | Float | 基地經緯度坐標 | 詳情 `housing.map.lat` / `.lng` | 【第二層：詳情】轉 float，建立複合索引 `ix_new_house_lat_lng` |
| `created_at` / `updated_at` | DateTime | 建立/更新時間 | - | 系統自動產生 |
