"""HouseLensAPI - 中古屋社區關聯補齊與兩階段消歧服務 (Community Resolution Service)

純淨架構領域服務：
1. 本地快速對齊 (Local Reconciliation): 0 網路請求快速扣合本地已有社區。
2. 遠端兩層式探索 (Remote Two-Tier Discovery): 透過社區清單 API 取得第一層 (包含坐標、身分、地址) 快照，
   再拉取社區詳情補齊第二層深層硬體規格，徹底遵循統一兩層式 SSOT，絕不裸調詳情 API 造成欄位遺漏。
3. 嚴格消歧比對 (Strict Disambiguation): 行政區吻合度檢驗、名稱精確比對、多候選歧義主動保護，防止老公寓與透天誤配。
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from src.core.registry import ProviderRegistry, registry
from src.domain.community import CommunitySearchQuery, NormalizedCommunitySummary
from src.domain.enums import Region
from src.storage.database import DatabaseManager, db_manager
from src.storage.repositories.community_repo import CommunityRepository
from src.storage.repositories.property_repo import PropertyRepository

logger = logging.getLogger(__name__)


class MatchStatus(str, Enum):
    """消歧與對齊狀態枚舉"""
    LOCAL_LINKED = "LOCAL_LINKED"          # 本地既有社區直接對齊成功
    REMOTE_RESOLVED = "REMOTE_RESOLVED"    # 遠端清單探索並補拉詳情入庫成功
    NO_COMMUNITY = "NO_COMMUNITY"          # 客觀無社區物件 (安全略過)
    NOT_FOUND = "NOT_FOUND"                # 遠端清單無匹配結果
    AMBIGUOUS = "AMBIGUOUS"                # 存在 2 個以上相似社區，為防誤配已主動略過


class CommunityMatchResult(BaseModel):
    """單一目標消歧比對結果值物件"""
    status: MatchStatus
    matched_community_uuid: Optional[str] = None
    matched_external_id: Optional[str] = None
    matched_name: Optional[str] = None
    confidence_score: float = 0.0
    reason: str = ""


class CommunityResolutionTarget(BaseModel):
    """待補齊之記憶體聚合任務實體"""
    provider_id: str
    region_name: str
    section_name: Optional[str] = None
    community_name: Optional[str] = None
    external_community_id: Optional[str] = None
    property_ids: List[str] = Field(default_factory=list)
    sample_title: Optional[str] = None


class CommunityResolutionOptions(BaseModel):
    """補齊任務執行參數規格"""
    provider_id: str = Field(default="591", description="來源平台代碼")
    region_name: Optional[str] = Field(default=None, description="指定限定縣市名稱 (如 台北市)")
    limit: Optional[int] = Field(default=None, description="掃描處理的中古屋上限數量")
    dry_run: bool = Field(default=False, description="是否為乾跑預演模式 (不寫入資料庫)")


class CommunityResolutionReport(BaseModel):
    """補齊執行統計報告實體"""
    scanned_properties_count: int = 0
    distinct_targets_count: int = 0
    locally_linked_properties_count: int = 0
    remotely_resolved_properties_count: int = 0
    persisted_communities_count: int = 0
    ambiguous_targets_count: int = 0
    not_found_targets_count: int = 0
    skipped_no_community_count: int = 0
    elapsed_seconds: float = 0.0
    details: List[Dict[str, Any]] = Field(default_factory=list)


class CommunityResolutionService:
    """中古屋社區消歧與兩層式補齊應用服務"""

    def __init__(
        self,
        provider_registry: ProviderRegistry = registry,
        database: DatabaseManager = db_manager,
    ):
        self.registry = provider_registry
        self.db = database

    async def resolve_unlinked_properties(
        self,
        options: CommunityResolutionOptions,
    ) -> CommunityResolutionReport:
        """執行中古屋社區消歧與批次外鍵補齊核心流程"""
        start_time = time.time()
        report = CommunityResolutionReport()
        provider = self.registry.get_provider(options.provider_id)

        # 1. 檢索未關聯社區之中古屋
        async with self.db.session() as session:
            prop_repo = PropertyRepository(session)
            unlinked_props = await prop_repo.get_unlinked_community_properties(
                provider_id=options.provider_id,
                region_name=options.region_name,
                limit=options.limit,
            )

        report.scanned_properties_count = len(unlinked_props)
        if not unlinked_props:
            report.elapsed_seconds = round(time.time() - start_time, 2)
            return report

        # 2. 記憶體去重聚合 (Deduplicated Aggregation)
        # 以 (external_community_id) 或 (region, section, community_name) 歸戶
        targets_map: Dict[str, CommunityResolutionTarget] = {}
        for prop in unlinked_props:
            clean_cname = prop.community_name.strip() if prop.community_name else None
            clean_ext_id = prop.external_community_id.strip() if prop.external_community_id else None

            # 若無社區代碼且無社區名稱，屬無社區物件
            if not clean_ext_id and not clean_cname:
                report.skipped_no_community_count += 1
                continue

            if clean_ext_id:
                agg_key = f"id:{options.provider_id}:{clean_ext_id}"
            else:
                agg_key = f"name:{options.provider_id}:{prop.region_name}:{prop.section_name or ''}:{clean_cname}"

            if agg_key not in targets_map:
                targets_map[agg_key] = CommunityResolutionTarget(
                    provider_id=options.provider_id,
                    region_name=prop.region_name,
                    section_name=prop.section_name,
                    community_name=clean_cname,
                    external_community_id=clean_ext_id,
                    sample_title=prop.title,
                )
            targets_map[agg_key].property_ids.append(prop.id)

        report.distinct_targets_count = len(targets_map)

        # 3. 逐一處理聚合任務
        for agg_key, target in targets_map.items():
            result = await self._resolve_single_target(target, provider, dry_run=options.dry_run)
            report.details.append({
                "target_name": target.community_name or target.external_community_id,
                "region": f"{target.region_name} {target.section_name or ''}".strip(),
                "properties_count": len(target.property_ids),
                "status": result.status.value,
                "matched_name": result.matched_name,
                "matched_external_id": result.matched_external_id,
                "reason": result.reason,
            })

            if result.status == MatchStatus.LOCAL_LINKED:
                report.locally_linked_properties_count += len(target.property_ids)
            elif result.status == MatchStatus.REMOTE_RESOLVED:
                report.remotely_resolved_properties_count += len(target.property_ids)
                report.persisted_communities_count += 1
            elif result.status == MatchStatus.AMBIGUOUS:
                report.ambiguous_targets_count += 1
            elif result.status == MatchStatus.NOT_FOUND:
                report.not_found_targets_count += 1

        report.elapsed_seconds = round(time.time() - start_time, 2)
        return report

    async def _resolve_single_target(
        self,
        target: CommunityResolutionTarget,
        provider: Any,
        dry_run: bool = False,
    ) -> CommunityMatchResult:
        """針對單一聚合目標執行兩階段消歧與關聯"""

        # --- 階段一：本地快速對齊 (Local Reconciliation, 0 HTTP 請求) ---
        async with self.db.session() as session:
            comm_repo = CommunityRepository(session)
            prop_repo = PropertyRepository(session)

            # 1. 依 external_community_id 查詢本地
            if target.external_community_id:
                local_comm = await comm_repo.get_by_external_id(
                    provider_id=target.provider_id,
                    external_community_id=target.external_community_id,
                )
                if local_comm:
                    if not dry_run:
                        await prop_repo.batch_update_community_links(
                            property_ids=target.property_ids,
                            community_uuid=local_comm.id,
                            external_community_id=local_comm.external_community_id,
                        )
                    return CommunityMatchResult(
                        status=MatchStatus.LOCAL_LINKED,
                        matched_community_uuid=local_comm.id,
                        matched_external_id=local_comm.external_community_id,
                        matched_name=local_comm.name,
                        confidence_score=1.0,
                        reason="本地資料庫依外部代碼精準命中",
                    )

            # 2. 依同行政區與名稱查詢本地
            if target.community_name:
                local_candidates = await comm_repo.search(
                    region=target.region_name,
                    section=target.section_name,
                    keyword=target.community_name,
                    limit=5,
                )
                exact_local = [
                    c for c in local_candidates
                    if self._is_name_exact_match(c.name, target.community_name)
                ]
                if len(exact_local) == 1:
                    matched = exact_local[0]
                    if not dry_run:
                        await prop_repo.batch_update_community_links(
                            property_ids=target.property_ids,
                            community_uuid=matched.id,
                            external_community_id=matched.external_community_id,
                        )
                    return CommunityMatchResult(
                        status=MatchStatus.LOCAL_LINKED,
                        matched_community_uuid=matched.id,
                        matched_external_id=matched.external_community_id,
                        matched_name=matched.name,
                        confidence_score=0.95,
                        reason="本地資料庫依同行政區名稱完全相符命中",
                    )

        # --- 階段二：遠端清單探索與兩層式入庫 (Remote Two-Tier Discovery) ---
        keyword = target.community_name or target.external_community_id
        if not keyword:
            return CommunityMatchResult(
                status=MatchStatus.NO_COMMUNITY,
                reason="無有效社區名稱或外部代碼，跳過遠端探索",
            )

        region_code = None
        if target.region_name:
            try:
                region_code = Region.from_name(target.region_name).value
            except Exception:
                region_code = None

        search_query = CommunitySearchQuery(
            region_id=region_code,
            keywords=keyword,
            page=1,
            page_size=20,
        )

        try:
            page_res = await provider.community.search_communities(search_query)
        except Exception as e:
            logger.error(f"調用社區搜尋端點失敗 (關鍵字: {keyword}): {e}")
            return CommunityMatchResult(
                status=MatchStatus.NOT_FOUND,
                reason=f"遠端搜尋請求失敗: {e}",
            )

        items = page_res.items
        if not items:
            return CommunityMatchResult(
                status=MatchStatus.NOT_FOUND,
                reason="遠端清單搜尋無回傳結果",
            )

        # 嚴格消歧比對 (Strict Disambiguation Matrix)
        matched_summary: Optional[NormalizedCommunitySummary] = None

        if target.external_community_id:
            # 若有外部代碼，在清單中比對 ID
            id_matches = [
                it for it in items
                if str(it.external_community_id).lstrip("C") == str(target.external_community_id).lstrip("C")
            ]
            if id_matches:
                matched_summary = id_matches[0]
        else:
            # 依同行政區與名稱完全吻合比對
            exact_name_matches = [
                it for it in items
                if self._is_name_exact_match(it.community_name, target.community_name)
            ]

            # 進一步校驗行政區
            if target.section_name:
                section_matches = [
                    it for it in exact_name_matches
                    if it.section_name == target.section_name or (it.address and target.section_name in it.address)
                ]
            else:
                section_matches = exact_name_matches

            if len(section_matches) == 1:
                matched_summary = section_matches[0]
            elif len(section_matches) > 1:
                return CommunityMatchResult(
                    status=MatchStatus.AMBIGUOUS,
                    reason=f"同名同區存在 {len(section_matches)} 個不同社區代碼，主動防護跳過",
                )

        if not matched_summary:
            return CommunityMatchResult(
                status=MatchStatus.NOT_FOUND,
                reason="遠端搜尋結果無符合嚴格名稱與行政區之社區",
            )

        # 兩層式入庫保證：取得第二層深層硬體規格
        try:
            detail = await provider.community.get_community_detail(
                matched_summary.external_community_id,
                summary=matched_summary,
            )
        except Exception as e:
            logger.error(f"調用社區詳情端點失敗 (ID: {matched_summary.external_community_id}): {e}")
            return CommunityMatchResult(
                status=MatchStatus.NOT_FOUND,
                reason=f"遠端詳情取得失敗: {e}",
            )

        saved_community_id = None
        if not dry_run:
            async with self.db.session() as session:
                comm_repo = CommunityRepository(session)
                prop_repo = PropertyRepository(session)
                saved_comm = await comm_repo.upsert_from_detail(detail, provider_id=target.provider_id)
                saved_community_id = saved_comm.id

                await prop_repo.batch_update_community_links(
                    property_ids=target.property_ids,
                    community_uuid=saved_comm.id,
                    external_community_id=matched_summary.external_community_id,
                )

        return CommunityMatchResult(
            status=MatchStatus.REMOTE_RESOLVED,
            matched_community_uuid=saved_community_id,
            matched_external_id=matched_summary.external_community_id,
            matched_name=matched_summary.community_name,
            confidence_score=0.98,
            reason="遠端兩層式清單探索與詳情補齊成功",
        )

    @staticmethod
    def _is_name_exact_match(name_a: Optional[str], name_b: Optional[str]) -> bool:
        """嚴格名稱相符性檢驗 (剔除標點符號與空白，但拒絕任意子字串模糊匹配)"""
        if not name_a or not name_b:
            return False

        def clean(s: str) -> str:
            return s.replace(" ", "").replace("-", "").replace("—", "").replace("(", "").replace(")", "").strip()

        return clean(name_a) == clean(name_b)
