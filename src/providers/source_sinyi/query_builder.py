"""HouseLensAPI - 信義房屋查詢條件構建與郵遞區號防腐層 (Sinyi Query Builder)

將系統通用 SaleHouseSearchQuery 規範轉換為信義房屋 /filterObject.php 加密端點所需之篩選酬載。
支援全台灣 22 縣市全區與 368 鄉鎮市區 3 碼郵遞區號映射、價格區間、屋齡區間與排序代碼轉換。
"""

import logging
from typing import Any, Dict, List, Optional

from src.domain.enums import Region
from src.domain.sale_house import SaleHouseSearchQuery

logger = logging.getLogger(__name__)

# 台灣 22 縣市各行政區 3 碼郵遞區號映射表
TAIWAN_DISTRICT_ZIPCODES: Dict[str, Dict[str, str]] = {
    "台北市": {
        "中正區": "100", "大同區": "103", "中山區": "104", "松山區": "105",
        "大安區": "106", "萬華區": "108", "信義區": "110", "士林區": "111",
        "北投區": "112", "內湖區": "114", "南港區": "115", "文山區": "116",
    },
    "新北市": {
        "萬里區": "207", "金山區": "208", "板橋區": "220", "汐止區": "221",
        "深坑區": "222", "石碇區": "223", "瑞芳區": "224", "平溪區": "226",
        "雙溪區": "227", "貢寮區": "228", "新店區": "231", "坪林區": "232",
        "烏來區": "233", "永和區": "234", "中和區": "235", "土城區": "236",
        "三峽區": "237", "樹林區": "238", "鶯歌區": "239", "三重區": "241",
        "新莊區": "242", "泰山區": "243", "林口區": "244", "蘆洲區": "247",
        "五股區": "248", "八里區": "249", "淡水區": "251", "三芝區": "252",
        "石門區": "253",
    },
    "基隆市": {
        "仁愛區": "200", "信義區": "201", "中正區": "202", "中山區": "203",
        "安樂區": "204", "暖暖區": "205", "七堵區": "206",
    },
    "宜蘭縣": {
        "宜蘭市": "260", "頭城鎮": "261", "礁溪鄉": "262", "壯圍鄉": "263",
        "員山鄉": "264", "羅東鎮": "265", "三星鄉": "266", "大同鄉": "267",
        "五結鄉": "268", "冬山鄉": "269", "蘇澳鎮": "270", "南澳鄉": "272",
    },
    "桃園市": {
        "中壢區": "320", "平鎮區": "324", "龍潭區": "325", "楊梅區": "326",
        "新屋區": "327", "觀音區": "328", "桃園區": "330", "龜山區": "333",
        "八德區": "334", "大溪區": "335", "復興區": "336", "大園區": "337",
        "蘆竹區": "338",
    },
    "新竹市": {
        "東區": "300", "北區": "300", "香山區": "300",
    },
    "新竹縣": {
        "竹北市": "302", "湖口鄉": "303", "新豐鄉": "304", "新埔鎮": "305",
        "關西鎮": "306", "芎林鄉": "307", "寶山鄉": "308", "竹東鎮": "310",
        "五峰鄉": "311", "橫山鄉": "312", "尖石鄉": "313", "北埔鄉": "314",
        "峨眉鄉": "315",
    },
    "苗栗縣": {
        "竹南鎮": "350", "頭份市": "351", "三灣鄉": "352", "南庄鄉": "353",
        "獅潭鄉": "354", "後龍鎮": "356", "通霄鎮": "357", "苑裡鎮": "358",
        "苗栗市": "360", "造橋鄉": "361", "頭屋鄉": "362", "公館鄉": "363",
        "大湖鄉": "364", "泰安鄉": "365", "銅鑼鄉": "366", "三義鄉": "367",
        "西湖鄉": "368", "卓蘭鎮": "369",
    },
    "台中市": {
        "中區": "400", "東區": "401", "南區": "402", "西區": "403",
        "北區": "404", "北屯區": "406", "西屯區": "407", "南屯區": "408",
        "太平區": "411", "大里區": "412", "霧峰區": "413", "烏日區": "414",
        "豐原區": "420", "后里區": "421", "石岡區": "422", "東勢區": "423",
        "和平區": "424", "新社區": "426", "潭子區": "427", "大雅區": "428",
        "神岡區": "429", "大肚區": "432", "沙鹿區": "433", "龍井區": "434",
        "梧棲區": "435", "清水區": "436", "大甲區": "437", "外埔區": "438",
        "大安區": "439",
    },
    "彰化縣": {
        "彰化市": "500", "芬園鄉": "502", "花壇鄉": "503", "秀水鄉": "504",
        "鹿港鎮": "505", "福興鄉": "506", "線西鄉": "507", "和美鎮": "508",
        "伸港鄉": "509", "員林市": "510", "社頭鄉": "511", "永靖鄉": "512",
        "埔心鄉": "513", "溪湖鎮": "514", "大村鄉": "515", "埔鹽鄉": "516",
        "田中鎮": "520", "北斗鎮": "521", "田尾鄉": "522", "埤頭鄉": "523",
        "溪州鄉": "524", "竹塘鄉": "525", "二林鎮": "526", "大城鄉": "527",
        "芳苑鄉": "528", "二水鄉": "530",
    },
    "南投縣": {
        "南投市": "540", "中寮鄉": "541", "草屯鎮": "542", "國姓鄉": "544",
        "埔里鎮": "545", "仁愛鄉": "546", "名間鄉": "551", "集集鎮": "552",
        "水里鄉": "553", "魚池鄉": "555", "信義鄉": "556", "竹山鎮": "557",
        "鹿谷鄉": "558",
    },
    "雲林縣": {
        "斗南鎮": "630", "大埤鄉": "631", "虎尾鎮": "632", "土庫鎮": "633",
        "褒忠鄉": "634", "東勢鄉": "635", "台西鄉": "636", "崙背鄉": "637",
        "麥寮鄉": "638", "斗六市": "640", "林內鄉": "643", "古坑鄉": "646",
        "莿桐鄉": "647", "西螺鎮": "648", "二崙鄉": "649", "北港鎮": "651",
        "水林鄉": "652", "口湖鄉": "653", "四湖鄉": "654", "元長鄉": "655",
    },
    "嘉義市": {
        "東區": "600", "西區": "600",
    },
    "嘉義縣": {
        "番路鄉": "602", "梅山鄉": "603", "竹崎鄉": "604", "阿里山鄉": "605",
        "中埔鄉": "606", "大埔鄉": "607", "水上鄉": "608", "鹿草鄉": "609",
        "太保市": "611", "朴子市": "612", "東石鄉": "613", "六腳鄉": "614",
        "新港鄉": "615", "民雄鄉": "621", "大林鎮": "622", "溪口鄉": "623",
        "義竹鄉": "624", "布袋鎮": "625",
    },
    "台南市": {
        "中西區": "700", "東區": "701", "南區": "702", "北區": "704",
        "安平區": "708", "安南區": "709", "永康區": "710", "歸仁區": "711",
        "新化區": "712", "左鎮區": "713", "玉井區": "714", "楠西區": "715",
        "南化區": "716", "仁德區": "717", "關廟區": "718", "龍崎區": "719",
        "官田區": "720", "麻豆區": "721", "佳里區": "722", "西港區": "723",
        "七股區": "724", "將軍區": "725", "學甲區": "726", "北門區": "727",
        "新營區": "730", "後壁區": "731", "白河區": "732", "東山區": "733",
        "六甲區": "734", "下營區": "735", "柳營區": "736", "鹽水區": "737",
        "善化區": "741", "大內區": "742", "山上區": "743", "新市區": "744",
        "安定區": "745",
    },
    "高雄市": {
        "新興區": "800", "前金區": "801", "苓雅區": "802", "鹽埕區": "803",
        "鼓山區": "804", "旗津區": "805", "前鎮區": "806", "三民區": "807",
        "楠梓區": "811", "小港區": "812", "左營區": "813", "仁武區": "814",
        "大社區": "815", "岡山區": "820", "路竹區": "821", "阿蓮區": "822",
        "田寮鄉": "823", "燕巢區": "824", "橋頭區": "825", "梓官區": "826",
        "彌陀區": "827", "永安區": "828", "湖內區": "829", "鳳山區": "830",
        "大寮區": "831", "林園區": "832", "鳥松區": "833", "大樹區": "840",
        "旗山區": "842", "美濃區": "843", "六龜區": "844", "內門區": "845",
        "杉林區": "846", "甲仙區": "847", "桃源區": "848", "那瑪夏區": "849",
        "茂林區": "851", "茄萣區": "852",
    },
    "屏東縣": {
        "屏東市": "900", "三地門鄉": "901", "霧台鄉": "902", "瑪家鄉": "903",
        "九如鄉": "904", "里港鄉": "905", "高樹鄉": "906", "鹽埔鄉": "907",
        "長治鄉": "908", "麟洛鄉": "909", "竹田鄉": "911", "內埔鄉": "912",
        "萬丹鄉": "913", "潮州鎮": "920", "泰武鄉": "921", "來義鄉": "922",
        "萬巒鄉": "923", "崁頂鄉": "924", "新埤鄉": "925", "南州鄉": "926",
        "林邊鄉": "927", "東港鎮": "928", "琉球鄉": "929", "佳冬鄉": "931",
        "新園鄉": "932", "枋寮鄉": "940", "枋山鄉": "941", "春日鄉": "942",
        "獅子鄉": "943", "車城鄉": "944", "牡丹鄉": "945", "恆春鎮": "946",
        "滿州鄉": "947",
    },
    "台東縣": {
        "台東市": "950", "綠島鄉": "951", "蘭嶼鄉": "952", "延平鄉": "953",
        "卑南鄉": "954", "鹿野鄉": "955", "關山鎮": "956", "海端鄉": "957",
        "池上鄉": "958", "東河鄉": "959", "成功鎮": "961", "長濱鄉": "962",
        "太麻里鄉": "963", "金峰鄉": "964", "大武鄉": "965", "達仁鄉": "966",
    },
    "花蓮縣": {
        "花蓮市": "970", "新城鄉": "971", "秀林鄉": "972", "吉安鄉": "973",
        "壽豐鄉": "974", "鳳林鎮": "975", "光復鄉": "976", "豐濱鄉": "977",
        "瑞穗鄉": "978", "萬榮鄉": "979", "玉里鎮": "981", "卓溪鄉": "982",
        "富里鄉": "983",
    },
    "澎湖縣": {
        "馬公市": "880", "西嶼鄉": "881", "望安鄉": "882", "七美鄉": "883",
        "白沙鄉": "884", "湖西鄉": "885",
    },
    "金門縣": {
        "金沙鎮": "890", "金湖鎮": "891", "金寧鄉": "892", "金城鎮": "893",
        "烈嶼鄉": "894", "烏坵鄉": "896",
    },
    "連江縣": {
        "南竿鄉": "209", "北竿鄉": "210", "莒光鄉": "211", "東引鄉": "212",
    },
}

# 排序代碼轉換
SORT_ORDER_MAP: Dict[str, str] = {
    "default": "default",
    "price_asc": "price-asc",
    "price-asc": "price-asc",
    "price_desc": "price-desc",
    "price-desc": "price-desc",
    "area_asc": "area-asc",
    "area-asc": "area-asc",
    "area_desc": "area-desc",
    "area-desc": "area-desc",
}


def resolve_sinyi_zipcodes(
    region_id: Optional[int] = None,
    region_name: Optional[str] = None,
    section_name: Optional[str] = None,
) -> List[str]:
    """解析縣市或行政區條件為信義房屋接受之 3 碼郵遞區號清單 (retRange)

    優先級別：
    1. 若指定具體行政區 (section_name)，優先精準鎖定該行政區之單一郵遞區號。
    2. 若僅指定縣市 (region_id 或 region_name)，返回該縣市下轄之所有行政區郵遞區號清單。
    3. 若皆未指定，預設返回台北市全區 12 區代碼。
    """
    target_city = "台北市"
    if region_id is not None:
        target_city = Region.to_chinese_name(region_id)
    elif region_name:
        # 兼容台/臺
        target_city = region_name.replace("臺", "台")

    # 取得該縣市字典
    city_districts = TAIWAN_DISTRICT_ZIPCODES.get(target_city)
    if not city_districts:
        # 再次嘗試台/臺互換
        alt_city = target_city.replace("台", "臺")
        city_districts = TAIWAN_DISTRICT_ZIPCODES.get(alt_city, TAIWAN_DISTRICT_ZIPCODES["台北市"])

    # 1. 若有具體行政區名稱
    if section_name:
        clean_section = section_name.strip()
        # 精準匹配
        if clean_section in city_districts:
            return [city_districts[clean_section]]
        # 模糊前綴匹配 (例如 "大安" 匹配 "大安區")
        for dist, code in city_districts.items():
            if clean_section in dist or dist.startswith(clean_section):
                return [code]

    # 2. 全縣市郵遞區號清單 (去重保序)
    seen = set()
    result: List[str] = []
    for code in city_districts.values():
        if code not in seen:
            seen.add(code)
            result.append(code)
    return result


def resolve_sinyi_price_payload(
    min_price_wan: Optional[int] = None,
    max_price_wan: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """將總價範圍條件轉換為信義房屋 PriceRequest 物件

    信義格式: {"priceType": 2, "priceRange": ["{min}-{max}"]}
    """
    if min_price_wan is None and max_price_wan is None:
        return None

    min_p = int(min_price_wan) if min_price_wan is not None else "0"
    max_p = int(max_price_wan) if max_price_wan is not None else "99999"

    return {
        "priceType": 2,
        "priceRange": [f"{min_p}-{max_p}"],
    }


def resolve_sinyi_age_payload(
    min_age_years: Optional[float] = None,
    max_age_years: Optional[float] = None,
) -> Optional[List[str]]:
    """將屋齡範圍條件轉換為信義房屋 houseAge 清單

    信義支援區間: ["min-5", "5-10", "10-20", "20-30", "30-max"]
    """
    if min_age_years is None and max_age_years is None:
        return None

    min_age = min_age_years if min_age_years is not None else 0.0
    max_age = max_age_years if max_age_years is not None else 999.0

    selected_ranges: List[str] = []
    # 判斷查詢區間 [min_age, max_age] 與各屋齡區間之實質交集
    if min_age < 5.0 and max_age > 0.0:
        selected_ranges.append("min-5")
    if min_age < 10.0 and max_age > 5.0:
        selected_ranges.append("5-10")
    if min_age < 20.0 and max_age > 10.0:
        selected_ranges.append("10-20")
    if min_age < 30.0 and max_age > 20.0:
        selected_ranges.append("20-30")
    if max_age > 30.0:
        selected_ranges.append("30-max")

    return selected_ranges if selected_ranges else None


def build_filter_object_payload(query: SaleHouseSearchQuery) -> Dict[str, Any]:
    """將 SaleHouseSearchQuery 轉換為信義房屋 /filterObject.php 之完整明文 Request 酬載"""
    # 1. 行政區郵遞區號
    region_name = getattr(query, "region_name", None)
    section_name = getattr(query, "section_name", None)
    ret_range = resolve_sinyi_zipcodes(
        region_id=query.region_id,
        region_name=region_name,
        section_name=section_name,
    )

    # 2. 篩選字典
    filter_obj: Dict[str, Any] = {
        "retType": 2,  # 固定為 2 (中古屋買賣)
        "retRange": ret_range,
        "floor": None,
    }

    # 關鍵字
    if query.keywords:
        filter_obj["keyword"] = {"keyword": query.keywords.strip()}

    # 屋齡
    age_ranges = resolve_sinyi_age_payload(query.min_age_years, query.max_age_years)
    if age_ranges:
        filter_obj["houseAge"] = age_ranges

    # 價格
    price_obj = resolve_sinyi_price_payload(query.min_price_wan, query.max_price_wan)
    if price_obj:
        filter_obj["price"] = price_obj

    # 3. 排序代碼
    sort_code = "default"
    if query.sort_order and query.sort_order in SORT_ORDER_MAP:
        sort_code = SORT_ORDER_MAP[query.sort_order]

    return {
        "page": query.page,
        "pageCnt": query.page_size,
        "sort": sort_code,
        "filter": filter_obj,
    }
