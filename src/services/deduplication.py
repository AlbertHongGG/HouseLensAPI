"""HouseLensAPI - 房產物件去重與實體消歧服務 (Property Deduplication Service)"""

from typing import List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from src.domain.sale_house import SaleHouseDetail, SaleHouseSummary
from src.storage.interfaces import IPropertyRepository
from src.storage.models.property import PropertyTable


class DeduplicationResult(BaseModel):
    """物件重複性比對評估報告"""

    is_duplicate: bool = False
    matched_property_id: Optional[str] = None
    confidence_score: float = 0.0
    match_reasons: List[str] = Field(default_factory=list)


def normalize_floor(floor_str: Optional[str]) -> Optional[str]:
    """正規化樓層，例如 '2F/24F'、'2樓'、'2' 轉為 '2'"""
    if not floor_str:
        return None
    first = floor_str.split("/")[0].strip()
    clean = first.upper().replace("F", "").replace("樓", "").strip()
    return clean if clean else floor_str


def is_layout_compatible(l1: Optional[str], l2: Optional[str]) -> bool:
    """判斷兩種格局描述是否相容 (例如 '3房2廳2衛' 與 '3房2廳')"""
    if not l1 or not l2:
        return True
    if l1 == l2:
        return True
    if l1.startswith(l2) or l2.startswith(l1):
        return True
    if "房" in l1 and "房" in l2:
        r1 = l1.split("房")[0].strip()
        r2 = l2.split("房")[0].strip()
        return r1 == r2
    return False


def is_area_compatible(
    area1: Optional[float], area2: Optional[float], tolerance_pct: float = 0.02
) -> bool:
    """比對兩面積坪數是否在指定誤差容許度內 (預設 ±2%)"""
    if area1 is None or area2 is None:
        return False
    diff = abs(area1 - area2)
    max_allowed = max(area1, area2) * tolerance_pct
    return diff <= max_allowed


class PropertyDeduplicationService:
    """跨平台房產物件實體去重服務"""

    def __init__(self, area_tolerance_pct: float = 0.02):
        self.area_tolerance_pct = area_tolerance_pct

    async def evaluate_candidate(
        self,
        candidate: Union[SaleHouseSummary, SaleHouseDetail],
        repository: IPropertyRepository,
    ) -> DeduplicationResult:
        """評估傳入之中古屋清單或詳情是否在庫內已存在相同之物理實體"""
        # 擷取特徵欄位
        if isinstance(candidate, SaleHouseSummary):
            community_name = candidate.community_name
            floor = candidate.floor
            total_area = candidate.total_area
            layout = candidate.layout
            address = candidate.address
        else:
            community_name = None  # Detail 通常從關聯或地址取得
            floor = candidate.floor
            total_area = candidate.total_area
            layout = candidate.layout
            address = candidate.address

        matched = await repository.find_duplicate_candidate(
            community_name=community_name,
            floor=floor,
            total_area=total_area,
            layout=layout,
            area_tolerance_pct=self.area_tolerance_pct,
        )

        if not matched:
            return DeduplicationResult(
                is_duplicate=False,
                matched_property_id=None,
                confidence_score=0.0,
                match_reasons=[],
            )

        # 計算信心分數
        reasons = []
        score = 0.0

        if community_name and matched.community_name == community_name:
            score += 0.4
            reasons.append(f"社區名稱完全相符: {community_name}")

        if floor and normalize_floor(floor) == normalize_floor(matched.floor):
            score += 0.3
            reasons.append(f"所在樓層相符: {floor} ~ {matched.floor}")

        if (
            total_area is not None
            and matched.total_area is not None
            and is_area_compatible(total_area, matched.total_area, self.area_tolerance_pct)
        ):
            score += 0.2
            reasons.append(f"權狀坪數相符 (容差 {self.area_tolerance_pct*100}%): {total_area} vs {matched.total_area}")

        if layout and is_layout_compatible(layout, matched.layout):
            score += 0.1
            reasons.append(f"格局規劃相容: {layout} ~ {matched.layout}")

        return DeduplicationResult(
            is_duplicate=score >= 0.7,
            matched_property_id=matched.id,
            confidence_score=round(score, 2),
            match_reasons=reasons,
        )
