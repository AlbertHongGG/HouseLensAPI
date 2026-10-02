"""HouseLensAPI - 終端文字安全清洗器單元測試 (Unit Tests for Text Sanitizer)"""

from src.application.text_sanitizer import sanitize_terminal_text


def test_sanitize_terminal_text_basic():
    assert sanitize_terminal_text(None) == ""
    assert sanitize_terminal_text("") == ""
    assert sanitize_terminal_text("   大安區 敦化南路一段   ") == "大安區 敦化南路一段"


def test_sanitize_terminal_text_removes_emojis():
    raw_title = "⭐信義安和站兩分鐘⭐信義名揚華廈⭐超低公設⭐稀有釋出"
    cleaned = sanitize_terminal_text(raw_title)
    assert "⭐" not in cleaned
    assert cleaned == "信義安和站兩分鐘信義名揚華廈超低公設稀有釋出"

    # 包含多種 Emoji 符號
    complex_title = "🔥 降價了！【寬悅團隊】內湖五期 🏆 豪宅釋出 🎉"
    cleaned_complex = sanitize_terminal_text(complex_title)
    assert "🔥" not in cleaned_complex
    assert "🏆" not in cleaned_complex
    assert "🎉" not in cleaned_complex
    assert "降價了！【寬悅團隊】內湖五期 豪宅釋出" in cleaned_complex


def test_sanitize_terminal_text_collapses_whitespace_and_newlines():
    text_with_newlines = "社區名稱:\n富域\r\n\t高樓層景觀戶"
    cleaned = sanitize_terminal_text(text_with_newlines)
    assert "\n" not in cleaned
    assert "\r" not in cleaned
    assert "\t" not in cleaned
    assert cleaned == "社區名稱: 富域 高樓層景觀戶"


def test_sanitize_terminal_text_truncation():
    long_text = "這是一個非常非常長但是很有吸引力的台北市大安區精選豪宅物件標題"
    truncated = sanitize_terminal_text(long_text, max_len=15)
    assert len(truncated) <= 15
    assert truncated.endswith("...")
