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
全套 51 項單元與整合測試（含 591 即時 API 整合測試與診斷套件）：
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
# 依總價與屋齡（10年以下）同步台北市中古屋（自動去重合併，並自動拆解產權五大面積）
uv run houselens sync sale -r 1 --max-age 10 --min-price 2000 --max-price 5000 -l 20

# 依屋齡區間與關鍵字搜尋社區並同步完整公設清單與建商團隊
uv run houselens sync community -r 1 -k "鳴森大苑" --max-age 5

# 同步預售屋建案及其 layout_v2 結構化房型坪數規劃
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

### 6. 來源 API 診斷與全流量錄製 (test)

依序測試目標房產來源之全部 API 探針，非侵入式雙向攔截 HTTP 請求與回應封包，並將完整快照（包含 Request、Response 與 Metadata）結構化持久化至專案根目錄 `.tmp/` 資料夾中。

#### 參數選項

| 參數 / 選項 | 簡寫 | 類型 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- | :--- |
| `provider_id` | - | Argument | None | 目標來源外掛代碼（例如 `591`），留空則依序測試所有已註冊來源 |
| `--domain` | `-d` | Option | None | 業務領域過濾：`community`, `sale`, `newhouse`, `system` |
| `--delay` | - | Option | `1.0` | 各端點調用間冷卻秒數（0.0 至 30.0，防止觸發平台風控） |
| `--format` | `-f` | Option | `text` | 輸出格式：彩色終端表格 (`text`) 或 JSON 總結 (`json`) |

#### 落盤目錄架構

測試執行時會自動於專案根目錄建立如下結構之 JSON 檔案（已納入 `.gitignore`）：
```
.tmp/
└── api_diagnostics/
    └── 591/
        └── 2026-09-29T18-50-53_683777_08-00/
            ├── summary.json          # 批次執行總結報告
            ├── health_ping.json       # 平台連線檢測端點全流量快照
            ├── community_list.json    # 社區清單 API 快照
            ├── community_detail.json  # 社區詳細資訊 API 快照
            ├── sale_list.json         # 中古屋清單 API 快照
            ├── sale_detail.json       # 中古屋詳細資訊 API 快照
            ├── new_house_list.json    # 新建案清單 API 快照
            └── new_house_detail.json  # 新建案詳細資訊 API 快照
```

#### 常用範例

```bash
# 測試 591 全端點並錄製封包（預設間隔 1.0 秒）
uv run houselens test 591

# 加快步調測試 591 全端點（間隔 0.5 秒）
uv run houselens test 591 --delay 0.5

# 僅針對 591 中古屋相關 API 進行健康檢測
uv run houselens test 591 --domain sale

# 輸出純 JSON 總結資料（供 CI/CD 流程自動化判定）
uv run houselens test 591 --format json
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

---

## 資料庫資料表與 API 欄位對照 (Database Schema & API Mapping)

資料庫共有 **4 張資料表**，所有數值欄位皆已清洗為純數字型別（`int` / `float`）：

* **`communities`**：社區基本資訊、行情、管費、公設規劃（來源：591 社區清單 & 詳情 API）
* **`properties`**：中古屋客觀實體主檔（去重合併後之房屋物理資料）
* **`property_listings`**：平台刊登廣告表（各大仲介刊登紀錄，1:N 關聯至 `properties`）
* **`new_houses`**：新建案與預售屋實體表（建案資訊、價格區間、房型規劃）

---

### 1. `communities` (社區)

對應來源：591 社區清單 API (`/v1/search/list`) & 社區詳情 API (`/v1/app/gateway/community/info`)

| 欄位 | 型別 | 說明 | 591 API Body 路徑 | 轉換規則 / 備註 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | String(36) | 主鍵 (PK) | - | UUID v4 |
| `source_provider` | String(32) | 來源平台 | - | 固定 `"591"` |
| `source_id` | String(64) | 來源社區 ID | 清單 `items[].id`<br>詳情 `base_info.community_id` | 轉字串（唯一索引） |
| `name` | String(128) | 社區名稱 | 清單 `items[].name`<br>詳情 `base_info.community_name` | 去前後空白 |
| `build_purpose` | String(64) | 主要用途 | 清單 `items[].build_purpose_simple`<br>詳情 `base_info.purpose_str` | 如「住家用」 |
| `build_type` | String(64) | 建物型態 | 清單 `items[].housing_type_str`<br>詳情 `base_info.build_type_str` | 如「電梯大樓」 |
| `region_name` | String(32) | 縣市 | 清單 `items[].region`<br>詳情 `base_info.region_name` | 如「台北市」 |
| `section_name` | String(32) | 行政區 | 清單 `items[].section`<br>詳情 `base_info.section_name` | 如「松山區」 |
| `address` | String(256) | 地址 | 清單 `items[].simple_address`<br>詳情 `base_info.address` | 清單組合縣市與行政區 |
| `lat` / `lng` | Float | 經緯度 | 清單 `items[].lat`, `lng`<br>詳情 `base_info.lat`, `lng` | 轉 float |
| `avg_unit_price_wan` | Float | 平均單價 (萬/坪) | 清單 `items[].price.price` | 轉 float |
| `building_age_years` | Float | 屋齡 (年) | 詳情 `build_info.age.content` | `1年` $\to$ `1.0`；`全新` $\to$ `0.0` |
| `total_households` | Int | 總戶數 | 詳情 `build_info.all_house_num.content` | 轉 int |
| `base_area_pin` | Float | 基地面積 (坪) | 詳情 `build_info.base_area_num` | 轉 float |
| `public_ratio_pct` | Float | 公設比 (%) | 詳情 `build_info.ratio` | 如 `30%` $\to$ `30.0` |
| `parking_count` | Int | 車位總數 | 詳情 `build_info.all_park_num` | 轉 int |
| `parking_ratio_pct` | Float | 車位比率 | 詳情 `build_info.park_rate` | 如 `1:1.07` $\to$ `1.07` |
| `manage_fee_per_pin` | Int | 管理費 (元/坪/月) | 詳情 `build_info.manage_cost.price` | 轉 int |
| `shopping_district` | String(64) | 所屬商圈 | 清單 `items[].shop_name` | - |
| `transport` | String(128) | 鄰近站點 | 清單 `items[].station_name` | - |
| `floor_plan` | String(64) | 樓層規劃 | 詳情 `build_info.floor` | 如「地上24層,地下4層」 |
| `structure` | String(64) | 結構工法 | 詳情 `build_info.structural_engine` | 如「SRC造」 |
| `park_type_str` | String(64) | 車位型態 | 詳情 `build_info.park_type_str` | 如「坡道平面」 |
| `direction_rule` | String(64) | 座向規劃 | 詳情 `build_info.direction_rule` | 如「朝北、朝南」 |
| `landscape_name` | String(128) | 景觀設計 | 詳情 `build_info.landscape_name` | - |
| `postulate_name` | String(128) | 公設設計 | 詳情 `build_info.postulate_name` | - |
| `facilities` | JSON | 公設清單 | 詳情 `build_info.facility` | 字串陣列 `["健身房", ...]` |
| `developer_company` | String(128) | 建商 | 詳情 `build_info.company` | 建設公司名稱 |
| `builder_company` | String(128) | 營造廠 | 詳情 `build_info.build_company` | 營造公司名稱 |
| `architect_company` | String(128) | 建築師 | 詳情 `build_info.construction_company` | 事務所名稱 |
| `cover_image_url` | String(512) | 封面圖 URL | 清單 `items[].photo_src.src` | - |
| `created_at` / `updated_at` | DateTime | 建立/更新時間 | - | 系統自動產生 |

---

### 2. `properties` (中古屋實體主檔)

對應來源：591 中古屋清單 API (`/v1/app/gateway/sale/list`) & 詳情 API (`/v1/app/gateway/sale/detail`)  
*消歧去重規則：同社區 + 樓層相等 + 房數相等 + 坪數誤差 $\pm 2\%$ 內自動合併*

| 欄位 | 型別 | 說明 | 591 API Body 路徑 | 轉換規則 / 備註 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | String(36) | 實體主鍵 (PK) | - | UUID v4 |
| `community_id` | String(36) | 所屬社區 ID (FK) | 清單 `items[].community_id` | 關聯至 `communities.id` |
| `community_name` | String(128) | 社區名稱 | 清單 `items[].community_info.community_name` | 去重比對鍵 |
| `title` | String(256) | 物件標題 | 清單 `items[].title`<br>詳情 `baseInfo.title` | 保留最新標題 |
| `price_wan` | Int | 總價 (萬元) | 清單 `items[].price`<br>詳情 `baseInfo.price` | 轉 int (如 `5258`) |
| `unit_price_wan` | Float | 單價 (萬/坪) | 清單 `items[].area_price`<br>詳情 `baseInfo.unitPrice` | 轉 float (如 `132.2`) |
| `total_area_pin` | Float | 登記總坪數 (坪) | 清單 `items[].areaUnit.area`<br>詳情 `baseInfo.area` | 轉 float (去重容差 $\pm 2\%$) |
| `rooms` | Int | 格局：房數 | 清單 `items[].layout_str`<br>詳情 `baseInfo.layout` | 解析純整數 (如 `3`) |
| `living_rooms` | Int | 格局：廳數 | 清單 `items[].layout_str`<br>詳情 `baseInfo.layout` | 解析純整數 (如 `2`) |
| `bathrooms` | Int | 格局：衛數 | 清單 `items[].layout_str`<br>詳情 `baseInfo.layout` | 解析純整數 (如 `2`) |
| `balconies` | Int | 格局：陽台數 | 詳情 `baseInfo.info[陽台].value` | 解析純整數 (如 `1`) |
| `floor_current` | Int | 所在樓層 | 清單 `items[].floor`<br>詳情 `baseInfo.info[樓層].value` | 轉 int (如 `2`；B1 記為 `-1`) |
| `floor_total` | Int | 總樓層 | 清單 `items[].all_floor`<br>詳情 `baseInfo.info[樓層].value` | 轉 int (如 `24`) |
| `building_age_years` | Float | 屋齡 (年) | 詳情 `baseInfo.info[屋齡].value` | `1年` $\to$ `1.0` |
| `management_fee_monthly` | Int | 管理費 (元/月) | 詳情 `baseInfo.info[管理費].value` | 轉 int (如 `4200`) |
| `public_ratio_pct` | Float | 公設比 (%) | 詳情 `baseInfo.info[公設比].value` | 如 `30%` $\to$ `30.0` |
| `has_lease` | Bool | 帶租約 | 詳情 `baseInfo.info[帶租約].value` | `"是"` $\to$ `True`, `"否"` $\to$ `False` |
| `building_type` | String(64) | 建物型態 | 清單 `items[].kindStr`<br>詳情 `kindStr` | 如「住宅」 |
| `building_structure` | String(64) | 建築型態 | 詳情 `baseInfo.info[型態].value` | 如「電梯大樓」 |
| `orientation` | String(32) | 朝向 | 詳情 `baseInfo.info[朝向].value` | 如「坐南朝北」 |
| `purpose` | String(64) | 法定用途 | 詳情 `baseInfo.info[用途].value` | 如「住家用」 |
| `current_state` | String(64) | 現況 | 詳情 `baseInfo.info[現況].value` | 如「住宅」 |
| `parking_desc` | String(256) | 車位說明 | 詳情 `baseInfo.parking` | - |
| `main_area_pin` | Float | 主建物 (坪) | 詳情 `baseInfo.areaIntro[主建物].value` | 轉 float |
| `auxiliary_area_pin` | Float | 附屬建物 (坪) | 詳情 `baseInfo.areaIntro[附屬建物].value` | 轉 float |
| `common_area_pin` | Float | 共有部分 (坪) | 詳情 `baseInfo.areaIntro[共有部分].value` | 轉 float |
| `land_area_pin` | Float | 土地持分 (坪) | 詳情 `baseInfo.areaIntro[土地持分坪數].value` | 轉 float |
| `parking_area_pin` | Float | 車位面積 (坪) | 詳情 `baseInfo.areaIntro[車位面積].value` | 轉 float |
| `region` | String(32) | 縣市 | 清單 `items[].region`<br>詳情 `baseInfo.address.region` | 如「台北市」 |
| `section` | String(32) | 行政區 | 清單 `items[].section`<br>詳情 `baseInfo.address.section` | 如「松山區」 |
| `street` | String(64) | 街道 | 清單 `items[].street_name`<br>詳情 `baseInfo.address.street` | 如「三民路」 |
| `address` | String(256) | 完整地址 | 清單 `items[].address`<br>詳情 `baseInfo.address` 組合 | 結構化組合完整地址 |
| `lat` / `lng` | Float | 經緯度 | 詳情 `baseInfo.address.lat`, `lng` | 轉 float |
| `created_at` / `updated_at` | DateTime | 建立/更新時間 | - | 系統自動產生 |

---

### 3. `property_listings` (刊登廣告表)

記錄各平台發布之房源廣告，多筆刊登可歸戶至同一 `properties` 實體。  
對應來源：591 中古屋清單 API (`/v1/app/gateway/sale/list`) & 詳情 API (`/v1/app/gateway/sale/detail`)

| 欄位 | 型別 | 說明 | 591 API Body 路徑 | 轉換規則 / 備註 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | String(36) | 刊登主鍵 (PK) | - | UUID v4 |
| `property_id` | String(36) | 所屬實體 ID (FK) | - | 關聯 `properties.id` (CASCADE) |
| `provider_id` | String(32) | 來源平台 | - | 固定 `"591"` |
| `external_house_id` | String(64) | 平台房源 ID | 清單 `items[].houseid`<br>詳情 `data.id` | 如 `"S20604856"`（唯一索引） |
| `listing_title` | String(256) | 刊登廣告標題 | 清單 `items[].title`<br>詳情 `baseInfo.title` | 房仲自訂廣告標題 |
| `listing_price_wan` | Int | 刊登開價 (萬元) | 清單 `items[].price`<br>詳情 `baseInfo.price` | 轉 int |
| `cover_image_url` | String(512) | 封面圖 URL | 清單 `items[].photo_src` | - |
| `raw_data` | JSON | 原始封包 | - | 快照備份 (可選) |
| `created_at` / `updated_at` | DateTime | 建立/更新時間 | - | 系統自動產生 |

---

### 4. `new_houses` (新建案)

對應來源：591 新建案清單 API (`/v1/list-search`) & 詳情 API (`/v1/detail/base-info`)

| 欄位 | 型別 | 說明 | 591 API Body 路徑 | 轉換規則 / 備註 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | String(36) | 建案主鍵 (PK) | - | UUID v4 |
| `provider_id` | String(32) | 來源平台 | - | 固定 `"591"` |
| `source_hid` | Int | 建案編號 (HID) | 清單 `items[].hid`<br>詳情 `housing.hid` | 轉 int (如 `138045`，唯一索引) |
| `project_name` | String(128) | 建案名稱 | 清單 `items[].build_name`<br>詳情 `housing.build_name` | 如「長虹MVP」 |
| `build_type` | String(64) | 銷售類型 | 清單 `items[].build_type_name`<br>詳情 `housing.build_type_name` | 如「預售屋」、「新成屋」 |
| `region` | String(32) | 縣市 | 清單 `items[].region`<br>詳情 `housing.region` | 如「台北市」 |
| `section` | String(32) | 行政區 | 清單 `items[].section`<br>詳情 `housing.section` | 如「萬華區」 |
| `address` | String(256) | 基地地址 | 清單 `items[].address`<br>詳情 `housing.address` | - |
| `min_unit_price_wan` | Float | 開價下限 (萬/坪) | 清單 `items[].price`<br>詳情 `housing.price` | 區間拆解 (如 `79.0`) |
| `max_unit_price_wan` | Float | 開價上限 (萬/坪) | 清單 `items[].price`<br>詳情 `housing.price` | 區間拆解 (如 `90.0`) |
| `min_area_pin` | Float | 規劃坪數下限 (坪) | 清單 `items[].area` | 區間拆解 (如 `28.0`) |
| `max_area_pin` | Float | 規劃坪數上限 (坪) | 清單 `items[].area` | 區間拆解 (如 `41.0`) |
| `base_area_pin` | Float | 基地面積 (坪) | 詳情 `housing.base_area.area` | 轉 float |
| `public_ratio_pct` | Float | 公設比 (%) | 詳情 `housing.ratio` | 如 `34.5%` $\to$ `34.5` |
| `total_households` | Int | 規劃戶數 | 詳情 `housing.households` | 轉 int (如 `120`) |
| `manage_fee_per_pin` | Int | 管理費 (元/坪/月) | 詳情 `housing.manage_cost.price` | 轉 int |
| `layouts` | JSON | 房型坪數矩陣 | 詳情 `housing.layout_v2[]` | `[{"room_name":"一房","rooms_count":1,"min_area_pin":14.0,"max_area_pin":17.0}]` |
| `structural_engine` | String(128) | 結構工法 | 詳情 `housing.structural_engine` | 如「SRC鋼骨鋼筋混凝土」 |
| `direction_rule` | String(64) | 座向規劃 | 詳情 `housing.direction_rule` | 如「朝南、朝東」 |
| `developer_company` | String(128) | 建商 | 清單 `items[].company`<br>詳情 `housing.company` | - |
| `builder_company` | String(128) | 營造廠 | 詳情 `housing.build_company` | - |
| `architect_company` | String(128) | 建築師 | 詳情 `housing.construction_company` | - |
| `reception_address` | String(256) | 接待會館 | 詳情 `housing.reception_address` | - |
| `cover_image_url` | String(512) | 封面圖 URL | 清單 `items[].photo_src` | - |
| `created_at` / `updated_at` | DateTime | 建立/更新時間 | - | 系統自動產生 |


