"""Unit and Integration Tests for HouseLens CLI (Typer CliRunner)"""

import json
import pytest
from typer.testing import CliRunner

from src.cli.main import app

runner = CliRunner()


def test_cli_help():
    """測試主命令與說明畫面"""
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "HouseLens" in res.output
    assert "provider" in res.output
    assert "sync" in res.output
    assert "list" in res.output
    assert "get" in res.output
    assert "db" in res.output


def test_cli_version():
    """測試版本查詢"""
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "HouseLens CLI version" in res.output


def test_cli_provider_list_text_and_json():
    """測試來源外掛列表指令 (純文字表格與 JSON)"""
    res_text = runner.invoke(app, ["provider", "list"])
    assert res_text.exit_code == 0
    assert "591" in res_text.output

    res_json = runner.invoke(app, ["provider", "list", "--format", "json"])
    assert res_json.exit_code == 0
    data = json.loads(res_json.output)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["provider_id"] == "591"


def test_cli_db_stats_text_and_json():
    """測試資料庫指標與儀表板指令"""
    res_text = runner.invoke(app, ["db", "stats"])
    assert res_text.exit_code == 0
    assert "HouseLens" in res_text.output

    res_json = runner.invoke(app, ["db", "stats", "--format", "json"])
    assert res_json.exit_code == 0
    data = json.loads(res_json.output)
    assert "total_communities" in data
    assert "total_properties" in data
    assert "dedup_ratio_pct" in data


def test_cli_list_queries():
    """測試庫存列表指令 (支援 JSON 管線輸出)"""
    # 1. 社區查詢
    res_c = runner.invoke(app, ["list", "community", "--format", "json"])
    assert res_c.exit_code == 0
    data_c = json.loads(res_c.output)
    assert isinstance(data_c, list)

    # 2. 中古屋查詢
    res_s = runner.invoke(app, ["list", "sale", "--format", "json"])
    assert res_s.exit_code == 0
    data_s = json.loads(res_s.output)
    assert isinstance(data_s, list)

    # 3. 新建案查詢
    res_nh = runner.invoke(app, ["list", "newhouse", "--format", "json"])
    assert res_nh.exit_code == 0
    data_nh = json.loads(res_nh.output)
    assert isinstance(data_nh, list)


def test_cli_get_detail_views():
    """測試單一物件規格與比價卡片檢視"""
    # 取得一筆新建案 HID
    res_nh = runner.invoke(app, ["list", "newhouse", "--format", "json", "--limit", "1"])
    assert res_nh.exit_code == 0
    items_nh = json.loads(res_nh.output)
    if items_nh:
        hid = str(items_nh[0]["source_hid"])
        res_get = runner.invoke(app, ["get", "newhouse", hid])
        assert res_get.exit_code == 0
        assert hid in res_get.output

    # 取得一筆中古屋
    res_s = runner.invoke(app, ["list", "sale", "--format", "json", "--limit", "1"])
    assert res_s.exit_code == 0
    items_s = json.loads(res_s.output)
    if items_s:
        pid = items_s[0]["id"]
        res_get_prop = runner.invoke(app, ["get", "sale", pid])
        assert res_get_prop.exit_code == 0
        assert "客觀房屋實體資訊" in res_get_prop.output


def test_cli_sale_house_age_filtering():
    """測試 list sale 之屋齡過濾參數"""
    res = runner.invoke(app, ["list", "sale", "--min-age", "0", "--max-age", "10", "--format", "json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert isinstance(data, list)
    for item in data:
        if item.get("building_age") is not None:
            assert 0.0 <= item["building_age"] <= 10.0
