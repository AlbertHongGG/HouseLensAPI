# HouseLensAPI - 台灣全網房產數據聚合與標準化中心

> **HouseLensAPI** 是一個專為台灣房產市場打造的極致解耦、高效能、非同步資料聚合引擎與知識庫。  
> 借鑑成熟的 Provider 插件化架構（參考 `ComicMgr` 模組模式），系統對外整合各大房產平台（首發 591，後續可平滑擴充信義房屋、永慶房屋、樂屋網等），對內提供統一純淨的領域模型、智能實體消歧去重、以及現代化的非同步持久化倉儲。

---

## 🌟 核心設計哲學

1. **極致解耦的 Provider 插件架構**：
   - 核心業務與底層來源零依賴，主程式僅認標準抽象介面（`IHouseSourceProvider`, `ICommunityProvider`, `ISaleHouseProvider`, `INewHouseProvider`）。
   - 透過 `ProviderRegistry` 動態註冊與調用各平台模組。
2. **純淨無污染的領域模型（Pure Domain Models）**：
   - 全面採用 Pydantic V2 定義強型別資料合約。
   - 徹底杜絕平台特有私有欄位（如 591 特有的 `shape: int`、重複的 `room` 與 `main_area`、運維廣告推廣標記等）。
3. **客觀實體與來源刊登嚴格分離（Entity vs Listing）**：
   - **客觀實體（Property）**：代表現實世界中的某一戶特定房屋。
   - **來源刊登（Listing）**：代表各房仲或屋主在不同平台上的刊登紀錄。
   - 內建 `PropertyDeduplicationService`，根據「社區、樓層、格局、面積（容差±2%）」自動跨來源去重合併。
4. **防禦性型別轉換（Defensive Parsing）**：
   - 房產資料充滿「價格待定」、「150 元/坪/月」、「SRC造」等雜訊，Mapper 層嚴格處理缺值降級與數值轉換，確保系統永久穩定。

---

## 🏛️ 系統分層架構

```text
HouseLensAPI/
├── pyproject.toml              # uv 專案設定檔
├── uv.lock                     # 鎖定依賴套件版本
├── src/
│   ├── domain/                 # 核心領域模型 (Pydantic V2, 無外部相依)
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
│   │       ├── client.py       # 連線池、自動注入 Android App 標頭與 Canonical 網域
│   │       ├── provider.py     # Source591Provider
│   │       ├── community.py    # 社區端點實作 (/v1/search/list, /v1/app/gateway/community/info)
│   │       ├── sale_house.py   # 中古屋端點實作 (/v1/app/gateway/sale/list, /detail)
│   │       ├── new_house.py    # 新建案端點實作 (/v1/list-search, /v1/detail/base-info)
│   │       └── mappers/        # 原始 JSON -> 領域模型轉換器
│   │
│   ├── storage/                # 資料庫與持久化倉儲 (SQLAlchemy 2.0 Async)
│   │   ├── database.py         # DatabaseManager, async_sessionmaker
│   │   ├── models/             # CommunityTable, PropertyTable, PropertyListingTable, NewHouseTable
│   │   ├── interfaces.py       # ICommunityRepository, IPropertyRepository, INewHouseRepository
│   │   └── repositories/       # 具體 SQL 實作 (含自動消歧去重 UPSERT)
│   │
│   └── services/               # 業務服務層
│       ├── deduplication.py    # 樓層正規化、格局相容性與坪數誤差比對
│       └── aggregator.py       # 跨平台一鍵同步與庫存檢索
│
└── tests/                      # 現代化測試套件 (Pytest + Asyncio)
    ├── unit/                   # 單元測試 (Domain, Mappers, Registry, Repositories, Services)
    └── integration/            # 整合測試 (591 官方 API 活體連通測試)
```

---

## 🚀 快速上手 (Quick Start)

專案全面原生支援 [`uv`](https://docs.astral.sh/uv/) 工具鏈。

### 1. 安裝與環境同步
```bash
# 複製專案後同步虛擬環境與相依套件
uv sync
```

### 2. 執行全套測試 (34 項測試 100% 通過)
```bash
# 執行所有測試（含單元測試與 591 活體 API 整合測試）
uv run pytest tests/ -v
```

---

## 💡 核心使用範例

### 1. 透過 Provider 直接調用 591 資料
```python
import asyncio
from src.core.registry import registry
from src.domain.community import CommunitySearchQuery
from src.domain.sale_house import SaleHouseSearchQuery
from src.domain.new_house import NewHouseSearchQuery
import src.providers  # 自動註冊內建 Provider

async def main():
    provider = registry.get_provider("591")
    
    # 搜尋台北市社區
    comms = await provider.community.search_communities(
        CommunitySearchQuery(region_id=1, keyword="鳴森大苑")
    )
    print(f"找到 {len(comms.items)} 筆社區，第一筆: {comms.items[0].community_name}")

    # 搜尋台北市中古屋
    houses = await provider.sale_house.search_sale_houses(
        SaleHouseSearchQuery(region_id=1, min_price=3000, max_price=6000)
    )
    print(f"找到 {len(houses.items)} 筆中古屋，第一筆總價: {houses.items[0].price}")

    # 搜尋預售屋新建案
    new_houses = await provider.new_house.search_new_houses(
        NewHouseSearchQuery(region_id=1, build_status="1")
    )
    print(f"找到 {len(new_houses.items)} 筆新建案，第一筆: {new_houses.items[0].project_name}")

asyncio.run(main())
```

### 2. 透過 Aggregator 一鍵同步並自動去重入庫
```python
import asyncio
from src.services.aggregator import HouseAggregatorService
from src.storage.database import db_manager
from src.domain.sale_house import SaleHouseSearchQuery

async def main():
    await db_manager.init_db()
    service = HouseAggregatorService()

    # 同步 591 中古屋前 10 筆物件及其詳細規格至本地資料庫 (自動執行消歧去重)
    synced = await service.sync_sale_houses(
        provider_id="591",
        query=SaleHouseSearchQuery(region_id=1, page=1),
        sync_details=True,
        max_items=10,
    )
    print(f"成功同步並入庫 {len(synced)} 筆標準物件實體！")

    # 本地快速檢索
    results = await service.search_properties(region="台北市", min_price=3000)
    for p in results:
        print(f"[{p.region}{p.section}] {p.title} - {p.price}萬元 (關聯刊登數: {len(p.listings)})")

asyncio.run(main())
```

---

## 📊 領域規格精準映射總結

| 領域 | 官方端點 | 核心特點 |
| :--- | :--- | :--- |
| **社區 (Community)** | `/v1/search/list`<br>`/v1/app/gateway/community/info` | 支援關鍵字/年份查詢，解析 15+ 項完整建築規劃（車位比、座向規則、景觀公設設計公司、公設清單、管理費）。 |
| **中古屋 (SaleHouse)** | `/v1/app/gateway/sale/list`<br>`/v1/app/gateway/sale/detail` | 廣告自動過濾（`is_ads == "1"`），數值化總坪數與純整數萬元總價。移除重複之 `room` 與 `main_area`，去除 591 特有 `shape`，全數移除仲介個資。 |
| **新建案 (NewHouse)** | `/v1/list-search`<br>`/v1/detail/base-info` | 解析 `area` 與 `price` 區間，詳情採用嚴格結構化 `layout_v2`（各房型對應坪數），補齊 `manage_cost`、`structural_engine`、`park_planning`、`direction_rule`、`build_intro` 等核心建材特色。 |
