"""Change detection layer for Inpol Monitor.

This module provides the Detector class with strategy pattern for
comparing snapshots and identifying status changes, new documents,
and deadline modifications.
"""

import json
import logging
from datetime import datetime
from typing import Optional, List

from src.models import Snapshot, Change, ChangeType, QUESTION_TITLES, QUESTION_STATUSES, STATUSES
from src.storage import SnapshotRepository

logger = logging.getLogger(__name__)


class BaseDetector:
    """Base detector class."""

    def __init__(self, storage=None):
        """Initialize detector.

        Args:
            storage: Optional storage repository (for test compatibility)
        """
        self.storage = storage

    def detect(self, old_snapshot: Optional[Snapshot], new_snapshot: Snapshot) -> List[Change]:
        """Detect changes - to be overridden by subclasses."""
        raise NotImplementedError


class StatusDetector(BaseDetector):
    """Detector for status changes.

    Monitors the raw status field for changes and translates numeric status IDs
    to human-readable labels using the STATUSES mapping.
    """

    def detect(self, old_snapshot: Optional[Snapshot], new_snapshot: Snapshot) -> List[Change]:
        """Detect status changes.

        Args:
            old_snapshot: Previous snapshot
            new_snapshot: Current snapshot

        Returns:
            List of Change objects for status changes
        """
        changes = []

        old_parsed = old_snapshot.parsed_data if old_snapshot else {}
        new_parsed = new_snapshot.parsed_data or {}

        old_status = old_parsed.get("status_raw")
        new_status = new_parsed.get("status_raw")

        if old_status != new_status:
            # Get translated labels using STATUSES mapping
            old_label = STATUSES.get(old_status, f"Unknown ({old_status})")
            new_label = STATUSES.get(new_status, f"Unknown ({new_status})")

            # Format description with both ID and label
            description = (
                f"Status changed from '{old_status} ({old_label})' "
                f"to '{new_status} ({new_label})'"
            )

            changes.append(Change(
                type=ChangeType.STATUS,
                old_value=old_status,
                new_value=new_status,
                description=description
            ))

        return changes


class DocumentDetector(BaseDetector):
    """Detector for document changes.

    Monitors relatedDocs list for new or removed documents.
    """

    def __init__(self, storage=None):
        super().__init__(storage)

    def detect(self, old_snapshot: Optional[Snapshot], new_snapshot: Snapshot) -> List[Change]:
        """Detect document changes.

        Args:
            old_snapshot: Previous snapshot
            new_snapshot: Current snapshot

        Returns:
            List of Change objects for document changes
        """
        changes = []

        old_parsed = old_snapshot.parsed_data if old_snapshot else {}
        new_parsed = new_snapshot.parsed_data or {}

        old_docs = old_parsed.get("relatedDocs", [])
        new_docs = new_parsed.get("relatedDocs", [])

        # Build sets of document IDs
        old_ids = {doc.get("id") for doc in old_docs if isinstance(doc, dict) and doc.get("id")}
        new_ids = {doc.get("id") for doc in new_docs if isinstance(doc, dict) and doc.get("id")}

        # New documents
        added_ids = new_ids - old_ids
        for doc_id in added_ids:
            doc_name = next((doc.get("name") for doc in new_docs if doc.get("id") == doc_id), "Unknown")
            changes.append(Change(
                type=ChangeType.NEW_DOCUMENT,
                old_value=None,
                new_value=doc_id,
                description=f"New document added: {doc_name}"
            ))

        # Removed documents
        removed_ids = old_ids - new_ids
        for doc_id in removed_ids:
            doc_name = next((doc.get("name") for doc in old_docs if doc.get("id") == doc_id), "Unknown")
            changes.append(Change(
                type=ChangeType.REMOVED_DOCUMENT,
                old_value=doc_id,
                new_value=None,
                description=f"Document removed: {doc_name}"
            ))

        return changes


class DateDetector(BaseDetector):
    """Detector for date changes.

    Monitors decision_date, submit_date, and updated_at fields.
    """

    def detect(self, old_snapshot: Optional[Snapshot], new_snapshot: Snapshot) -> List[Change]:
        """Detect date changes.

        Args:
            old_snapshot: Previous snapshot
            new_snapshot: Current snapshot

        Returns:
            List of Change objects for date changes
        """
        changes = []

        old_parsed = old_snapshot.parsed_data if old_snapshot else {}
        new_parsed = new_snapshot.parsed_data or {}

        # Decision date
        old_dec = old_parsed.get("decision_date")
        new_dec = new_parsed.get("decision_date")
        if old_dec != new_dec:
            changes.append(Change(
                type=ChangeType.DECISION_DATE_CHANGE,
                old_value=old_dec,
                new_value=new_dec,
                description=f"Decision date changed from {old_dec} to {new_dec}"
            ))

        # Submit date
        old_sub = old_parsed.get("submit_date")
        new_sub = new_parsed.get("submit_date")
        if old_sub != new_sub:
            changes.append(Change(
                type=ChangeType.SUBMIT_DATE_CHANGE,
                old_value=old_sub,
                new_value=new_sub,
                description=f"Submit date changed from {old_sub} to {new_sub}"
            ))

        # Updated at
        old_upd = old_parsed.get("updated_at")
        new_upd = new_parsed.get("updated_at")
        if old_upd != new_upd:
            changes.append(Change(
                type=ChangeType.UPDATED_AT_CHANGE,
                old_value=old_upd,
                new_value=new_upd,
                description=f"Updated at changed from {old_upd} to {new_upd}"
            ))

        return changes


class TimelineDetector(BaseDetector):
    """Detector for timeline event additions.

    Monitors timelineEvents array for new events only.
    """

    def detect(self, old_snapshot: Optional[Snapshot], new_snapshot: Snapshot) -> List[Change]:
        """Detect timeline event additions.

        Args:
            old_snapshot: Previous snapshot
            new_snapshot: Current snapshot

        Returns:
            List of Change objects for new timeline events (one per event)
        """
        changes = []

        old_parsed = old_snapshot.parsed_data if old_snapshot else {}
        new_parsed = new_snapshot.parsed_data or {}

        old_events = old_parsed.get("timelineEvents", [])
        new_events = new_parsed.get("timelineEvents", [])

        # Detect new timeline events by comparing sets of (eventType, date) tuples
        old_keys = {(e.get("eventType"), e.get("date")) for e in old_events if isinstance(e, dict)}
        new_keys = {(e.get("eventType"), e.get("date")) for e in new_events if isinstance(e, dict)}

        added_keys = new_keys - old_keys
        for event_type, date in added_keys:
            event = next((e for e in new_events
                         if isinstance(e, dict)
                         and e.get("eventType") == event_type
                         and e.get("date") == date), None)
            if event:
                # Get localized name (english) if available
                name_data = event.get("name", {})
                event_name = name_data.get("english") if isinstance(name_data, dict) else None
                
                description = f"New timeline event: {event_type} @ {date} by {event.get('author', 'Unknown')}"
                if event_name:
                    description += f": {event_name}"
                
                changes.append(Change(
                    type=ChangeType.TIMELINE_EVENT_ADDED,
                    old_value=None,
                    new_value=json.dumps(event, ensure_ascii=False),
                    description=description
                ))

        return changes


class QuestionsEndpointDetector(BaseDetector):
    """Detector for questions endpoint changes.

    Monitors the questions endpoint snapshot for count changes and new questions.
    """

    def detect(self, old_snapshot: Optional[Snapshot], new_snapshot: Snapshot) -> List[Change]:
        """Detect questions endpoint changes.

        Args:
            old_snapshot: Previous snapshot
            new_snapshot: Current snapshot

        Returns:
            List of Change objects for questions endpoint changes
        """
        changes = []

        old_parsed = old_snapshot.parsed_data if old_snapshot else {}
        new_parsed = new_snapshot.parsed_data or {}

        old_count = old_parsed.get("count", 0)
        new_count = new_parsed.get("count", 0)

        if old_count != new_count:
            changes.append(Change(
                type=ChangeType.QUESTION_COUNT_CHANGE,
                old_value=str(old_count),
                new_value=str(new_count),
                description=f"Total number of questions changed from {old_count} to {new_count}"
            ))

        old_questions = old_parsed.get("questions", [])
        new_questions = new_parsed.get("questions", [])

        old_by_id = {q.get("id"): q for q in old_questions if isinstance(q, dict) and q.get("id")}
        new_by_id = {q.get("id"): q for q in new_questions if isinstance(q, dict) and q.get("id")}

        new_ids = set(new_by_id.keys()) - set(old_by_id.keys())
        for qid in new_ids:
            question = new_by_id[qid]
            status = question.get("status", "1")
            title_id = str(question.get("title", ""))
            title_text = QUESTION_TITLES.get(title_id, f"Unknown ({title_id})") if title_id else "Unknown"
            status_label = QUESTION_STATUSES.get(str(status), f"Unknown ({status})")
            body = question.get("body", "") or question.get("content", "")
            sent_time = question.get("sentTime", "")
            
            sent_dt = None
            if sent_time:
                try:
                    from datetime import datetime
                    sent_dt = datetime.fromisoformat(sent_time.replace('Z', '+00:00'))
                    sent_formatted = sent_dt.strftime("%Y-%b-%d %H:%M")
                except:
                    sent_formatted = sent_time
            else:
                sent_formatted = ""
            
            changes.append(Change(
                type=ChangeType.NEW_QUESTION_DETAIL,
                old_value=None,
                new_value=json.dumps(question, ensure_ascii=False),
                description=f'New "{title_text}" question was added: {body[:80]}{"..." if len(body) > 80 else ""} at {sent_formatted} ({status_label})'
            ))

        # Status changes (question answered)
        for qid in new_by_id:
            if qid in old_by_id:
                old_status = old_by_id[qid].get("status")
                new_status = new_by_id[qid].get("status")
                if old_status != new_status:
                    question = new_by_id[qid]
                    title_id = str(question.get("title", ""))
                    title_text = QUESTION_TITLES.get(title_id, f"Unknown ({title_id})") if title_id else "Unknown"
                    new_status_label = QUESTION_STATUSES.get(str(new_status), f"Unknown ({new_status})")
                    if new_status == 2:
                        answer_content = question.get("answer", "")
                        description = f"Question answered (title: {title_text}, status: {new_status_label})"
                        if answer_content:
                            description += f" with answer: {answer_content[:100]}{'...' if len(answer_content) > 100 else ''}"
                        changes.append(Change(
                            type=ChangeType.QUESTION_ANSWERED,
                            old_value=str(old_status),
                            new_value=str(new_status),
                            description=description
                        ))

        return changes


class AttachmentsEndpointDetector(BaseDetector):
    """Detector for attachments endpoint changes.

    Monitors the attachments endpoint snapshot for count changes and new/removed attachments.
    """

    def detect(self, old_snapshot: Optional[Snapshot], new_snapshot: Snapshot) -> List[Change]:
        """Detect attachments endpoint changes.

        Args:
            old_snapshot: Previous snapshot
            new_snapshot: Current snapshot

        Returns:
            List of Change objects for attachments endpoint changes
        """
        changes = []

        old_parsed = old_snapshot.parsed_data if old_snapshot else {}
        new_parsed = new_snapshot.parsed_data or {}

        old_count = old_parsed.get("count", 0)
        new_count = new_parsed.get("count", 0)

        if old_count != new_count:
            direction = "increased" if new_count > old_count else "decreased"
            changes.append(Change(
                type=ChangeType.NEW_DOCUMENT,
                old_value=str(old_count),
                new_value=str(new_count),
                description=f"Total number of documents {direction} from {old_count} to {new_count}"
            ))

        return changes


class QuestionDetector(BaseDetector):
    """Detector for question/answer changes.

    Monitors questions list for new questions and status changes.
    """

    def detect(self, old_snapshot: Optional[Snapshot], new_snapshot: Snapshot) -> List[Change]:
        """Detect question/answer changes.

        Args:
            old_snapshot: Previous snapshot
            new_snapshot: Current snapshot

        Returns:
            List of Change objects for question changes
        """
        changes = []

        old_parsed = old_snapshot.parsed_data if old_snapshot else {}
        new_parsed = new_snapshot.parsed_data or {}

        old_questions = old_parsed.get("questions", [])
        new_questions = new_parsed.get("questions", [])

        # Build dict of questions by ID
        old_by_id = {q.get("id"): q for q in old_questions if isinstance(q, dict) and q.get("id")}
        new_by_id = {q.get("id"): q for q in new_questions if isinstance(q, dict) and q.get("id")}

        # New questions (asked)
        new_ids = set(new_by_id.keys()) - set(old_by_id.keys())
        for qid in new_ids:
            question = new_by_id[qid]
            status = question.get("status")
            status_label = QUESTION_STATUSES.get(str(status), f"Unknown ({status})") if status else "Unknown"
            title_id = str(question.get("title", ""))
            title_text = QUESTION_TITLES.get(title_id, f"Unknown ({title_id})")
            sent_time = question.get("sentTime") or question.get("sent_time", "")
            changes.append(Change(
                type=ChangeType.QUESTION_ASKED,
                old_value=None,
                new_value=json.dumps(question, ensure_ascii=False),
                description=f"New question asked (status: {status_label}, title: {title_text}) at {sent_time}"
            ))

        # Status changes (question answered)
        for qid in new_by_id:
            if qid in old_by_id:
                old_status = old_by_id[qid].get("status")
                new_status = new_by_id[qid].get("status")
                if old_status != new_status:
                    # Assume status 1=asked, 2=answered
                    new_status_label = QUESTION_STATUSES.get(str(new_status), f"Unknown ({new_status})") if new_status else "Unknown"
                    if new_status == 2:
                        question = new_by_id[qid]
                        title_id = str(question.get("title", ""))
                        title_text = QUESTION_TITLES.get(title_id, f"Unknown ({title_id})")
                        answer_content = question.get("answer", "")
                        description = f"Question answered (title: {title_text}, status: {new_status_label})"
                        if answer_content:
                            description += f" with answer: {answer_content[:100]}{'...' if len(answer_content) > 100 else ''}"
                        changes.append(Change(
                            type=ChangeType.QUESTION_ANSWERED,
                            old_value=str(old_status),
                            new_value=str(new_status),
                            description=description
                        ))

        return changes


class Detector:
    """Main detector that coordinates multiple detection strategies."""

    def __init__(self, storage: SnapshotRepository, notifier=None):
        """Initialize detector.

        Args:
            storage: SnapshotRepository for loading previous snapshots
            notifier: Optional TelegramNotifier for sending notifications
        """
        self.storage = storage
        self.notifier = notifier
        self.status_detector = StatusDetector()
        self.document_detector = DocumentDetector()
        self.date_detector = DateDetector()
        self.timeline_detector = TimelineDetector()
        self.question_detector = QuestionDetector()
        self.questions_endpoint_detector = QuestionsEndpointDetector()
        self.attachments_endpoint_detector = AttachmentsEndpointDetector()

    def detect_changes(self, old_snapshot: Optional[Snapshot], new_snapshot: Snapshot) -> List[Change]:
        """Detect all changes between two snapshots.

        Args:
            old_snapshot: Previous snapshot (can be None for first check)
            new_snapshot: Current snapshot

        Returns:
            List of Change objects representing detected changes
        """
        changes = []

        if old_snapshot is None:
            logger.info("No previous snapshot found. Skipping change detection.")
            return changes

        changes.extend(self.status_detector.detect(old_snapshot, new_snapshot))
        changes.extend(self.document_detector.detect(old_snapshot, new_snapshot))
        changes.extend(self.date_detector.detect(old_snapshot, new_snapshot))
        changes.extend(self.timeline_detector.detect(old_snapshot, new_snapshot))
        changes.extend(self.question_detector.detect(old_snapshot, new_snapshot))

        return changes

    def get_previous_snapshot(
        self,
        account_id: str,
        case_id: str,
        endpoint_type: str
    ) -> Optional[Snapshot]:
        """Get the previous snapshot for comparison.

        Args:
            account_id: Account identifier
            case_id: Case identifier
            endpoint_type: Endpoint type (case_data, attachments, questions)

        Returns:
            Previous Snapshot or None if no previous snapshot exists
        """
        try:
            conn = self.storage._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp
                FROM snapshots
                WHERE case_id = ? AND endpoint_type = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (case_id, endpoint_type))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return Snapshot(
                account_id=row["account_id"],
                case_id=row["case_id"],
                endpoint_type=row["endpoint_type"],
                raw_json=json.loads(row["raw_json"]) if row["raw_json"] else {},
                parsed_data=json.loads(row["parsed_data"]) if row["parsed_data"] else {},
                timestamp=datetime.fromisoformat(row["timestamp"])
            )
        except Exception as e:
            logger.error(f"Failed to get previous snapshot: {e}")
            return None

    async def detect_all_changes(
        self,
        sessions: dict,
        credentials: dict,
        notifier=None
    ) -> dict:
        """Detect changes for all cases across all accounts.

        Args:
            sessions: Dict[account_name] -> session object
            credentials: Dict[account_name] -> {"case_ids": [...]}
            notifier: Optional TelegramNotifier

        Returns:
            Dictionary mapping account name to list of changes
        """
        results = {}
        processed = set()

        # Get previous snapshots for all cases
        previous_snapshots = {}
        for account_name, account_info in credentials.items():
            # Handle both formats: {"case_ids": [...]} or direct list [...]
            if isinstance(account_info, dict):
                case_ids = account_info.get("case_ids", [])
                # Get account login to use as account_id in snapshots
                account_login = account_info.get("username", account_name)
            else:
                # Assume it's a direct list of case IDs
                case_ids = account_info
                account_login = account_name
            for case_id in case_ids:
                if case_id not in processed:
                    prev = self.get_previous_snapshot(
                        account_id=account_login,
                        case_id=case_id,
                        endpoint_type="case_data"
                    )
                    previous_snapshots[case_id] = prev

        # Process each case
        for account_name, account_info in credentials.items():
            # Handle both formats: {"case_ids": [...]} or direct list [...]
            if isinstance(account_info, dict):
                case_ids = account_info.get("case_ids", [])
                # Get account login to use as account_id in snapshots
                account_login = account_info.get("username", account_name)
            else:
                # Assume it's a direct list of case IDs
                case_ids = account_info
                account_login = account_name
            results[account_name] = []

            for case_id in case_ids:
                if case_id in processed:
                    continue

                prev_snapshot = previous_snapshots.get(case_id)

                if account_name not in sessions:
                    if self.notifier:
                        case_url = f"https://inpol.mazowieckie.pl/home/cases/{case_id}"
                        error_msg = "Account authentication failed or session unavailable"
                        try:
                            self.notifier.on_change(
                                account_id=account_name,
                                account_login=account_login,
                                case_id=case_id,
                                changes=[],
                                case_type="",
                                person_first="",
                                case_url=case_url,
                                error_message=error_msg
                            )
                        except Exception as notify_err:
                            logger.error(f"Failed to notify about inaccessible case: {notify_err}")
                    logger.error(f"Skipping case {case_id}: account {account_name} not authenticated")
                    continue

                try:
                    from src.scraper import InpolScraper
                    session = sessions[account_name]
                    if isinstance(session, tuple):
                        session = session[0]
                    scraper = InpolScraper(session=session, account_name=account_name)
                    
                    # Fetch and log case data
                    current_data = scraper.fetch_case_data(case_id)
                    if current_data is None:
                        logger.error(f"Failed to fetch case data for {case_id}")
                        continue

                    # Build case data snapshot
                    current_snapshot = Snapshot(
                        account_id=account_login,
                        case_id=case_id,
                        endpoint_type="case_data",
                        raw_json=current_data.model_dump(mode="json") if hasattr(current_data, 'model_dump') else {},
                        parsed_data={
                            "person_first": current_data.person_first,
                            "person_last": current_data.person_last,
                            "case_number": current_data.case_number,
                            "case_type": current_data.case_type,
                            "submit_date": current_data.submit_date,
                            "decision_date": current_data.decision_date,
                            "updated_at": current_data.updated_at,
                            "status_raw": current_data.status_raw,
                            "relatedDocs": current_data.related_docs,
                            "timelineEvents": current_data.timeline_events,
                            "questions": [
                                {
                                    "id": q.id,
                                    "content": q.content,
                                    "status": q.status,
                                    "status_label": q.status_label,
                                    "sent_time": q.sent_time
                                }
                                for q in current_data.questions
                            ]
                        },
                        timestamp=datetime.utcnow()
                    )
                    
# Detect changes
                    changes = self.detect_changes(prev_snapshot, current_snapshot)

                    # Build case URL for hyperlink
                    case_url = f"{scraper.base_url}/home/cases/{case_id}"

                    # Save case data snapshot first
                    self.storage.save_snapshot(current_snapshot)
                    logger.info(f"Processed {case_id}: {len(changes)} changes")

# Fetch and log attachments
                    attachments = scraper.fetch_attachments(case_id)
                    if attachments is not None:  # Empty list is valid
                        attachments_list = []
                        for a in attachments:
                            attachments_list.append({
                                "id": getattr(a, 'id', None),
                                "name": a.name,
                                "date_added": a.date_added,
                                "url": a.url
                            })
                        
                        attachments_snapshot = Snapshot(
                            account_id=account_login,
                            case_id=case_id,
                            endpoint_type="attachments",
                            raw_json={"attachments": [a.model_dump(mode="json") if hasattr(a, 'model_dump') else a.__dict__ for a in attachments]},
                            parsed_data={
                                "count": len(attachments),
                                "attachments": attachments_list
                            },
                            timestamp=datetime.utcnow()
                        )
                        
                        prev_attachments_snapshot = self.get_previous_snapshot(
                            account_id=account_login,
                            case_id=case_id,
                            endpoint_type="attachments"
                        )
                        attachment_changes = self.attachments_endpoint_detector.detect(prev_attachments_snapshot, attachments_snapshot)
                        if attachment_changes:
                            changes.extend(attachment_changes)
                            logger.info(f"Attachments endpoint changes for {case_id}: {len(attachment_changes)}")
                        
                        self.storage.save_snapshot(attachments_snapshot)
                        logger.info(f"Saved attachments for {case_id}: {len(attachments)} attachments")
                       
                    # Fetch and log questions
                    try:
                        questions = scraper.fetch_questions(case_id)
                        if questions is not None:  # Empty list is valid
                            questions_list = []
                            for q in questions:
                                questions_list.append({
                                    "id": q.id,
                                    "title": q.title,
                                    "body": q.content,
                                    "status": q.status,
                                    "status_label": q.status_label,
                                    "sentTime": q.sent_time,
                                    "answer": q.answer,
                                    "responseTime": q.response_time
                                })
                            
                            questions_snapshot = Snapshot(
                                account_id=account_login,
                                case_id=case_id,
                                endpoint_type="questions",
                                raw_json={"questions": [q.model_dump(mode="json") if hasattr(q, 'model_dump') else q.__dict__ for q in questions]},
                                parsed_data={
                                    "count": len(questions),
                                    "totalResults": getattr(scraper, '_last_total_results', 0),
                                    "questions": questions_list
                                },
                                timestamp=datetime.utcnow()
                            )
                            
                            prev_questions_snapshot = self.get_previous_snapshot(
                                account_id=account_login,
                                case_id=case_id,
                                endpoint_type="questions"
                            )
                            question_changes = self.questions_endpoint_detector.detect(prev_questions_snapshot, questions_snapshot)
                            if question_changes:
                                changes.extend(question_changes)
                                logger.info(f"Questions endpoint changes for {case_id}: {len(question_changes)}")
                            
                            self.storage.save_snapshot(questions_snapshot)
                            logger.info(f"Saved questions for {case_id}: {len(questions)} questions")
                    except Exception as e:
                        logger.error(f"Error processing case {case_id}: {e}")

                    # Accumulate case for notification AFTER all endpoint changes are detected
                    if self.notifier:
                        try:
                            self.notifier.on_change(
                                account_id=account_name,
                                account_login=account_login,
                                case_id=case_id,
                                changes=changes,
                                case_type=current_data.case_type,
                                person_first=current_data.person_first,
                                case_url=case_url,
                                status=current_data.status_raw
                            )
                        except Exception as e:
                            logger.error(f"Failed to accumulate notification: {e}")
                    
                    if changes:
                        results[account_name].extend(changes)
                        continue
                    processed.add(case_id)

                except Exception as e:
                    logger.error(f"Error processing case {case_id}: {e}")
                    continue

        return results


def detect_changes(old_snapshot: Optional[Snapshot], new_snapshot: Snapshot) -> List[Change]:
    """Convenience function for change detection (used by tests).

    Args:
        old_snapshot: Previous snapshot (can be None)
        new_snapshot: Current snapshot

    Returns:
        List of detected changes
    """
    detector = Detector(None)
    return detector.detect_changes(old_snapshot, new_snapshot)


def detect_all_changes(
    storage: SnapshotRepository,
    sessions: dict,
    credentials: dict,
    notifier=None
) -> dict:
    """Convenience function to detect changes across all cases."""
    import asyncio
    detector = Detector(storage, notifier=notifier)
    return asyncio.run(detector.detect_all_changes(sessions, credentials, notifier))
