# HouseLens - 台灣全網房產數據終端與聚合引擎 (Real Estate Terminal & CLI Engine)

> **HouseLens** 是一個專為台灣房產市場打造的極致解耦、高效能、非同步資料聚合引擎與終端工具。  
> 擺脫傳統爬蟲腳本與純內部 Library 的思維，系統採用現代化 **Typer + Rich** 打造世界級的 CLI 終端工具，對外支援多平台外掛（首發 591，後續可平滑擴充信義房屋、永慶房屋、樂屋網等），對內提供純淨領域模型、智能實體消歧去重、以及現代化的非同步持久化倉儲。

---

## 🌟 核心設計哲學

1. **第一級終端命令體驗（First-class CLI Experience）**：
   - 內建 `houselens` 命令，支援彩色表格、動態進度條、跨平台比價卡片，並提供 `--format json` 支援管線自動化腳本。
2. **極致解耦的 Provider 插件架構**：
   - 核心業務與底層來源零依賴，主程式僅認標準抽象介面（`IHouseSourceProvider`, `ICommunityProvider`, `ISaleHouseProvider`, `INewHouseProvider`）。
   - 透過 `ProviderRegistry` 動態註冊與調用各平台模組。
3. **客觀實體與來源刊登嚴格分離（Entity vs Listing）**：
   - **客觀實體（Property）**：代表現實世界中的某一戶特定房屋。
   - **來源刊登（Listing）**：代表各房仲或屋主在不同平台上的刊登紀錄。
   - 內建 `PropertyDeduplicationService`，根據「社區、樓層、格局、面積（容差±2%）」自動跨來源去重合併。
4. **純淨無污染的領域模型（Pure Domain Models）**：
   - 全面採用 Pydantic V2 定義強型別資料合約。
   - 徹底杜絕平台特有私有欄位（如 591 特有的 `shape: int`、重複的 `room` 與 `main_area`、運維廣告推廣標記等）。
5. **防禦性型別轉換（Defensive Parsing）**：
   - 房產資料充滿「價格待定」、「150 元/坪/月」、「SRC造」等雜訊，Mapper 層嚴格處理缺值降級與數值轉換，確保系統永久穩定。

---

## 🏛️ 系統分層架構

```text
HouseLensAPI/
├── pyproject.toml              # uv 專案設定檔 (含 [project.scripts] houselens 入口)
├── uv.lock                     # 鎖定依賴套件版本
├── README.md                   # 系統架構說明書與 CLI 使用指南
│
├── src/
│   ├── cli/                    # 終端機表現層 (Typer + Rich)
│   │   ├── main.py             # CLI 主進入點與全域旗標處理
│   │   ├── views/              # Rich 視圖渲染器 (表格、卡片、儀表板)
│   │   └── commands/           # 子命令模組 (provider, db, sync, list, get)
│   │
│   ├── application/            # 應用協調層 (Use Cases & Progress)
│   │   ├── sync_usecase.py     # 數據同步流水線
│   │   ├── query_usecase.py    # 庫存多維檢索
│   │   ├── inspect_usecase.py  # 單一物件深入組裝 (含比價聚合)
│   │   ├── db_usecase.py       # 資料庫維護與指標統計
│   │   └── progress.py         # 進度回報抽象介面與 Rich 進度條
│   │
│   ├── domain/                 # 核心純淨領域模型 (Pydantic V2, 無外部污染)
│   │   ├── enums.py            # 縣市代碼、房屋型態、預售狀態等枚舉
│   │   ├── common.py           # 分頁查詢/結果、GeoPoint 座標
│   │   ├── community.py        # 社區 Summary / Detail / SearchQuery
│   │   ├── sale_house.py       # 中古屋 Summary / Detail / SearchQuery
│   │   └── new_house.py        # 新建案 Summary / Detail (layout_v2) / SearchQuery
│   │
│   ├── core/                   # 抽象介面合約與工廠
│   │   ├── exceptions.py       # 階層化例外體系
│   │   ├── registry.py         # ProviderRegistry 動態註冊中心
│   │   └── interfaces/         # IHouseSourceProvider, ICommunityProvider...
│   │
│   ├── providers/              # 來源模組外掛包 (完全自我封閉)
│   │   └── source_591/         # 591 專屬模組
│   │       ├── client.py       # 連線池、自動注入 App 標頭與 Canonical 網域
│   │       ├── provider.py     # Source591Provider
│   │       ├── community.py    # 社區端點實作
│   │       ├── sale_house.py   # 中古屋端點實作 (自動過濾 is_ads 廣告)
│   │       ├── new_house.py    # 新建案端點實作 (支援 p/limit, buildstatus)
│   │       └── mappers/        # 原始 JSON -> 領域模型轉換器
│   │
│   ├── storage/                # 持久化倉儲層 (SQLAlchemy 2.0 Async + Repository Pattern)
│   │   ├── database.py         # DatabaseManager, async_sessionmaker
│   │   ├── models/             # CommunityTable, PropertyTable, PropertyListingTable, NewHouseTable
│   │   ├── interfaces.py       # ICommunityRepository, IPropertyRepository, INewHouseRepository
│   │   └── repositories/       # 具體 SQL 倉儲實作 (含消歧去重 UPSERT)
│   │
│   └── services/               # 業務服務層
│       ├── deduplication.py    # 樓層正規化、格局相容性與坪數誤差比對
│       └── aggregator.py       # 跨平台一鍵同步與庫存檢索
│
└── tests/                      # 現代化測試套件 (Pytest + Asyncio)
    ├── unit/                   # 36 項單元測試 (CLI, Domain, Mappers, Registry, Repositories, Services)
    └── integration/            # 4 項 591 官方 API 活體驗證測試
```

---

## 🚀 快速上手 (Quick Start)

專案全面原生支援 [`uv`](https://docs.astral.sh/uv/) 工具鏈。

### 1. 安裝與環境同步
```bash
# 複製專案後同步虛擬環境與相依套件
uv sync
```

### 2. 執行全套自動化測試 (40 項測試 100% 通過)
```bash
uv run pytest tests/ -v
```

---

## 💻 CLI 終端指令完整手冊

只要在終端機輸入 `uv run houselens`（或在啟用虛擬環境下輸入 `houselens`）：

```text
Usage: houselens [OPTIONS] COMMAND [ARGS]...

🏠 HouseLens - 台灣全網房產數據終端管理系統 (Real Estate Terminal & CLI Engine)

Options:
  --db-path TEXT        自訂 SQLite 資料庫路徑 (預設: ./houselens.db)
  --debug               開啟除錯模式，印出詳細 Exception Stacktrace
  --version, -v         顯示目前 CLI 版本
  --help                顯示說明文件

Commands:
  provider  🔌 來源外掛模組管理與即時健康狀態檢查
  db        💾 本地資料庫維護、統計儀表板與重整
  sync      🔄 從外部房產平台同步資料並進行入庫與去重
  list      📋 檢索本地資料庫庫存房產資料 (支援表格與 JSON 輸出)
  get       🔍 檢視單一房產物件深度規格與跨平台比價卡片
```

---

### 1. 外掛模組管理 (`provider`)
```bash
# 查看所有已安裝註冊的房產外掛
uv run houselens provider list

# 輸出 JSON 格式供腳本使用
uv run houselens provider list --format json

# 執行即時健康檢查並量測連線延遲 (毫秒)
uv run houselens provider check 591
```

---

### 2. 資料庫維護與指標儀表板 (`db`)
```bash
# 初始化資料表結構
uv run houselens db init

# 檢視庫存容量、實體數量與消歧去重率儀表板
uv run houselens db stats

# 執行 SQLite 磁碟重整與空間最佳化 (VACUUM)
uv run houselens db vacuum
```

---

### 3. 數據同步流水線 (`sync`)
```bash
# 同步台北市社區資料 (含完整規格與公設詳情)
uv run houselens sync community --region-id 1 --limit 10 --details

# 同步台北市中古屋 (自動執行消歧去重合併與跨平台刊登聚合)
uv run houselens sync sale --region-id 1 --limit 10 --details

# 同步預售屋新建案 (含 layout_v2 房型坪數規劃矩陣)
uv run houselens sync newhouse --region-id 1 --limit 10 --details

# 一鍵同步指定行政區的三大領域完整資料
uv run houselens sync all --region-id 1 --limit 10 --details
```

---

### 4. 本地庫存檢索 (`list`)
```bash
# 查詢在庫社區清單
uv run houselens list community --region 台北市 --limit 10

# 查詢在庫中古屋 (標註各平台刊登筆數與聚合比價徽章)
uv run houselens list sale --region 台北市 --min-price 2000 --max-price 5000

# 查詢在庫新建案
uv run houselens list newhouse --region 台北市

# 管線輸出 (Pipe to jq 或儲存為檔案)
uv run houselens list sale --format json | jq '.[0]'
```

---

### 5. 物件詳情卡片與跨平台比價 (`get`)
```bash
# 查看單一社區規格卡片 (支援 UUID 或 591 社區 ID)
uv run houselens get community 5935874

# 查看單一中古屋規格 + 跨平台來源刊登比價明細 (支援 UUID、前綴或外部房源編號)
uv run houselens get sale S20912908

# 查看單一新建案建材特色與 layout_v2 房型坪數矩陣
uv run houselens get newhouse 134497
```

---

## 📊 領域規格精準映射總結

| 領域 | 官方端點 | 核心特點 |
| :--- | :--- | :--- |
| **社區 (Community)** | `/v1/search/list`<br>`/v1/app/gateway/community/info` | 支援關鍵字/年份查詢，解析 15+ 項完整建築規劃（車位比、座向規則、景觀公設設計公司、公設清單、管理費）。 |
| **中古屋 (SaleHouse)** | `/v1/app/gateway/sale/list`<br>`/v1/app/gateway/sale/detail` | 廣告自動過濾（`is_ads == "1"`），數值化總坪數與純整數萬元總價。移除重複之 `room` 與 `main_area`，去除 591 特有 `shape`，全數移除仲介個資。 |
| **新建案 (NewHouse)** | `/v1/list-search`<br>`/v1/detail/base-info` | 解析 `area` 與 `price` 區間，詳情採用嚴格結構化 `layout_v2`（各房型對應坪數），補齊 `manage_cost`、`structural_engine`、`park_planning`、`direction_rule`、`build_intro` 等核心建材特色。 |
