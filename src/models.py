"""Pydantic models for Inpol case data structures.

This module defines data models for case data, attachments, questions,
and snapshots using Pydantic v2 syntax.
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from enum import Enum
from pydantic import BaseModel, Field

try:
    from src.localization import get_status_label, get_question_title, get_question_status
    _USE_L10N = True
except ImportError:
    _USE_L10N = False


class ChangeType(str, Enum):
    """Types of changes that can be detected."""
    STATUS = "status"
    NEW_DOCUMENT = "new_document"
    REMOVED_DOCUMENT = "removed_document"
    DECISION_DATE_CHANGE = "decision_date_change"
    SUBMIT_DATE_CHANGE = "submit_date_change"
    UPDATED_AT_CHANGE = "updated_at_change"
    TIMELINE_EVENT_ADDED = "timeline_event_added"
    QUESTION_ASKED = "question_asked"
    QUESTION_ANSWERED = "question_answered"
    QUESTION_COUNT_CHANGE = "question_count_change"
    NEW_QUESTION_DETAIL = "new_question_detail"
    NONE = "none"


# Question title mappings (fallback when localization unavailable)
_QUESTION_TITLES_FALLBACK = {
    "1": "Missing documents",
    "2": "Proxy",
    "3": "Issuance of a certificate",
    "4": "Inspection of the proceeding files",
    "5": "Acceleration of decision issuance",
    "6": "Acceleration of card issuance",
    "7": "Other"
}

# Question status mappings (fallback when localization unavailable)
_QUESTION_STATUSES_FALLBACK = {
    "1": "Waiting for an answer",
    "2": "Answer"
}

def get_question_title_localized(title_id: str) -> str:
    """Get question title for title ID (uses localization if available)."""
    if _USE_L10N:
        return get_question_title(title_id)
    return _QUESTION_TITLES_FALLBACK.get(title_id, f"Unknown ({title_id})")


def get_question_status_localized(status_id: str) -> str:
    """Get question status label for status ID (uses localization if available)."""
    if _USE_L10N:
        return get_question_status(status_id)
    return _QUESTION_STATUSES_FALLBACK.get(status_id, f"Unknown ({status_id})")


# Attachment status/type mappings
ATTACHMENT_STATUSES = {
    "1": "Pending",
    "2": "Uploaded",
    "3": "Rejected"
}

# Status labels mapping (fallback when localization unavailable)
_STATUSES_FALLBACK = {
    "1": "New",
    "2": "In progress - signature assigned",
    "3": "In progress - call for formal defects",
    "4": "In progress",
    "5": "In progress",
    "6": "In progress",
    "7": "In progress - the second instance",
    "8": "In progress",
    "9": "In progress",
    "10": "Decision signed",
    "11": "Decision signed",
    "12": "Decision signed",
    "13": "Documents to pick up",
    "14": "Closed",
    "15": "Closed",
    "16": "Closed",
    "17": "Closed",
    "18": "Closed",
    "19": "Closed",
    "20": "Proceeding files on loan",
    "21": "Suspended",
    "22": "Opinion delivered"
}

# Exported mappings for compatibility with code using .get()
QUESTION_TITLES = _QUESTION_TITLES_FALLBACK
QUESTION_STATUSES = _QUESTION_STATUSES_FALLBACK
STATUSES = _STATUSES_FALLBACK


def get_status_label_localized(status_id: str) -> str:
    """Get status label for status ID (uses localization if available)."""
    if _USE_L10N:
        return get_status_label(status_id)
    return _STATUSES_FALLBACK.get(status_id, f"Unknown ({status_id})")


class Change(BaseModel):
    """Represents a detected change between two snapshots.

    Attributes:
        type: Type of change (status, new_document, etc.)
        old_value: Value from previous snapshot
        new_value: Value from current snapshot
        description: Human-readable description
    """
    type: ChangeType = Field(..., description="Type of change")
    old_value: Any = Field(..., description="Value from previous snapshot")
    new_value: Any = Field(..., description="Value from current snapshot")
    description: str = Field(..., description="Human-readable description")

    def to_dict(self) -> Dict[str, Any]:
        """Convert change to dictionary.

        Returns:
            Dictionary with type, old_value, new_value, description
        """
        return {
            "type": self.type.value,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "description": self.description
        }


class Attachment(BaseModel):
    """Model for attachment data.

    Attributes:
        name: Filename of the attachment
        date_added: Date when attachment was added to the case
        url: Download URL if available (optional)
    """
    name: str = Field(..., description="Filename of the attachment")
    date_added: str = Field(..., description="Date added (ISO format)")
    url: Optional[str] = Field(None, description="Download URL if available")


class Question(BaseModel):
    """Model for case question data.

    Attributes:
        id: Question identifier
        title: Question title ID (numeric from JSON)
        content: Question text (from body field)
        status: Status code (raw from JSON)
        status_label: Resolved status label (via i18n dictionary)
        sent_time: When the question was submitted
        answer: Answer text (from answer field, if exists)
        response_time: When the question was answered (from responseTime field, if exists)
    """
    id: str = Field(..., description="Question identifier")
    title: Optional[str] = Field(None, description="Question title ID")
    content: str = Field(..., description="Question text")
    status: str = Field(..., description="Status code (raw)")
    status_label: Optional[str] = Field(None, description="Resolved status label")
    sent_time: str = Field(..., description="Submission time (ISO format)")
    answer: Optional[str] = Field(None, description="Answer text")
    response_time: Optional[str] = Field(None, description="Response time (ISO format)")


class CaseData(BaseModel):
    """Model for case data.

    Attributes:
        person_first: First name of the person
        person_last: Last name of the person
        case_number: Case number (format: "WSC-V.6153.4537.2025")
        case_type: Type of case
        submit_date: Date case was submitted
        decision_date: Expected decision date
        updated_at: Last update timestamp (critical for change detection)
        status_raw: Raw status code from JSON
        status_label: Resolved status label (via i18n dictionary)
        attachments: List of attachments for the case
        questions: List of questions for the case
        timeline: List of raw timeline entries
    """
    person_first: str = Field(..., description="First name")
    person_last: str = Field(..., description="Last name")
    case_number: str = Field(..., description="Case number")
    case_type: str = Field(..., description="Case type")
    submit_date: Optional[str] = Field(None, description="Submission date")
    decision_date: Optional[str] = Field(None, description="Expected decision date")
    updated_at: str = Field(..., description="Last update timestamp")
    status_raw: str = Field(..., description="Raw status code")
    status_label: Optional[str] = Field(None, description="Resolved status label")
    attachments: List[Attachment] = Field(default_factory=list, description="Attachments")
    questions: List[Question] = Field(default_factory=list, description="Questions")
    timeline: List[dict] = Field(default_factory=list, description="Raw timeline entries")
    related_docs: List[dict] = Field(default_factory=list, description="Related documents (relatedDocs)")
    timeline_events: List[dict] = Field(default_factory=list, description="Timeline events (timelineEvents)")


class Snapshot(BaseModel):
    """Model for database snapshot.

    Attributes:
        id: Database primary key
        account_id: Account identifier
        case_id: Case identifier
        endpoint_type: Endpoint type (case_data, attachments, questions)
        raw_json: Full raw JSON response
        parsed_data: Extracted fields
        timestamp: Timestamp of check (UTC)
    """
    id: Optional[int] = Field(None, description="Database primary key")
    account_id: str = Field(..., description="Account identifier")
    case_id: str = Field(..., description="Case identifier")
    endpoint_type: str = Field(..., description="Endpoint type")
    raw_json: dict = Field(default_factory=dict, description="Full raw JSON response")
    parsed_data: dict = Field(default_factory=dict, description="Extracted fields")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")


def from_json_snapshot(
    account_id: str,
    case_id: str,
    endpoint_type: str,
    raw_json: dict
) -> Snapshot:
    """Create a Snapshot from raw JSON response.

    Args:
        account_id: Account identifier
        case_id: Case identifier
        endpoint_type: Endpoint type
        raw_json: Full raw JSON response

    Returns:
        Snapshot model with raw_json preserved
    """
    return Snapshot(
        account_id=account_id,
        case_id=case_id,
        endpoint_type=endpoint_type,
        raw_json=raw_json,
        parsed_data={},
        timestamp=datetime.utcnow()
    )
