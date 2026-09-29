"""HouseLensAPI - 房產物件去重與實體消歧服務 (Property Deduplication Service)

純數學與精確整數比對引擎：
- 樓層：純整數相等性比對 O(1)
- 房數：純整數相等性比對 O(1)
- 坪數：浮點數誤差容許度百分比計算 (|area1 - area2| <= max(area1, area2) * tolerance)
- 社區：字串完全相符
零字串正則、零未清洗雜質！
"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field

from src.domain.sale_house import NormalizedSaleListing, NormalizedSalePropertyDetail
from src.storage.interfaces import IPropertyRepository


class DeduplicationResult(BaseModel):
    """物件重複性比對評估報告"""

    is_duplicate: bool = False
    matched_property_id: Optional[str] = None
    confidence_score: float = 0.0
    match_reasons: List[str] = Field(default_factory=list)


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
    """跨平台房產物件實體去重服務 (純數值比對)"""

    def __init__(self, area_tolerance_pct: float = 0.02):
        self.area_tolerance_pct = area_tolerance_pct

    async def evaluate_candidate(
        self,
        candidate: Union[NormalizedSaleListing, NormalizedSalePropertyDetail],
        repository: IPropertyRepository,
    ) -> DeduplicationResult:
        """評估傳入之中古屋清單或詳情是否在庫內已存在相同之物理實體"""
        community_name = candidate.community_name
        floor_current = candidate.floor_current
        rooms = candidate.rooms
        total_area_pin = candidate.total_area_pin

        matched = await repository.find_duplicate_candidate(
            community_name=community_name,
            floor_current=floor_current,
            rooms=rooms,
            total_area_pin=total_area_pin,
            area_tolerance_pct=self.area_tolerance_pct,
        )

        if not matched:
            return DeduplicationResult(
                is_duplicate=False,
                matched_property_id=None,
                confidence_score=0.0,
                match_reasons=[],
            )

        # 純數值計算信心分數
        reasons = []
        score = 0.0

        if community_name and matched.community_name == community_name:
            score += 0.4
            reasons.append(f"社區名稱完全相符: {community_name}")

        if floor_current is not None and matched.floor_current is not None and floor_current == matched.floor_current:
            score += 0.3
            reasons.append(f"所在樓層完全相符: {floor_current}F")

        if (
            total_area_pin is not None
            and matched.total_area_pin is not None
            and is_area_compatible(total_area_pin, matched.total_area_pin, self.area_tolerance_pct)
        ):
            score += 0.2
            reasons.append(
                f"權狀坪數相符 (容差 {self.area_tolerance_pct * 100}%): {total_area_pin}坪 vs {matched.total_area_pin}坪"
            )

        if rooms is not None and matched.rooms is not None and rooms == matched.rooms:
            score += 0.1
            reasons.append(f"格局房數完全相符: {rooms}房")

        return DeduplicationResult(
            is_duplicate=score >= 0.7,
            matched_property_id=matched.id,
            confidence_score=round(score, 2),
            match_reasons=reasons,
        )
