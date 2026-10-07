"""HouseLensAPI - 信義房屋密碼學防腐層單元測試 (Unit Tests for Sinyi Crypto)"""

import base64
import gzip
import json
import pytest

from src.providers.source_sinyi.config import SINYI_AES_KEY
from src.providers.source_sinyi.crypto import (
    AESCipher,
    BlockAlignmentError,
    GzipCompressor,
    InvalidKeyError,
    PaddingError,
    SinyiCryptoService,
    SinyiPayloadError,
    clean_b64_string,
)


class TestAESCipher:
    """AESCipher 底層加解密單元測試"""

    def test_invalid_key_length(self):
        """測試無效金鑰長度與型別應拋出 InvalidKeyError"""
        with pytest.raises(InvalidKeyError):
            AESCipher(b"short_key")

        with pytest.raises(InvalidKeyError):
            AESCipher("string_key_not_bytes")  # type: ignore

    def test_encrypt_decrypt_roundtrip(self):
        """測試加解密回環一致性"""
        cipher = AESCipher(SINYI_AES_KEY)
        sample_text = b'{"machineNo": "0d092df5", "name": "\xe4\xbf\xa1\xe7\xbe\xa9\xe6\x88\xbf\xe5\xb1\x8b"}'

        encrypted = cipher.encrypt(sample_text)
        assert len(encrypted) % 16 == 0
        assert encrypted != sample_text

        decrypted = cipher.decrypt(encrypted)
        assert decrypted == sample_text

    def test_unaligned_ciphertext_raises_error(self):
        """測試未對齊 16 位元組之密文應拋出 BlockAlignmentError"""
        cipher = AESCipher(SINYI_AES_KEY)
        with pytest.raises(BlockAlignmentError):
            cipher.decrypt(b"not_aligned_bytes_123")

    def test_corrupted_padding_raises_error(self):
        """測試 PKCS7 填充內容毀損應拋出 PaddingError"""
        cipher = AESCipher(SINYI_AES_KEY)
        # 建立一塊長度為 16 但結尾 padding 毀損的密文
        raw_block = b"X" * 16
        with pytest.raises(PaddingError):
            cipher.decrypt(raw_block)


class TestGzipCompressor:
    """GzipCompressor 單元測試"""

    def test_gzip_detection_and_decompress(self):
        """測試 GZIP 串流辨識與解壓縮"""
        original = b'{"status": "ok", "message": "hello sinyi"}'
        gzipped = gzip.compress(original)

        assert GzipCompressor.is_gzipped(gzipped) is True
        assert GzipCompressor.is_gzipped(original) is False

        decompressed = GzipCompressor.decompress_if_needed(gzipped)
        assert decompressed == original

    def test_non_gzip_data_passthrough(self):
        """測試非 GZIP 格式直接原值返回"""
        plain = b"regular uncompressed bytes"
        assert GzipCompressor.decompress_if_needed(plain) == plain


class TestSinyiCryptoService:
    """SinyiCryptoService 整合加解密服務測試"""

    def test_clean_b64_string(self):
        """測試 Base64 字串清洗與轉義修復"""
        dirty = "QUJD\\\nREV\\r\n  R0hJSkt\\/MTIz"
        cleaned = clean_b64_string(dirty)
        assert "\n" not in cleaned
        assert "\r" not in cleaned
        assert " " not in cleaned
        assert r"\/" not in cleaned

    def test_encrypt_request_payload_format(self):
        """測試請求酬載加密與 JSON 封裝"""
        service = SinyiCryptoService()
        req_data = {
            "machineNo": "0d092df536b15527",
            "page": 1,
            "filter": {"houseAge": ["min-5"]},
        }

        wrapped = service.encrypt_request_payload(req_data, wrap_param=True)
        assert "param" in wrapped
        b64_val = wrapped["param"]
        assert isinstance(b64_val, str)

        # 反向驗證解碼解密
        decrypted = service.decrypt_response_payload(b64_val)
        assert decrypted == req_data

    def test_decrypt_response_with_gzip(self):
        """測試伺服器回應包含 GZIP 壓縮之解密還原"""
        service = SinyiCryptoService()
        resp_json = {
            "retCode": "000000",
            "retMsg": "成功",
            "content": {
                "totalCnt": "120",
                "object": [{"houseNo": "80689A", "price": 3838}],
            },
        }

        # 模擬伺服器端：JSON -> GZIP -> AES -> Base64
        json_bytes = json.dumps(resp_json, ensure_ascii=False).encode("utf-8")
        gzipped_bytes = gzip.compress(json_bytes)
        encrypted_bytes = service.cipher.encrypt(gzipped_bytes)
        b64_str = base64.b64encode(encrypted_bytes).decode("ascii")

        # 客戶端解密
        restored = service.decrypt_response_payload(b64_str)
        assert restored["retCode"] == "000000"
        assert restored["content"]["totalCnt"] == "120"
        assert restored["content"]["object"][0]["houseNo"] == "80689A"

    def test_decrypt_invalid_payload_raises_error(self):
        """測試傳入損毀內容拋出 SinyiPayloadError"""
        service = SinyiCryptoService()
        with pytest.raises(SinyiPayloadError):
            service.decrypt_response_payload("invalid_base64_!@#$")
