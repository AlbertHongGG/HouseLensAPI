"""HouseLensAPI - 信義房屋高階加解密協調服務 (Sinyi Crypto Service)

整合 Base64 編解碼、AES-256-ECB 加解密、GZIP 串流解壓與 JSON 雙向結構裝卸。
"""

import base64
import json
import logging
from typing import Any, Dict, Union

from src.core.exceptions import HouseLensError
from src.providers.source_sinyi.config import SINYI_AES_KEY
from src.providers.source_sinyi.crypto.cipher import AESCipher
from src.providers.source_sinyi.crypto.compressor import GzipCompressor

logger = logging.getLogger(__name__)


class SinyiPayloadError(HouseLensError):
    """信義房屋封包格式無效或解析異常"""


def clean_b64_string(text: str) -> str:
    """清理 Base64 中的換行、空格與轉義字元"""
    return (
        text.replace(r"\n", "")
        .replace(r"\r", "")
        .replace(r"\/", "/")
        .replace("\\/", "/")
        .replace("\r", "")
        .replace("\n", "")
        .replace(" ", "")
        .strip()
    )


class SinyiCryptoService:
    """信義房屋加解密高階管線服務"""

    def __init__(self, key: bytes = SINYI_AES_KEY):
        self.cipher = AESCipher(key)
        self.compressor = GzipCompressor()

    def encrypt_request_payload(
        self, payload: Dict[str, Any], wrap_param: bool = True
    ) -> Dict[str, str]:
        """將請求明文字典加密為 Base64 密文並包裹為傳輸 JSON

        Args:
            payload: 待發送之業務參數字典。
            wrap_param: 是否外層包裹 {"param": "<B64>"}，預設為 True。

        Returns:
            若 wrap_param 為 True，返回 {"param": "<Base64_Cipher>"}。
            若為 False，返回 {"data": "<Base64_Cipher>"}。
        """
        try:
            json_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            plaintext_bytes = json_text.encode("utf-8")
        except Exception as e:
            raise SinyiPayloadError(f"請求資料序列化為 JSON 失敗: {e}") from e

        encrypted_bytes = self.cipher.encrypt(plaintext_bytes)
        b64_str = base64.b64encode(encrypted_bytes).decode("ascii")

        if wrap_param:
            return {"param": b64_str}
        return {"data": b64_str}

    def decrypt_response_payload(self, raw_content: Union[str, bytes]) -> Dict[str, Any]:
        """將伺服器回傳之 Base64 密文字串解密、解壓並還原為業務字典

        Args:
            raw_content: 伺服器回傳之文字或位元組。

        Returns:
            解密後的 Python 業務字典 (通常包含 retCode, retMsg, content 等)。
        """
        # 1. 萃取純 Base64 字串
        b64_candidate = ""
        if isinstance(raw_content, bytes):
            b64_candidate = raw_content.decode("utf-8", errors="replace")
        else:
            b64_candidate = str(raw_content)

        # 容錯處理：若回傳本為 JSON 且外層帶有 "param" 或 "data"
        if b64_candidate.strip().startswith("{"):
            try:
                parsed_json = json.loads(b64_candidate)
                if isinstance(parsed_json, dict) and "param" in parsed_json:
                    b64_candidate = str(parsed_json["param"])
                elif isinstance(parsed_json, dict) and "retCode" in parsed_json:
                    # 伺服器已回傳明文錯誤 JSON (例如未通過驗證)
                    return parsed_json
            except Exception:
                pass

        cleaned_b64 = clean_b64_string(b64_candidate)
        if not cleaned_b64:
            raise SinyiPayloadError("信義房屋回應內容為空或無有效密文")

        # 2. Base64 解碼
        try:
            ciphertext = base64.b64decode(cleaned_b64)
        except Exception as e:
            raise SinyiPayloadError(f"信義房屋回應 Base64 解碼失敗: {e}") from e

        # 3. AES-256-ECB 解密
        decrypted_bytes = self.cipher.decrypt(ciphertext)

        # 4. GZIP 檢測與自動解壓縮
        decompressed_bytes = self.compressor.decompress_if_needed(decrypted_bytes)

        # 5. UTF-8 解碼與 JSON 反序列化
        try:
            text = decompressed_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise SinyiPayloadError(f"信義房屋解密資料 UTF-8 解碼失敗: {e}") from e

        try:
            result = json.loads(text)
            if not isinstance(result, dict):
                raise SinyiPayloadError(f"信義房屋解密結果非 JSON 物件: {type(result).__name__}")
            return result
        except json.JSONDecodeError as e:
            raise SinyiPayloadError(f"信義房屋解密字串非有效 JSON: {e}") from e
