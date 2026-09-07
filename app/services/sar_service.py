"""
QuantumAML Nexus - Suspicious Activity Reporting (SAR / STR) Service
=====================================================================

Implements the thread-safe, high-throughput Suspicious Activity Report
management service under the Prevention of Money Laundering Act (PMLA)
and FIU-IND FINnet 2.0 / FINGate regulatory standards.

Features:
- Thread-safe in-memory case repository backed by asyncio.Lock.
- 5-Minute (300-second) rolling-window ring deduplication engine to prevent
  alert fatigue by aggregating rapid-fire structuring transactions (e.g. mule rings
  transferring amounts under ₹50,000) into a single consolidated case file.
- Dynamic legal narrative synthesizer for FIU-IND grounds of suspicion.
- Case lifecycle management (review, escalation, regulatory filing, dismissal).
- Module-level singleton export: `sar_service = SARService()`.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.sar import (
    CaseStatus,
    GroundsOfSuspicion,
    MLTelemetry,
    PaymentRail,
    ReportingEntityInfo,
    ReportingEntityType,
    RiskTier,
    SARCaseRecord,
    SuspectEntityProfile,
    SuspicionTypology,
    TransactionAuditRecord,
    calculate_fiu_deadline,
    generate_sar_id,
)

logger = logging.getLogger("SARService")


class SARService:
    """
    Thread-safe Suspicious Activity Report management service with
    5-minute rolling-window ring deduplication and regulatory narrative synthesis.
    """

    DEDUP_WINDOW_SECONDS: float = 300.0  # 5-minute rolling ring deduplication window

    def __init__(self):
        # Primary index: keyed by sar_id
        self._cases: Dict[str, SARCaseRecord] = {}
        # Secondary index: maps normalized suspect entity identifier -> active sar_id
        self._active_ring_index: Dict[str, str] = {}
        # Tracks epoch timestamp of the most recent activity in each ring/case
        self._ring_last_active: Dict[str, float] = {}
        # Concurrency lock for thread-safe operations
        self._lock = asyncio.Lock()

    # --------------------------------------------------------------------------
    # Narrative Synthesizer
    # --------------------------------------------------------------------------
    def _synthesize_narrative(
        self,
        typology: SuspicionTypology,
        tx_records: List[TransactionAuditRecord],
        suspect: SuspectEntityProfile,
        counterparty: Optional[SuspectEntityProfile],
        ml_result: Dict[str, Any],
        avg_risk_score: float,
        latest_tx_payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Synthesizes standardized, legally sound grounds of suspicion compliant
        with FIU-IND FINnet 2.0 / PMLA standards.
        """
        payload = latest_tx_payload or {}
        num_txs = len(tx_records)
        latest_tx = tx_records[-1] if tx_records else None
        earliest_tx = tx_records[0] if tx_records else None

        # Determine payment rail representation
        rails = list({tx.rail for tx in tx_records if tx.rail})
        rail_str = ", ".join(rails) if rails else (str(payload.get("rail") or payload.get("payment_format") or "UPI"))

        # Calculate total exposure in INR
        total_inr = sum(tx.amount for tx in tx_records if tx.currency.upper() == "INR")
        total_inr_formatted = f"{total_inr:,.2f}"

        # Target entity resolution: in structuring, target is the aggregator receiving the deposits (account_to)
        target_entity = (
            payload.get("account_to")
            or payload.get("to_entity")
            or payload.get("to_address")
            or (latest_tx.counterparty_to if latest_tx else None)
            or (counterparty.entity_identifier if counterparty else None)
            or suspect.entity_identifier
            or "ANONYMOUS_COUNTERPARTY"
        )

        # Elapsed window in seconds across transactions
        if earliest_tx and latest_tx and len(tx_records) > 1:
            window_seconds = int(abs((latest_tx.timestamp - earliest_tx.timestamp).total_seconds()))
            if window_seconds == 0:
                window_seconds = int(self.DEDUP_WINDOW_SECONDS)
        else:
            window_seconds = int(self.DEDUP_WINDOW_SECONDS)

        # Typology-specific synthesis matching statutory specs
        if typology == SuspicionTypology.IN_TYP_STRUCT:
            return (
                f"Coordinated structuring pattern detected: {num_txs} transactions "
                f"aggregating to \u20b9{total_inr_formatted} executed across {rail_str} "
                f"within {window_seconds}s to counterparty {target_entity}, intentionally structured "
                f"below the statutory \u20b950,000 PAN reporting threshold. "
                f"Model confidence: {avg_risk_score:.2f}."
            )

        elif typology == SuspicionTypology.IN_TYP_HAWALA:
            amount_val = latest_tx.amount if latest_tx else float(payload.get("amount", total_inr))
            amount_formatted = f"{amount_val:,.2f}"
            corp_entity = (
                payload.get("entity_name")
                or suspect.entity_name
                or suspect.entity_identifier
                or "Commercial Shell Entity"
            )
            branch_ifsc = (
                payload.get("branch_ifsc")
                or payload.get("ifsc")
                or suspect.institution_code
                or "DOM_CORP_BRANCH"
            )
            return (
                f"High-value wire anomaly: Uncharacteristic {rail_str} transfer of "
                f"\u20b9{amount_formatted} routed via corporate entity {corp_entity} "
                f"domiciled at branch {branch_ifsc} exceeding baseline profile thresholds."
            )

        elif typology == SuspicionTypology.IN_TYP_VDA_MIX:
            tx_hash = (
                (latest_tx.transaction_id if latest_tx else None)
                or payload.get("tx_hash")
                or payload.get("node_id")
                or payload.get("transaction_id")
                or "0xUNKNOWN_HASH"
            )
            num_inputs = int(payload.get("num_inputs") or payload.get("inputs_count") or 5)
            num_outputs = int(payload.get("num_outputs") or payload.get("outputs_count") or 8)
            return (
                f"Illicit crypto hop detected: High-velocity peeling or mixer signature "
                f"identified across {num_inputs} inputs and {num_outputs} outputs "
                f"for transaction hash {tx_hash}."
            )

        elif typology == SuspicionTypology.IN_TYP_MULE:
            return (
                f"Mule account burst detected: High-velocity fund dispersion across {rail_str} "
                f"totaling \u20b9{total_inr_formatted} following dormancy period. "
                f"Counterparty: {target_entity}. Model confidence: {avg_risk_score:.2f}."
            )

        # Fallback compliant narrative
        return (
            f"Suspicious activity alert: {num_txs} transactions aggregating to "
            f"\u20b9{total_inr_formatted} flagged under typology {typology.value if hasattr(typology, 'value') else typology}. "
            f"Suspect entity: {suspect.entity_identifier}. Model confidence: {avg_risk_score:.2f}."
        )

    # --------------------------------------------------------------------------
    # Suspect Entity Identification Helper
    # --------------------------------------------------------------------------
    def _extract_suspect_identifier(
        self,
        tx_payload: Dict[str, Any],
        typology: SuspicionTypology,
    ) -> Tuple[str, Optional[str]]:
        """
        Extracts the primary suspect entity identifier and counterparty identifier
        based on payload attributes, typology, and existing active rings.
        """
        # Explicit override if passed
        explicit_suspect = tx_payload.get("suspect_identifier")
        if explicit_suspect:
            c_to = (
                tx_payload.get("account_to")
                or tx_payload.get("counterparty_to")
                or tx_payload.get("to_entity")
                or tx_payload.get("to_address")
            )
            return str(explicit_suspect).strip(), (str(c_to).strip() if c_to else None)

        # Candidate entities from fiat / crypto payloads
        candidate_from = (
            tx_payload.get("account_from")
            or tx_payload.get("counterparty_from")
            or tx_payload.get("from_address")
            or tx_payload.get("from_entity")
            or tx_payload.get("node_id")
        )
        candidate_to = (
            tx_payload.get("account_to")
            or tx_payload.get("counterparty_to")
            or tx_payload.get("to_address")
            or tx_payload.get("to_entity")
        )

        c_from = str(candidate_from).strip() if candidate_from else None
        c_to = str(candidate_to).strip() if candidate_to else None

        # Check if an existing active ring matches either entity
        if c_to and c_to in self._active_ring_index:
            return c_to, c_from
        if c_from and c_from in self._active_ring_index:
            return c_from, c_to

        # Typology-specific suspect assignment:
        # In structuring rings (IN_TYP_STRUCT), the aggregator/funnel target (account_to)
        # is the central suspect consolidating smurfed transactions under ₹50,000.
        if typology == SuspicionTypology.IN_TYP_STRUCT:
            primary = c_to or c_from or "ANONYMOUS_AGGREGATOR"
            counterparty = c_from if primary == c_to else c_to
            return primary, counterparty

        # In mule draining (IN_TYP_MULE), the compromised account dispersing funds (account_from) is primary.
        if typology == SuspicionTypology.IN_TYP_MULE:
            primary = c_from or c_to or "ANONYMOUS_MULE"
            counterparty = c_to if primary == c_from else c_from
            return primary, counterparty

        # For Hawala or crypto forensics
        primary = c_from or c_to or (tx_payload.get("tx_hash") or "ANONYMOUS_ENTITY")
        counterparty = c_to if primary == c_from else c_from
        return primary, counterparty

    # --------------------------------------------------------------------------
    # Helper: Build TransactionAuditRecord
    # --------------------------------------------------------------------------
    def _build_audit_record(
        self,
        tx_payload: Dict[str, Any],
        ml_result: Dict[str, Any],
        suspect_id: str,
        counterparty_id: Optional[str],
    ) -> TransactionAuditRecord:
        """Constructs a compliant TransactionAuditRecord from payload and ML inference."""
        raw_tx_id = (
            tx_payload.get("transaction_id")
            or tx_payload.get("tx_id")
            or tx_payload.get("tx_hash")
            or tx_payload.get("node_id")
            or f"TXN-{uuid.uuid4().hex[:12].upper()}"
        )

        # Execution timestamp
        ts = tx_payload.get("timestamp")
        if isinstance(ts, str):
            try:
                tx_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                tx_time = datetime.now(timezone.utc)
        elif isinstance(ts, datetime):
            tx_time = ts
        else:
            tx_time = datetime.now(timezone.utc)

        # Payment Rail
        raw_rail = str(
            tx_payload.get("payment_format")
            or tx_payload.get("rail")
            or ("BTC" if "btc" in str(tx_payload.get("currency", "")).lower() else "UPI")
        ).upper()

        try:
            rail = PaymentRail(raw_rail)
        except ValueError:
            rail = PaymentRail.BTC if "BTC" in raw_rail else PaymentRail.UPI

        # Amount & Currency
        amount = float(
            tx_payload.get("amount")
            or tx_payload.get("btc_value")
            or tx_payload.get("value")
            or 1.0
        )
        currency = str(
            tx_payload.get("currency")
            or ("BTC" if rail in (PaymentRail.BTC, PaymentRail.ETH) else "INR")
        ).upper()

        risk_score = float(
            ml_result.get("risk_score")
            if ml_result.get("risk_score") is not None
            else tx_payload.get("risk_score", 0.85)
        )
        risk_score = max(0.0, min(1.0, risk_score))

        # Anomalies
        anomalies = list(
            tx_payload.get("detected_anomalies")
            or ml_result.get("anomalies")
            or ml_result.get("flags")
            or []
        )
        if ml_result.get("recommended_action") and ml_result["recommended_action"] not in anomalies:
            anomalies.append(ml_result["recommended_action"])

        c_from = (
            tx_payload.get("account_from")
            or tx_payload.get("counterparty_from")
            or tx_payload.get("from_address")
            or suspect_id
        )
        c_to = (
            tx_payload.get("account_to")
            or tx_payload.get("counterparty_to")
            or tx_payload.get("to_address")
            or (counterparty_id or "ANONYMOUS_BENEFICIARY")
        )

        return TransactionAuditRecord(
            transaction_id=str(raw_tx_id),
            timestamp=tx_time,
            rail=rail,
            amount=amount,
            currency=currency,
            counterparty_from=str(c_from),
            counterparty_to=str(c_to),
            risk_score=risk_score,
            detected_anomalies=anomalies,
        )

    # --------------------------------------------------------------------------
    # Core API 1: Create or Aggregate SAR (5-Minute Deduplication Engine)
    # --------------------------------------------------------------------------
    async def create_or_aggregate_sar(
        self,
        tx_payload: Dict[str, Any],
        ml_result: Dict[str, Any],
        typology: SuspicionTypology,
    ) -> SARCaseRecord:
        """
        Ingests flagged critical risk events and dynamically executes 5-minute
        rolling-window ring deduplication.

        - If an unfiled active case exists within 300 seconds for the suspect entity:
          Appends transaction, recalculates exposure and average risk, updates telemetry,
          extends the legal grounds of suspicion narrative, and resets the 300s window.
        - Otherwise:
          Creates a new SARCaseRecord, registers the active ring, and sets the 7 working-day
          FIU-IND filing deadline.
        """
        async with self._lock:
            current_time = time.time()
            suspect_id, counterparty_id = self._extract_suspect_identifier(tx_payload, typology)
            tx_record = self._build_audit_record(tx_payload, ml_result, suspect_id, counterparty_id)

            existing_sar_id = self._active_ring_index.get(suspect_id)
            is_active_case = False
            existing_case: Optional[SARCaseRecord] = None

            if existing_sar_id and existing_sar_id in self._cases:
                candidate_case = self._cases[existing_sar_id]
                # Unfiled check: status in PENDING_REVIEW or ESCALATED
                unfiled_statuses = {
                    CaseStatus.PENDING_REVIEW,
                    CaseStatus.ESCALATED,
                    CaseStatus.PENDING_REVIEW.value,
                    CaseStatus.ESCALATED.value,
                }
                is_unfiled = candidate_case.status in unfiled_statuses
                last_active = self._ring_last_active.get(existing_sar_id, 0.0)
                within_window = (current_time - last_active) <= self.DEDUP_WINDOW_SECONDS

                if is_unfiled and within_window:
                    is_active_case = True
                    existing_case = candidate_case
                elif not within_window:
                    # Rolling window expired; evict stale ring mapping
                    self._active_ring_index.pop(suspect_id, None)

            # ------------------------------------------------------------------
            # Case A: Active Case Exists within 300 Seconds (5 Minutes)
            # ------------------------------------------------------------------
            if is_active_case and existing_case is not None:
                logger.info(
                    "Aggregating transaction %s into active ring case %s (suspect=%s, window_remaining=%.1fs)",
                    tx_record.transaction_id,
                    existing_case.sar_id,
                    suspect_id,
                    self.DEDUP_WINDOW_SECONDS - (current_time - self._ring_last_active.get(existing_case.sar_id, current_time)),
                )

                # 1. Append transaction audit record
                existing_case.transactions.append(tx_record)

                # 2. Increment cumulative exposures
                if tx_record.currency.upper() == "INR":
                    existing_case.total_exposure_inr = round(
                        sum(tx.amount for tx in existing_case.transactions if tx.currency.upper() == "INR"),
                        2,
                    )
                elif tx_record.currency.upper() == "BTC":
                    btc_sum = sum(tx.amount for tx in existing_case.transactions if tx.currency.upper() == "BTC")
                    existing_case.total_exposure_btc = round(btc_sum, 6)

                # 3. Recalculate rolling average risk score
                avg_score = sum(tx.risk_score for tx in existing_case.transactions) / len(existing_case.transactions)

                # 4. Update ML telemetry feature importance and latency
                new_importance = (
                    ml_result.get("feature_importance")
                    or ml_result.get("top_features")
                    or {}
                )
                if new_importance:
                    existing_case.ml_telemetry.feature_importance.update(new_importance)

                new_latency = float(ml_result.get("latency_ms", 0.0))
                if new_latency > 0:
                    existing_case.ml_telemetry.inference_latency_ms = round(
                        (existing_case.ml_telemetry.inference_latency_ms + new_latency) / 2.0,
                        2,
                    )

                # 5. Re-synthesize and extend legal narrative summary
                updated_narrative = self._synthesize_narrative(
                    typology=typology,
                    tx_records=existing_case.transactions,
                    suspect=existing_case.suspect,
                    counterparty=existing_case.counterparty,
                    ml_result=ml_result,
                    avg_risk_score=avg_score,
                    latest_tx_payload=tx_payload,
                )
                existing_case.grounds_of_suspicion.narrative_summary = updated_narrative

                # Append secondary typology if new and distinct
                if (
                    typology != existing_case.grounds_of_suspicion.primary_typology
                    and typology not in existing_case.grounds_of_suspicion.secondary_typologies
                ):
                    existing_case.grounds_of_suspicion.secondary_typologies.append(typology)

                # 6. Reset 5-minute rolling activity timer to keep ring open
                self._ring_last_active[existing_case.sar_id] = current_time
                self._active_ring_index[suspect_id] = existing_case.sar_id
                if counterparty_id:
                    self._active_ring_index[counterparty_id] = existing_case.sar_id

                return existing_case

            # ------------------------------------------------------------------
            # Case B: No Active Case or Rolling Window Expired
            # ------------------------------------------------------------------
            sar_id = generate_sar_id()
            fiu_deadline = calculate_fiu_deadline()

            logger.info(
                "Initializing new SAR dossier %s for suspect %s under typology %s",
                sar_id,
                suspect_id,
                typology,
            )

            # Suspect profile
            suspect_profile = SuspectEntityProfile(
                entity_identifier=suspect_id,
                entity_name=tx_payload.get("entity_name") or "ANONYMOUS_HOLDER",
                entity_type=tx_payload.get("entity_type", "INDIVIDUAL"),
                institution_code=tx_payload.get("branch_ifsc") or tx_payload.get("ifsc"),
                kyc_risk_tier=RiskTier.CRITICAL_SAR,
                is_pep=bool(tx_payload.get("is_pep", False)),
                flags=list(tx_payload.get("flags", [])),
            )

            # Counterparty profile
            counterparty_profile: Optional[SuspectEntityProfile] = None
            if counterparty_id:
                counterparty_profile = SuspectEntityProfile(
                    entity_identifier=counterparty_id,
                    entity_name=tx_payload.get("counterparty_name") or "ANONYMOUS_COUNTERPARTY",
                    entity_type="INDIVIDUAL",
                    institution_code=tx_payload.get("counterparty_ifsc"),
                    kyc_risk_tier=RiskTier.HIGH,
                )

            # Model telemetry
            model_name = ml_result.get("model_name") or (
                "Elliptic-XGBoost-v1.2" if tx_record.currency.upper() == "BTC" else "CatBoost-Banking-v2.4"
            )
            model_version = str(ml_result.get("model_version", "v2.4"))
            latency_ms = float(ml_result.get("latency_ms", 12.4))
            feature_imp = dict(ml_result.get("feature_importance") or ml_result.get("top_features") or {})

            ml_telemetry = MLTelemetry(
                model_name=model_name,
                model_version=model_version,
                inference_latency_ms=latency_ms,
                feature_importance=feature_imp,
            )

            # Grounds of suspicion
            rule_triggers = ["PMLA-SEC-12", "PMLA-RULE-3"]
            if typology == SuspicionTypology.IN_TYP_STRUCT:
                rule_triggers.append("PAN-MANDATE-50K")
            elif typology == SuspicionTypology.IN_TYP_HAWALA:
                rule_triggers.append("WIRE-PROFILE-DEVIATION")
            elif typology == SuspicionTypology.IN_TYP_VDA_MIX:
                rule_triggers.append("VDA-UNHOSTED-PEEL")

            narrative = self._synthesize_narrative(
                typology=typology,
                tx_records=[tx_record],
                suspect=suspect_profile,
                counterparty=counterparty_profile,
                ml_result=ml_result,
                avg_risk_score=tx_record.risk_score,
                latest_tx_payload=tx_payload,
            )

            grounds = GroundsOfSuspicion(
                primary_typology=typology,
                secondary_typologies=[],
                rule_triggers=rule_triggers,
                narrative_summary=narrative,
            )

            total_inr = tx_record.amount if tx_record.currency.upper() == "INR" else 0.0
            total_btc = tx_record.amount if tx_record.currency.upper() == "BTC" else None

            case_record = SARCaseRecord(
                sar_id=sar_id,
                created_at=datetime.now(timezone.utc),
                fiu_deadline=fiu_deadline,
                status=CaseStatus.PENDING_REVIEW,
                reporting_entity=ReportingEntityInfo(),
                suspect=suspect_profile,
                counterparty=counterparty_profile,
                transactions=[tx_record],
                total_exposure_inr=total_inr,
                total_exposure_btc=total_btc,
                ml_telemetry=ml_telemetry,
                grounds_of_suspicion=grounds,
                assigned_analyst=None,
            )

            # Persist in lookup indexes
            self._cases[sar_id] = case_record
            self._active_ring_index[suspect_id] = sar_id
            if counterparty_id:
                self._active_ring_index[counterparty_id] = sar_id
            self._ring_last_active[sar_id] = current_time

            return case_record

    # --------------------------------------------------------------------------
    # Core API 2: Get SAR By ID
    # --------------------------------------------------------------------------
    async def get_sar_by_id(self, sar_id: str) -> Optional[SARCaseRecord]:
        """Retrieves a single SAR case dossier by its canonical SAR ID."""
        async with self._lock:
            return self._cases.get(sar_id)

    # --------------------------------------------------------------------------
    # Core API 3: List SARs (Paginated, Sorted Newest First, Filterable)
    # --------------------------------------------------------------------------
    async def list_sars(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[CaseStatus] = None,
        typology: Optional[SuspicionTypology] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[SARCaseRecord], int]:
        """
        Returns a paginated list of cases sorted by newest first,
        with query filtering across case status, grounds typology, and text search.
        """
        async with self._lock:
            # Sort newest first by created_at
            all_cases = sorted(
                self._cases.values(),
                key=lambda c: c.created_at,
                reverse=True,
            )

            filtered: List[SARCaseRecord] = []
            search_clean = search.strip().lower() if search else None

            for case in all_cases:
                # Filter by status
                if status is not None:
                    c_status = case.status.value if hasattr(case.status, "value") else case.status
                    s_status = status.value if hasattr(status, "value") else status
                    if c_status != s_status:
                        continue

                # Filter by primary typology
                if typology is not None:
                    c_typology = (
                        case.grounds_of_suspicion.primary_typology.value
                        if hasattr(case.grounds_of_suspicion.primary_typology, "value")
                        else case.grounds_of_suspicion.primary_typology
                    )
                    t_typology = typology.value if hasattr(typology, "value") else typology
                    if c_typology != t_typology:
                        continue

                # Filter by search string
                if search_clean:
                    match_fields = [
                        case.sar_id.lower(),
                        case.suspect.entity_identifier.lower(),
                        (case.suspect.entity_name or "").lower(),
                        case.grounds_of_suspicion.narrative_summary.lower(),
                    ]
                    if case.counterparty:
                        match_fields.append(case.counterparty.entity_identifier.lower())
                        match_fields.append((case.counterparty.entity_name or "").lower())
                    for tx in case.transactions:
                        if tx.counterparty_from:
                            match_fields.append(tx.counterparty_from.lower())
                        if tx.counterparty_to:
                            match_fields.append(tx.counterparty_to.lower())

                    if not any(search_clean in field for field in match_fields):
                        continue

                filtered.append(case)

            total_count = len(filtered)
            start = max(0, (page - 1) * page_size)
            end = start + page_size
            page_items = filtered[start:end]

            return page_items, total_count

    # --------------------------------------------------------------------------
    # Core API 4: Update SAR Status & Ring Eviction
    # --------------------------------------------------------------------------
    async def update_sar_status(
        self,
        sar_id: str,
        new_status: CaseStatus,
        analyst_id: str,
        resolution_notes: Optional[str] = None,
    ) -> Optional[SARCaseRecord]:
        """
        Handles state transitions (e.g. PENDING_REVIEW -> FILED_WITH_FIU or DISMISSED).
        Evicts closed cases from `_active_ring_index` so future activity triggers fresh investigations.
        """
        async with self._lock:
            case = self._cases.get(sar_id)
            if not case:
                return None

            case.status = new_status
            case.assigned_analyst = analyst_id

            # Closed case statuses: evict from active ring index
            closed_statuses = {
                CaseStatus.FILED_WITH_FIU,
                CaseStatus.DISMISSED,
                CaseStatus.FILED_WITH_FIU.value,
                CaseStatus.DISMISSED.value,
            }

            if new_status in closed_statuses:
                # Find all ring mappings pointing to this sar_id and evict
                evicted_entities = [
                    entity
                    for entity, linked_sar_id in self._active_ring_index.items()
                    if linked_sar_id == sar_id
                ]
                for entity in evicted_entities:
                    self._active_ring_index.pop(entity, None)

                self._ring_last_active.pop(sar_id, None)

                logger.info(
                    "Case %s transitioned to %s by %s. Evicted %d suspect entities from active ring index.",
                    sar_id,
                    new_status,
                    analyst_id,
                    len(evicted_entities),
                )

            return case


# ------------------------------------------------------------------------------
# Module-Level Singleton Export
# ------------------------------------------------------------------------------
sar_service = SARService()
