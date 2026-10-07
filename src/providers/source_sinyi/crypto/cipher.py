"""HouseLensAPI - 信義房屋 AES-256-ECB 加解密器實作 (Sinyi AES Cipher)

專責處理 bytes 等級之 AES-ECB 區塊對齊、PKCS7 填充與反填充校驗，嚴格遵守單一職責原則 (SRP)。
"""

from Crypto.Cipher import AES

from src.core.exceptions import HouseLensError
from src.providers.source_sinyi.config import AES_BLOCK_SIZE, AES_KEY_LENGTH, SINYI_AES_KEY


class SinyiCryptoError(HouseLensError):
    """信義房屋密碼學運算通用基礎異常"""


class InvalidKeyError(SinyiCryptoError):
    """金鑰長度或格式無效異常"""


class BlockAlignmentError(SinyiCryptoError):
    """密文區塊長度未對齊異常"""


class PaddingError(SinyiCryptoError):
    """PKCS7 填充或反填充內容損毀異常"""


class AESCipher:
    """AES-256-ECB 加解密引擎 (搭配 PKCS7 Padding)"""

    def __init__(self, key: bytes = SINYI_AES_KEY):
        if not isinstance(key, bytes):
            raise InvalidKeyError(f"金鑰必須為 bytes 類型，傳入類型為 {type(key).__name__}")
        if len(key) != AES_KEY_LENGTH:
            raise InvalidKeyError(
                f"金鑰長度必須為 {AES_KEY_LENGTH} 位元組 (AES-256)，目前長度為 {len(key)}"
            )
        self._key = key

    @property
    def key(self) -> bytes:
        return self._key

    def encrypt(self, plaintext: bytes) -> bytes:
        """將明文進行 PKCS7 填充後以 AES-ECB 加密"""
        if not isinstance(plaintext, bytes):
            raise SinyiCryptoError("待加密明文必須為 bytes 類型")

        # PKCS7 填充
        pad_len = AES_BLOCK_SIZE - (len(plaintext) % AES_BLOCK_SIZE)
        padded_data = plaintext + bytes([pad_len]) * pad_len

        cipher = AES.new(self._key, AES.MODE_ECB)
        return cipher.encrypt(padded_data)

    def decrypt(self, ciphertext: bytes) -> bytes:
        """以 AES-ECB 解密並校驗去除 PKCS7 填充"""
        if not isinstance(ciphertext, bytes):
            raise SinyiCryptoError("待解密密文必須為 bytes 類型")

        if len(ciphertext) == 0:
            return b""

        if len(ciphertext) % AES_BLOCK_SIZE != 0:
            raise BlockAlignmentError(
                f"密文長度 ({len(ciphertext)} 位元組) 未對齊 AES 區塊大小 ({AES_BLOCK_SIZE} 位元組)"
            )

        cipher = AES.new(self._key, AES.MODE_ECB)
        decrypted = cipher.decrypt(ciphertext)

        # PKCS7 反填充與校驗
        pad_len = decrypted[-1]
        if not (1 <= pad_len <= AES_BLOCK_SIZE):
            raise PaddingError(f"無效的 Padding 長度數值: {pad_len}")

        expected_padding = bytes([pad_len]) * pad_len
        if decrypted[-pad_len:] != expected_padding:
            raise PaddingError("PKCS7 Padding 位元組內容損毀或不一致")

        return decrypted[:-pad_len]
