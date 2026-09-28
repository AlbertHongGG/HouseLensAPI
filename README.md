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

## CLI 指令手冊

命令進入點為 `houselens`（使用 `uv run houselens` 或虛擬環境直接執行 `houselens`）。

### 全域旗標 (Global Options)

| 選項 | 類型 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- |
| `--db-path` | `TEXT` | `./houselens.db` | 自訂 SQLite 資料庫路徑（支援環境變數 `HOUSELENS_DB_PATH`） |
| `--debug` | `FLAG` | `False` | 開啟除錯模式，印出詳細例外堆疊追蹤 |
| `--version`, `-v` | `FLAG` | - | 顯示目前 CLI 版本資訊 |
| `--help` | `FLAG` | - | 顯示說明手冊 |

---

### 1. 來源外掛模組 (`houselens provider`)

#### `houselens provider list`
列出所有已註冊的房產來源外掛模組與連線狀態。

* **參數選項**：
  | 選項 | 簡寫 | 類型 | 預設值 | 說明 |
  | :--- | :--- | :--- | :--- | :--- |
  | `--format` | `-f` | `TEXT` | `text` | 輸出格式：`text`（彩色表格）或 `json`（程式管線） |

* **常用範例**：
  ```bash
  # 檢視已安裝外掛表格
  uv run houselens provider list

  # 輸出 JSON 格式供自動化腳本調用
  uv run houselens provider list --format json
  ```

#### `houselens provider check [PROVIDER_ID]`
對指定外掛發送即時連線封包，量測延遲毫秒數（Latency）與可用性。

* **參數選項**：
  | 參數 | 類型 | 預設值 | 說明 |
  | :--- | :--- | :--- | :--- |
  | `PROVIDER_ID` | `ARG` | `591` | 來源外掛代碼（位置參數） |

* **常用範例**：
  ```bash
  uv run houselens provider check 591
  ```

---

### 2. 資料庫維護 (`houselens db`)

#### `houselens db init`
初始化資料庫結構，建立所有實體表（`communities`, `properties`, `property_listings`, `new_houses`）。

* **參數選項**：無（依賴全域 `--db-path`）
* **常用範例**：
  ```bash
  uv run houselens db init
  ```

#### `houselens db stats`
檢視資料庫指標儀表板：包含庫存總量、多平台重複刊登歸戶數與消歧去重率。

* **參數選項**：
  | 選項 | 簡寫 | 類型 | 預設值 | 說明 |
  | :--- | :--- | :--- | :--- | :--- |
  | `--format` | `-f` | `TEXT` | `text` | 輸出格式：`text`（儀表板面板）或 `json` |

* **常用範例**：
  ```bash
  uv run houselens db stats
  uv run houselens db stats --format json
  ```

#### `houselens db vacuum`
執行 SQLite 磁碟空間重整與最佳化回收。

* **參數選項**：無
* **常用範例**：
  ```bash
  uv run houselens db vacuum
  ```

---

### 3. 數據同步流水線 (`houselens sync`)

所有同步命令均具備動態進度條（Rich Progress）、爬取速率計算與庫存增量更新。

#### `houselens sync community`
從外部平台同步社區清單與詳細規劃。

* **參數選項**：
  | 選項 | 簡寫 | 類型 | 預設值 | 說明 |
  | :--- | :--- | :--- | :--- | :--- |
  | `--provider` | `-p` | `TEXT` | `591` | 來源外掛代碼 |
  | `--region-id` | `-r` | `INT` | `1` | 縣市代碼（1: 台北市、3: 新北市...） |
  | `--keyword` | `-k` | `TEXT` | `None` | 社區名稱關鍵字 |
  | `--details / --no-details` | `-d` | `BOOL` | `False` | 是否深入爬取建築規劃、公設清單與管理費 |
  | `--limit` | `-l` | `INT` | `None` | 同步筆數上限（留空則同步整頁 20 筆） |
  | `--format` | `-f` | `TEXT` | `text` | 輸出格式：`text` 或 `json` |

* **常用範例**：
  ```bash
  # 同步台北市前 10 筆社區基本資料
  uv run houselens sync community -r 1 -l 10

  # 搜尋關鍵字並深入爬取完整公設與建商詳情
  uv run houselens sync community -r 1 -k "鳴森大苑" --details
  ```

#### `houselens sync sale`
同步中古屋物件（**自動執行四維消歧去重**，同物理物件自動合併並建立刊登關聯）。

* **參數選項**：
  | 選項 | 簡寫 | 類型 | 預設值 | 說明 |
  | :--- | :--- | :--- | :--- | :--- |
  | `--provider` | `-p` | `TEXT` | `591` | 來源外掛代碼 |
  | `--region-id` | `-r` | `INT` | `1` | 縣市代碼 |
  | `--keyword` | `-k` | `TEXT` | `None` | 物件標題或路名關鍵字 |
  | `--min-price` | - | `INT` | `None` | 最低總價（萬元） |
  | `--max-price` | - | `INT` | `None` | 最高總價（萬元） |
  | `--details / --no-details` | `-d` | `BOOL` | `False` | 是否爬取產權面積拆解（主建/附屬/共有）與建築規格 |
  | `--limit` | `-l` | `INT` | `None` | 同步筆數上限 |
  | `--format` | `-f` | `TEXT` | `text` | 輸出格式：`text` 或 `json` |

* **常用範例**：
  ```bash
  # 依價格區間同步台北市中古屋（含去重合併）
  uv run houselens sync sale -r 1 --min-price 2000 --max-price 5000 -l 10

  # 同步並深入擷取產權坪數拆解與規格詳情
  uv run houselens sync sale -r 1 --details -l 20
  ```

#### `houselens sync newhouse`
同步預售屋與新成屋建案。

* **參數選項**：
  | 選項 | 簡寫 | 類型 | 預設值 | 說明 |
  | :--- | :--- | :--- | :--- | :--- |
  | `--provider` | `-p` | `TEXT` | `591` | 來源外掛代碼 |
  | `--region-id` | `-r` | `INT` | `1` | 縣市代碼 |
  | `--keyword` | `-k` | `TEXT` | `None` | 建案關鍵字 |
  | `--status` | `-s` | `TEXT` | `1,2` | 狀態代碼（`1`: 預售屋, `2`: 新成屋） |
  | `--details / --no-details` | `-d` | `BOOL` | `False` | 是否深入爬取 layout_v2 房型坪數規劃與團隊 |
  | `--limit` | `-l` | `INT` | `None` | 同步筆數上限 |
  | `--format` | `-f` | `TEXT` | `text` | 輸出格式：`text` 或 `json` |

* **常用範例**：
  ```bash
  # 同步台北市預售屋建案，含 layout_v2 房型規劃矩陣
  uv run houselens sync newhouse -r 1 -s 1 --details -l 10
  ```

#### `houselens sync all`
一鍵同步指定縣市的社區、中古屋與新建案三大領域。

* **參數選項**：
  | 選項 | 簡寫 | 類型 | 預設值 | 說明 |
  | :--- | :--- | :--- | :--- | :--- |
  | `--provider` | `-p` | `TEXT` | `591` | 來源外掛代碼 |
  | `--region-id` | `-r` | `INT` | `1` | 縣市代碼 |
  | `--details / --no-details` | `-d` | `BOOL` | `False` | 是否深入爬取詳情 |
  | `--limit` | `-l` | `INT` | `10` | 各領域同步筆數上限 |

* **常用範例**：
  ```bash
  uv run houselens sync all -r 1 -l 10 --details
  ```

---

### 4. 本地庫存檢索 (`houselens list`)

#### `houselens list community`
檢索在庫社區節點。

* **參數選項**：
  | 選項 | 簡寫 | 類型 | 預設值 | 說明 |
  | :--- | :--- | :--- | :--- | :--- |
  | `--region` | `-r` | `TEXT` | `None` | 縣市名稱（例: 台北市） |
  | `--section` | `-s` | `TEXT` | `None` | 行政區名稱（例: 松山區） |
  | `--keyword` | `-k` | `TEXT` | `None` | 社區名稱、地址或生活圈關鍵字 |
  | `--limit` | `-l` | `INT` | `20` | 每頁筆數上限 |
  | `--offset` | - | `INT` | `0` | 分頁偏移量 |
  | `--format` | `-f` | `TEXT` | `text` | 輸出格式：`text` 或 `json` |

* **常用範例**：
  ```bash
  uv run houselens list community -r 台北市 -s 松山區
  uv run houselens list community -k 鳴森 --format json
  ```

#### `houselens list sale`
檢索在庫中古屋實體（顯示各平台刊登筆數與聚合比價徽章）。

* **參數選項**：
  | 選項 | 簡寫 | 類型 | 預設值 | 說明 |
  | :--- | :--- | :--- | :--- | :--- |
  | `--region` | `-r` | `TEXT` | `None` | 縣市名稱 |
  | `--section` | `-s` | `TEXT` | `None` | 行政區名稱 |
  | `--min-price` | - | `INT` | `None` | 最低總價（萬元） |
  | `--max-price` | - | `INT` | `None` | 最高總價（萬元） |
  | `--keyword` | `-k` | `TEXT` | `None` | 標題或社區關鍵字 |
  | `--limit` | `-l` | `INT` | `20` | 每頁筆數上限 |
  | `--offset` | - | `INT` | `0` | 分頁偏移量 |
  | `--format` | `-f` | `TEXT` | `text` | 輸出格式：`text` 或 `json` |

* **常用範例**：
  ```bash
  uv run houselens list sale -r 台北市 --min-price 2000 --max-price 5000
  uv run houselens list sale --format json | jq '.[0]'
  ```

#### `houselens list newhouse`
檢索在庫新建案清單。

* **參數選項**：
  | 選項 | 簡寫 | 類型 | 預設值 | 說明 |
  | :--- | :--- | :--- | :--- | :--- |
  | `--region` | `-r` | `TEXT` | `None` | 縣市名稱 |
  | `--section` | `-s` | `TEXT` | `None` | 行政區名稱 |
  | `--keyword` | `-k` | `TEXT` | `None` | 建案關鍵字 |
  | `--limit` | `-l` | `INT` | `20` | 每頁筆數上限 |
  | `--offset` | - | `INT` | `0` | 分頁偏移量 |
  | `--format` | `-f` | `TEXT` | `text` | 輸出格式：`text` 或 `json` |

* **常用範例**：
  ```bash
  uv run houselens list newhouse -r 台北市
  ```

---

### 5. 物件規格與比價檢視 (`houselens get`)

#### `houselens get community <IDENTIFIER>`
檢視單一社區建築規格、公設清單、管理費與周邊交通。

* **參數選項**：
  | 參數/選項 | 類型 | 預設值 | 說明 |
  | :--- | :--- | :--- | :--- |
  | `IDENTIFIER` | `ARG` | (必填) | 社區內部 UUID、UUID 前綴、或 591 社區編號（如 `5855864`） |
  | `--format`, `-f` | `TEXT` | `text` | 輸出格式：`text`（Rich 面板）或 `json` |

* **常用範例**：
  ```bash
  uv run houselens get community 5855864
  uv run houselens get community 97af7c58 --format json
  ```

#### `houselens get sale <IDENTIFIER>`
檢視單一中古屋客觀實體規格，以及**跨平台來源刊登比價明細清單**。

* **參數選項**：
  | 參數/選項 | 類型 | 預設值 | 說明 |
  | :--- | :--- | :--- | :--- |
  | `IDENTIFIER` | `ARG` | (必填) | 房屋實體 UUID、UUID 前綴、或任何平台房源編號（如 `S20912908`） |
  | `--format`, `-f` | `TEXT` | `text` | 輸出格式：`text`（比價卡片）或 `json` |

* **常用範例**：
  ```bash
  # 依 UUID 前綴查詢
  uv run houselens get sale d9d9c8

  # 依 591 刊登編號反查實體與比價
  uv run houselens get sale S20912908
  ```

#### `houselens get newhouse <IDENTIFIER>`
檢視單一新建案建築規格、建材團隊與 `layout_v2` 房型坪數規劃矩陣。

* **參數選項**：
  | 參數/選項 | 類型 | 預設值 | 說明 |
  | :--- | :--- | :--- | :--- |
  | `IDENTIFIER` | `ARG` | (必填) | 建案內部 UUID、UUID 前綴、或建案 HID（如 `134497`） |
  | `--format`, `-f` | `TEXT` | `text` | 輸出格式：`text` 或 `json` |

* **常用範例**：
  ```bash
  uv run houselens get newhouse 134497
  ```

---

## 核心數據模型與去重機制

* **實體與刊登解耦（1:N）**：
  * `PropertyTable`：代表現實物理房屋（客觀總價、主建坪、格局、樓層）。
  * `PropertyListingTable`：代表各房仲刊登廣告（平台來源、外部 ID、該刊登開價、封面圖）。
* **四維消歧去重規則**：
  1. **社區名稱**：同社區判定。
  2. **樓層正規化**：統一提取主樓層（`2F/24F`、`2樓`、`2` 皆正規化為 `2`）。
  3. **權狀總坪數**：容許 $\pm 2\%$ 浮點四捨五入誤差。
  4. **格局相容性**：相容相符房數（`3房2廳2衛` 與 `3房2廳` 判定相容）。
  符合上述規則之新刊登，自動歸戶至同一物理實體，不重複膨脹房屋數量。
