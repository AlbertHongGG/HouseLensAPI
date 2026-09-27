"""
HouseLens API - 封包驗證與最小化呼叫示範腳本
此腳本實測「封包紀錄」資料夾內的所有 API，以最小化參數與標頭驗證 591 資料獲取。
已涵蓋：
1. 房屋物件清單
2. 房屋物件清單 (關鍵字搜尋)
3. 房屋物件詳情資訊
4. 社區清單
5. 社區清單 (關鍵字搜尋)
6. 社區詳情資訊
7. 新建案物件清單 (新增)
8. 新建案物件詳情資訊 (新增)
"""

import sys
import json
import requests

sys.stdout.reconfigure(encoding='utf-8')

COMMON_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def verify_1_sale_list():
    """1. 房屋物件清單 API"""
    url = "https://bff-house.591.com.tw/v1/app/gateway/sale/list"
    headers = {
        "user-agent": COMMON_UA,
        "device": "android"  # 必要標頭：缺乏時 items 會回傳空陣列 []
    }
    params = {
        "regionid": "1",          # 台北市
        "version": "8.13.0.975",  # 必要參數：控制回傳資料結構格式
        "newlist": "1",           # 推薦：每頁筆數從 9 筆提升至 25 筆
        "p": "1"                  # 頁碼
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    data = r.json()
    items = data.get("data", {}).get("items", [])
    records = data.get("data", {}).get("records")
    return {
        "api": "房屋物件清單",
        "url": url,
        "status": data.get("status"),
        "success": data.get("status") == 1 and len(items) > 0,
        "items_count": len(items),
        "total_records": records,
        "sample_item": items[0].get("title") if items else None
    }

def verify_2_sale_list_keyword():
    """2. 房屋物件清單 (關鍵字搜尋) API"""
    url = "https://bff-house.591.com.tw/v1/app/gateway/sale/list"
    headers = {
        "user-agent": COMMON_UA,
        "device": "android"
    }
    params = {
        "regionid": "1",
        "version": "8.13.0.975",
        "newlist": "1",
        "keywords": "碧硯閣"
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    data = r.json()
    items = data.get("data", {}).get("items", [])
    records = data.get("data", {}).get("records")
    return {
        "api": "房屋物件清單(關鍵字搜尋)",
        "url": url,
        "status": data.get("status"),
        "success": data.get("status") == 1 and len(items) > 0,
        "items_count": len(items),
        "total_records": records,
        "sample_item": items[0].get("title") if items else None
    }

def verify_3_sale_detail():
    """3. 房屋物件詳情 API"""
    url = "https://bff-house.591.com.tw/v1/app/gateway/sale/detail"
    headers = {
        "user-agent": COMMON_UA  # 僅需 User-Agent
    }
    params = {
        "id": "20604856"         # 僅需房屋 ID
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    data = r.json()
    base_info = data.get("data", {}).get("baseInfo", {})
    return {
        "api": "房屋物件詳情資訊",
        "url": url,
        "status": data.get("status"),
        "success": data.get("status") == 1 and "title" in base_info,
        "title": base_info.get("title"),
        "price": f"{base_info.get('price')} 萬",
        "layout": base_info.get("layout")
    }

def verify_4_community_list():
    """4. 社區清單 API"""
    url = "https://bff-market.591.com.tw/v1/search/list"
    headers = {
        "user-agent": COMMON_UA  # 僅需 User-Agent
    }
    params = {
        "regionid": "1",         # 僅需 regionid
        "page": "1"              # 頁碼 (每頁 20 筆)
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    data = r.json()
    items = data.get("data", {}).get("items", [])
    paginate = data.get("data", {}).get("paginate", {})
    return {
        "api": "社區清單",
        "url": url,
        "status": data.get("status"),
        "success": data.get("status") == 1 and len(items) > 0,
        "items_count": len(items),
        "total_records": paginate.get("total"),
        "sample_item": items[0].get("name") if items else None
    }

def verify_5_community_keyword():
    """5. 社區清單 (關鍵字搜尋) API"""
    url = "https://bff-market.591.com.tw/v1/search/match"
    headers = {
        "user-agent": COMMON_UA,
        "device": "android",     # 必要標頭
        "deviceid": "houselens"  # 必要標頭 (任意字串)
    }
    params = {
        "keyword": "鳴森大苑"    # 僅需 keyword
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    data = r.json()
    items = data.get("data", {}).get("items", [])
    return {
        "api": "社區清單(關鍵字搜尋)",
        "url": url,
        "status": data.get("status"),
        "success": data.get("status") == 1 and len(items) > 0,
        "items_count": len(items),
        "sample_item": items[0].get("name") if items else None,
        "sample_address": items[0].get("full_address") if items else None
    }

def verify_6_community_detail():
    """6. 社區詳情資訊 API"""
    url = "https://bff-market.591.com.tw/v1/app/gateway/community/info"
    headers = {
        "user-agent": COMMON_UA  # 僅需 User-Agent
    }
    params = {
        "id": "5855864"          # 僅需社區 ID
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    data = r.json()
    base_info = data.get("data", {}).get("base_info", {})
    build_info = data.get("data", {}).get("build_info", {})
    return {
        "api": "社區詳情資訊",
        "url": url,
        "status": data.get("status"),
        "success": data.get("status") == 1 and "community_name" in base_info,
        "community_name": base_info.get("community_name"),
        "address": base_info.get("address"),
        "build_type": build_info.get("build_type_str"),
        "total_house": build_info.get("all_house_num", {}).get("content")
    }

def verify_7_newhouse_list():
    """7. 新建案物件清單 API (新增)"""
    url = "https://bff-newhouse.591.com.tw/v1/list-search"
    headers = {
        "user-agent": COMMON_UA  # 僅需 User-Agent
    }
    params = {
        "regionid": "1",         # 台北市 (亦支援 keywords 或無參數全台查詢)
        "p": "1",                # 頁碼
        "limit": "20"            # 每頁筆數
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    data = r.json()
    items = data.get("data", {}).get("items", [])
    total = data.get("data", {}).get("total")
    return {
        "api": "新建案物件清單",
        "url": url,
        "status": data.get("status"),
        "success": data.get("status") == 1 and len(items) > 0,
        "items_count": len(items),
        "total_records": total,
        "sample_item": items[0].get("build_name") if items else None,
        "sample_address": items[0].get("address") if items else None
    }

def verify_8_newhouse_detail():
    """8. 新建案物件詳情資訊 API (新增)"""
    url = "https://bff-newhouse.591.com.tw/v1/detail/base-info"
    headers = {
        "user-agent": COMMON_UA,
        "deviceid": "houselens"  # 必要標頭：缺少會回傳 '設備 ID 不能為空'
    }
    params = {
        "id": "138045"           # 僅需建案 ID (hid)
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    data = r.json()
    housing = data.get("data", {}).get("housing", {})
    price_info = housing.get("price", {})
    return {
        "api": "新建案物件詳情資訊",
        "url": url,
        "status": data.get("status"),
        "success": data.get("status") == 1 and "build_name" in housing,
        "build_name": housing.get("build_name"),
        "address": housing.get("address"),
        "build_type": housing.get("build_type_name"),
        "price": f"{price_info.get('price')} {price_info.get('unit')}"
    }

def main():
    print("=" * 80)
    print("HouseLens API - 全 8 項封包紀錄端點即時驗證測試報告")
    print("=" * 80)
    
    tests = [
        verify_1_sale_list,
        verify_2_sale_list_keyword,
        verify_3_sale_detail,
        verify_4_community_list,
        verify_5_community_keyword,
        verify_6_community_detail,
        verify_7_newhouse_list,
        verify_8_newhouse_detail
    ]
    
    results = []
    for t in tests:
        res = t()
        results.append(res)
        status_str = "SUCCESS" if res["success"] else "FAIL"
        print(f"[{status_str}] {res['api']}")
        for k, v in res.items():
            if k not in ["api", "success"]:
                print(f"    - {k}: {v}")
        print("-" * 60)
        
    all_success = all(r["success"] for r in results)
    print("\n" + "=" * 80)
    print(f"驗證總結: 共 {len(results)} 項 API，全數通過: {all_success}")
    print("=" * 80)

if __name__ == "__main__":
    main()
