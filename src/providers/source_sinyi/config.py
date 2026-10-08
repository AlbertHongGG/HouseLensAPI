"""HouseLensAPI - 信義房屋專屬系統常數與通訊設定 (Sinyi Provider Configuration)

定義信義房屋手機端 API 網關、加密金鑰規格、預設裝置標頭與常用設備參數樣板。
"""

from typing import Any, Dict

# 信義房屋手機端 API 主機基底位址
SINYI_API_BASE_URL: str = "https://sinyiapi.sinyi.com.tw"

# 靜態對稱加密金鑰 (AES-256，剛好 32 位元組)
SINYI_AES_KEY: bytes = b"Sinyi100111111111111111111111111"

# 密碼學規格常數
AES_KEY_LENGTH: int = 32
AES_BLOCK_SIZE: int = 16
GZIP_MAGIC_BYTES: bytes = b"\x1f\x8b"

# 通訊標頭規格
SINYI_USER_AGENT: str = "Sinyi100"
SINYI_HEADER_CODE: str = "1"

# 手機端 App 預設設備與環境指紋樣板
DEFAULT_DEVICE_PAYLOAD: Dict[str, Any] = {
    "machineNo": "0d092df536b15527",
    "ipAddress": "10.117.252.108",
    "osType": 1,
    "model": "SM-A315G",
    "tradeMark": "samsung",
    "deviceVersion": "10",
    "appVersion": "9.1.15",
    "deviceType": 1,
    "apType": 1,
    "browser": 0,
    "IDFA": "25bc599b-d8bc-4392-8386-662ed5d0fea5",
}

# 信義房屋網頁端 API 主機基底位址與常數
SINYI_WEB_API_BASE_URL: str = "https://sinyiwebapi.sinyi.com.tw"

# 網頁端通訊基礎標頭規格 (靜態傳輸標頭，不包含動態會話憑證 sat 與 sid)
SINYI_WEB_BASE_HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
    "code": "0",
    "Origin": "https://www.sinyi.com.tw",
    "Referer": "https://www.sinyi.com.tw/",
    "Content-Type": "application/json",
}

# 手機端靜態備用種子 SID (當遠端動態握手異常時之防禦性 Fallback)
FALLBACK_SEED_MOBILE_SID: str = "20261007235202049"

# 網頁端靜態備用種子會話憑證 (當遠端兩階段動態握手異常時之防禦性 Fallback)
FALLBACK_SEED_WEB_SAT: str = "730282"
FALLBACK_SEED_WEB_SID: str = "20260713043603896"

# 網頁端預設設備與環境指紋樣板 (防範缺漏欄位造成參數個數校驗失敗)
DEFAULT_WEB_DEVICE_PAYLOAD: Dict[str, Any] = {
    "machineNo": "",
    "ipAddress": "101.12.206.109",
    "osType": 3,
    "model": "web",
    "deviceVersion": "Windows 10",
    "appVersion": "154.0.0.0",
    "deviceType": 3,
    "apType": 3,
    "browser": 1,
    "memberId": "",
    "domain": "www.sinyi.com.tw",
    "utmSource": "",
    "utmMedium": "",
    "utmCampaign": "",
    "utmCode": "",
    "requestor": 1,
    "utmContent": "",
    "utmTerm": "",
    "sinyiGroup": 1,
}

