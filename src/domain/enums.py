"""HouseLensAPI - 核心領域枚舉定義 (Domain Enums)

定義跨平台統一之標準常數，包括行政縣市、建物類型、成屋/預售狀態、建築座向與屋齡範圍。
"""

from enum import Enum, IntEnum


class Region(IntEnum):
    """台灣主要行政縣市代碼 (對應標準縣市代碼)"""
    TAIPEI = 1          # 台北市
    NEW_TAIPEI = 3      # 新北市
    TAOYUAN = 6         # 桃園市
    HSINCHU_CITY = 4    # 新竹市
    HSINCHU_COUNTY = 5  # 新竹縣
    TAICHUNG = 8        # 台中市
    TAINAN = 21         # 台南市
    KAOHSIUNG = 17      # 高雄市
    KEELUNG = 2         # 基隆市
    YILAN = 22          # 宜蘭縣
    MIAOLI = 7          # 苗栗縣
    CHANGHUA = 10       # 彰化縣
    NANTOU = 11         # 南投縣
    YUNLIN = 12         # 雲林縣
    CHIAYI_CITY = 13    # 嘉義市
    CHIAYI_COUNTY = 14  # 嘉義縣
    PINGTUNG = 19       # 屏東縣
    HUALIEN = 23        # 花蓮縣
    TAITUNG = 24        # 台東縣
    PENGHU = 25         # 澎湖縣
    KINMEN = 26         # 金門縣
    LIENCHIANG = 27     # 連江縣

    @classmethod
    def from_name(cls, name: str) -> "Region":
        """根據縣市名稱取得代碼"""
        name_map = {
            "台北市": cls.TAIPEI, "臺北市": cls.TAIPEI,
            "新北市": cls.NEW_TAIPEI,
            "桃園市": cls.TAOYUAN,
            "新竹市": cls.HSINCHU_CITY,
            "新竹縣": cls.HSINCHU_COUNTY,
            "台中市": cls.TAICHUNG, "臺中市": cls.TAICHUNG,
            "台南市": cls.TAINAN, "臺南市": cls.TAINAN,
            "高雄市": cls.KAOHSIUNG,
            "基隆市": cls.KEELUNG,
            "宜蘭縣": cls.YILAN,
            "苗栗縣": cls.MIAOLI,
            "彰化縣": cls.CHANGHUA,
            "南投縣": cls.NANTOU,
            "雲林縣": cls.YUNLIN,
            "嘉義市": cls.CHIAYI_CITY,
            "嘉義縣": cls.CHIAYI_COUNTY,
            "屏東縣": cls.PINGTUNG,
            "花蓮縣": cls.HUALIEN,
            "台東縣": cls.TAITUNG, "臺東縣": cls.TAITUNG,
            "澎湖縣": cls.PENGHU,
            "金門縣": cls.KINMEN,
            "連江縣": cls.LIENCHIANG,
        }
        if name not in name_map:
            raise ValueError(f"未知的縣市名稱: {name}")
        return name_map[name]

    @property
    def chinese_name(self) -> str:
        """傳回標準台灣縣市中文全名 (例如: '台北市', '新北市')"""
        chinese_names = {
            self.TAIPEI: "台北市",
            self.NEW_TAIPEI: "新北市",
            self.TAOYUAN: "桃園市",
            self.HSINCHU_CITY: "新竹市",
            self.HSINCHU_COUNTY: "新竹縣",
            self.TAICHUNG: "台中市",
            self.TAINAN: "台南市",
            self.KAOHSIUNG: "高雄市",
            self.KEELUNG: "基隆市",
            self.YILAN: "宜蘭縣",
            self.MIAOLI: "苗栗縣",
            self.CHANGHUA: "彰化縣",
            self.NANTOU: "南投縣",
            self.YUNLIN: "雲林縣",
            self.CHIAYI_CITY: "嘉義市",
            self.CHIAYI_COUNTY: "嘉義縣",
            self.PINGTUNG: "屏東縣",
            self.HUALIEN: "花蓮縣",
            self.TAITUNG: "台東縣",
            self.PENGHU: "澎湖縣",
            self.KINMEN: "金門縣",
            self.LIENCHIANG: "連江縣",
        }
        return chinese_names.get(self, "台北市")

    @classmethod
    def to_chinese_name(cls, val: int) -> str:
        """將整數代碼安全轉換為標準中文縣市全名 (無效值回退 '台北市')"""
        try:
            return cls(val).chinese_name
        except (ValueError, TypeError):
            return "台北市"


class BuildingType(str, Enum):
    """跨平台統一建物類型"""
    RESIDENTIAL = "住宅"
    STUDIO = "套房"
    APARTMENT = "公寓"
    ELEVATOR_BUILDING = "電梯大樓"
    MANSION = "華廈"
    VILLA = "別墅"
    TOWNHOUSE = "透天厝"
    STORE = "店面"
    OFFICE = "辦公"
    FACTORY = "廠房"
    PARKING = "車位"
    LAND = "土地"
    OTHER = "其他"


class NewHouseStatus(str, Enum):
    """新建案工程期程/銷售狀態"""
    PRE_SALE = "預售屋"
    NEW_CONSTRUCTION = "新成屋"
    UPCOMING = "即將公開"


class AgeRange(str, Enum):
    """屋齡篩選代碼"""
    AGE_0_5 = "0_5"     # 0-5年
    AGE_5_10 = "5_10"   # 5-10年
    AGE_10_20 = "10_20" # 10-20年
    AGE_20_30 = "20_30" # 20-30年
    AGE_30_PLUS = "30_" # 30年以上
