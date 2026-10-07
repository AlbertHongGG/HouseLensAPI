"""HouseLensAPI - 信義房屋 GZIP 串流檢測與解壓縮器 (Sinyi GZIP Compressor)

專責處理回應資料流中 GZIP 魔術位元組之辨識與解壓縮。
"""

import zlib

from src.core.exceptions import HouseLensError
from src.providers.source_sinyi.config import GZIP_MAGIC_BYTES


class DecompressionError(HouseLensError):
    """GZIP 解壓縮異常"""


class GzipCompressor:
    """GZIP 資料流檢測與解壓縮工具"""

    @staticmethod
    def is_gzipped(data: bytes) -> bool:
        """檢測開頭是否為 GZIP 魔術位元組 (0x1F 0x8B)"""
        return bool(data and data.startswith(GZIP_MAGIC_BYTES))

    @classmethod
    def decompress_if_needed(cls, data: bytes) -> bytes:
        """若資料為 GZIP 格式則自動解壓，否則原樣返回"""
        if not cls.is_gzipped(data):
            return data

        try:
            # zlib.MAX_WBITS | 16 代表啟用 gzip 標頭辨識
            return zlib.decompress(data, zlib.MAX_WBITS | 16)
        except Exception as e:
            raise DecompressionError(f"信義房屋回應 GZIP 解壓縮失敗: {e}") from e
