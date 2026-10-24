"""Typed loaders for the participant-facing dataset CSVs."""
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List

from paths import DATASET


@dataclass(frozen=True)
class Request:
    case_id: str
    email: str
    requested_at: str
    reported_status: str
    reported_at: str
    audit_at: str
    request_text: str


@dataclass(frozen=True)
class Identity:
    user_id: str
    name: str
    email: str
    phone: str
    email_hash: str
    updated_at: str


@dataclass(frozen=True)
class AuditEntry:
    audit_id: str
    user_id: str
    event_time: str
    field_name: str
    old_value: str
    new_value: str


@dataclass(frozen=True)
class Activity:
    activity_id: str
    event_time: str
    event_type: str
    source_system: str
    target_system: str
    resource_id: str
    reported_result: str
    details: str


@dataclass(frozen=True)
class Rule:
    rule_id: str
    data_category: str
    condition: str
    required_action: str


@dataclass(frozen=True)
class EvidenceFile:
    file_id: str
    file_path: str
    origin: str
    captured_at: str


def _read(path: Path, cls) -> list:
    with open(path, newline="", encoding="utf-8") as f:
        return [cls(**row) for row in csv.DictReader(f)]


def load_requests(path: Path = DATASET / "deletion_requests.csv") -> List[Request]:
    return _read(path, Request)


def load_samples() -> List[Request]:
    return _read(DATASET / "sample_deletion_requests.csv", Request)


def load_identities() -> List[Identity]:
    return _read(DATASET / "user_identities.csv", Identity)


def load_audit_log() -> List[AuditEntry]:
    return _read(DATASET / "user_audit_log.csv", AuditEntry)


def load_activity() -> List[Activity]:
    return _read(DATASET / "system_activity.csv", Activity)


def load_rules() -> List[Rule]:
    return _read(DATASET / "deletion_rules.csv", Rule)


def load_evidence_manifest() -> List[EvidenceFile]:
    return _read(DATASET / "evidence_files.csv", EvidenceFile)
