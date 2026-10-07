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
