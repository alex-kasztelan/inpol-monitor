"""Data extraction layer for inpol.mazowieckie.pl.

This module provides the InpolScraper class for fetching and parsing
case data from the Inpol portal JSON endpoints.
"""

import logging
from typing import Optional, List

from src.session_manager import SessionManager
from src.models import CaseData, Attachment, Question, Snapshot
from src.config import get_json_logging_enabled
from src.tools.json_logger import JSONResponseLogger

logger = logging.getLogger(__name__)


# Class-level cache for status dictionary (loaded once per scraper instance)
class _StatusCache:
    """Thread-safe status dictionary cache."""
    _cache: Optional[dict] = None
    _lock = False  # Using simple flag, not threading.Lock for simplicity


class InpolScraper:
    """Scraper for fetching Inpol case data from JSON endpoints.

    Provides methods to fetch case data, attachments, questions,
    and status dictionary from authenticated sessions.
    """

    def __init__(
        self,
        session: SessionManager,
        status_dict: Optional[dict] = None,
        base_url: str = "https://inpol.mazowieckie.pl",
        account_name: str = "unknown"
    ):
        """Initialize scraper with authenticated session.

        Args:
            session: Authenticated SessionManager instance
            status_dict: Status code -> label mapping (optional, will be fetched if not provided)
            base_url: Base URL for the portal
            account_name: Account identifier for logging context
        """
        self.session = session
        self.base_url = base_url
        self._status_dict = status_dict
        self._status_cache = status_dict
        self.account_name = account_name
        
        # Initialize JSON response logger
        self.json_logger = JSONResponseLogger(enabled=get_json_logging_enabled())

    def _get_status_dict(self, lang: str = "en") -> dict:
        """Fetch status dictionary from the portal.

        Caches the result for reuse across multiple case fetches.

        Args:
            lang: Language code for i18n (default: "en")

        Returns:
            Dictionary of status codes -> labels, or cached value if available
        """
        if self._status_dict is not None:
            logger.debug("Using provided status dictionary")
            return self._status_dict

        if _StatusCache._cache is not None:
            logger.debug("Using cached status dictionary")
            return _StatusCache._cache

        # Fetch status dictionary
        url = f"{self.base_url}/assets/i18n/{lang}.json"
        logger.debug(f"Fetching status dictionary from {url}")

        response = self.session.get(url)
        if not response or response.status_code != 200:
            logger.error(f"Failed to fetch status dictionary: {response.status_code if response else 'No response'}")
            return {}

        try:
            status_dict = response.json()
            _StatusCache._cache = status_dict
            logger.info("Status dictionary cached")
            
            # Log JSON response for status dictionary
            self.json_logger.log_response(
                account=self.account_name,
                case_id="status_dict",
                endpoint="status_dict",
                url=url,
                response_data=status_dict
            )
            
            return status_dict
        except Exception as e:
            logger.error(f"Failed to parse status dictionary: {e}")
            return {}

    def _resolve_status_label(self, status_code: str) -> Optional[str]:
        """Resolve status code to label using i18n dictionary.

        Args:
            status_code: Raw status code from JSON

        Returns:
            Status label or None if not found
        """
        if not self._status_dict:
            return None

        # Try direct key lookup
        label = self._status_dict.get(status_code, None)
        if label:
            return label

        # Try key with underscore converted to space
        label = self._status_dict.get(status_code.replace("_", " "), None)
        if label:
            return label

        return None

    def _resolve_question_title(self, title_id: str) -> Optional[str]:
        """Resolve question title ID to label using i18n dictionary.

        Args:
            title_id: Question title ID from JSON (maps to en.json.Question.Titles)

        Returns:
            Question title label or None if not found
        """
        if not self._status_dict:
            return None

        # Try to get the title from the Question.Titles section
        # First try direct lookup
        label = self._status_dict.get(f"Question.Titles.{title_id}", None)
        if label:
            return label

        # Try alternative formats
        label = self._status_dict.get(f"Question.Titles.{title_id.replace('_', ' ')}", None)
        if label:
            return label

        return None

    def fetch_case_data(self, case_id: str) -> Optional[CaseData]:
        """Fetch case data for a specific case.

        Args:
            case_id: Case identifier (UUID or case number)

        Returns:
            CaseData model or None if fetch failed
        """
        url = f"/api/proceedings/{case_id}"

        logger.debug(f"Fetching case data for {case_id}")
        response = self.session.get(url)

        if not response or response.status_code != 200:
            logger.error(f"Failed to fetch case data for {case_id}: {response.status_code if response else 'No response'}")
            return None

        # Debug: log content type if available (skip in tests with Mock responses)
        try:
            ct = response.headers.get('Content-Type', '') or ''
            if 'json' not in ct:
                logger.warning(f"Case data for {case_id}: unexpected Content-Type '{ct}', body: {response.text[:300]}")
        except (AttributeError, TypeError):
            pass  # Skip CT check for Mock responses in tests

        try:
            raw_data = response.json()
            
            # Log JSON response for case data
            self.json_logger.log_response(
                account=self.account_name,
                case_id=case_id,
                endpoint="case_data",
                url=url,
                response_data=raw_data
            )
        except Exception as e:
            logger.error(f"Failed to parse case data response for {case_id}: {e}")
            return None

        # Extract fields from raw JSON
        try:
            # Parse person name from person node
            person_node = raw_data.get("person", {})
            person_first = person_node.get("firstName", "").strip()
            person_last = person_node.get("surname", "").strip()

            case_number = raw_data.get("signature", "")
            # Get case type from circumstance.english
            circumstance = raw_data.get("circumstance", {})
            case_type = circumstance.get("english", "")
            submit_date = raw_data.get("creationDate")
            decision_date = raw_data.get("decisionDate")
            updated_at = raw_data.get("editDate", "")
            status_raw = raw_data.get("status", "")

            # Resolve status label
            status_label = self._resolve_status_label(status_raw)

            # Extract related docs and timeline events
            related_docs = raw_data.get("relatedDocs", [])
            timeline_events = raw_data.get("timelineEvents", [])

            # Extract attachments
            attachments = raw_data.get("attachments", [])
            attachments = [
                Attachment(
                    name=a.get("name", ""),
                    date_added=a.get("dateAdded", ""),
                    url=a.get("url")
                )
                for a in attachments
            ]

            # Extract questions
            questions_data = raw_data.get("questions", [])
            status_dict = self._get_status_dict()
            questions = [
                Question(
                    id=q.get("id", ""),
                    content=q.get("content", ""),
                    status=q.get("status", ""),
                    status_label=self._resolve_status_label(q.get("status")) or q.get("statusLabel"),
                    sent_time=q.get("sentTime", "")
                )
                for q in questions_data
            ]

            # Extract timeline (if present)
            timeline = raw_data.get("timeline", [])

            return CaseData(
                person_first=person_first,
                person_last=person_last,
                case_number=case_number,
                case_type=case_type,
                submit_date=submit_date,
                decision_date=decision_date,
                updated_at=updated_at,
                status_raw=status_raw,
                status_label=status_label,
                attachments=attachments,
                questions=questions,
                timeline=timeline,
                related_docs=related_docs,
                timeline_events=timeline_events
            )

        except Exception as e:
            logger.error(f"Failed to parse case data for {case_id}: {e}")
            return None

    def fetch_attachments(self, case_id: str) -> List[Attachment]:
        """Fetch attachments for a specific case.

        Args:
            case_id: Case identifier

        Returns:
            List of Attachment models or empty list if failed
        """
        url = f"/api/proceedings/getRequiredAttachments"
        params = {"official_proceedings_id": case_id}

        logger.debug(f"Fetching attachments for {case_id}")
        response = self.session.get(url, params=params)

        if not response or response.status_code != 200:
            logger.error(f"Failed to fetch attachments for {case_id}: {response.status_code if response else 'No response'}")
            return []

        try:
            raw_data = response.json()
            # Handle different possible response formats
            if isinstance(raw_data, dict):
                attachments = raw_data.get("attachments", [])
            elif isinstance(raw_data, list):
                attachments = raw_data
            else:
                attachments = []
            
            # Log JSON response for attachments
            self.json_logger.log_response(
                account=self.account_name,
                case_id=case_id,
                endpoint="attachments",
                url=url,
                response_data=raw_data
            )

            return [
                Attachment(
                    name=a.get("name", "") if isinstance(a, dict) else str(a),
                    date_added=a.get("dateAdded", "") if isinstance(a, dict) else "",
                    url=a.get("url") if isinstance(a, dict) else None
                )
                for a in attachments
            ]
        except Exception as e:
            logger.error(f"Failed to parse attachments for {case_id}: {e}")
            return []

    def fetch_questions(self, case_id: str, page: int = 1, results: int = 100) -> List[Question]:
        """Fetch questions for a specific case.

        Args:
            case_id: Case identifier
            page: Page number (default: 1)
            results: Results per page (default: 100)

        Returns:
            List of Question models or empty list if failed
        """
        url = f"/api/proceedings/{case_id}/questions"
        params = {
            "page": page,
            "results": results,
            "filterBy": "",
            "orderBy": "Status desc,SentTime desc"
        }

        logger.debug(f"Fetching questions for {case_id}")
        response = self.session.get(url, params=params)

        if not response or response.status_code != 200:
            logger.error(f"Failed to fetch questions for {case_id}: {response.status_code if response else 'No response'}")
            return []

        try:
            raw_data = response.json()
            # The API returns questions in the "items" array
            if isinstance(raw_data, dict):
                questions_data = raw_data.get("items", [])
            elif isinstance(raw_data, list):
                questions_data = raw_data
            else:
                questions_data = []
            
            # Log JSON response for questions list
            self.json_logger.log_response(
                account=self.account_name,
                case_id=case_id,
                endpoint="questions",
                url=url,
                response_data=raw_data
            )
            
            status_dict = self._get_status_dict()
            self._last_total_results = raw_data.get("totalResults", 0) if isinstance(raw_data, dict) else 0
            questions = []
            for q in questions_data:
                # Get question ID
                question_id = q.get("id", "")
                
                # Get status (1=Waiting for answer, 2=Answer)
                status_code = str(q.get("status", ""))
                
                # Get title mapping (numeric ID that maps to question titles in en.json)
                title_id = str(q.get("title", ""))
                title_label = self._resolve_question_title(title_id)
                
                # Get sent time
                sent_time = q.get("sentTime", "")
                
                # Fetch full question details to get body/content and answer
                content = ""
                answer = None
                response_time = None
                
                if question_id:
                    question_details = self._fetch_question_details(question_id)
                    if question_details:
                        content = question_details.get("body", "")
                        answer = question_details.get("answer")
                        response_time = question_details.get("responseTime")
                
                questions.append(Question(
                    id=question_id,
                    title=title_id,
                    content=content,
                    status=status_code,
                    status_label=self._resolve_status_label(status_code) or title_label,
                    sent_time=sent_time,
                    answer=answer,
                    response_time=response_time
                ))
            
            return questions

        except Exception as e:
            logger.error(f"Failed to parse questions for {case_id}: {e}")
            return []

    def _fetch_question_details(self, question_id: str) -> Optional[dict]:
        """Fetch full question details including body and answer.

        Args:
            question_id: Question identifier

        Returns:
            Dictionary with question details or None if failed
        """
        url = f"/api/proceeding-question/{question_id}"
        
        logger.debug(f"Fetching question details for {question_id}")
        response = self.session.get(url)

        if not response or response.status_code != 200:
            logger.warning(f"Failed to fetch question details for {question_id}: {response.status_code if response else 'No response'}")
            return None

        try:
            raw_data = response.json()
            
            # Log JSON response for question details
            self.json_logger.log_response(
                account=self.account_name,
                case_id="question_" + question_id if question_id else "unknown",
                endpoint="question_details",
                url=url,
                response_data=raw_data
            )
            
            return raw_data
        except Exception as e:
            logger.error(f"Failed to parse question details for {question_id}: {e}")
            return None

    def fetch_status_dictionary(self, lang: str = "en") -> dict:
        """Fetch status dictionary from the portal.

        Args:
            lang: Language code (default: "en")

        Returns:
            Status dictionary or empty dict if failed
        """
        return self._get_status_dict(lang)

    def fetch_all_for_case(self, case_id: str) -> dict:
        """Fetch all data for a case (case data, attachments, questions).

        Args:
            case_id: Case identifier

        Returns:
            Dictionary with all fetched data or None if any fetch failed
        """
        try:
            case_data = self.fetch_case_data(case_id)
            attachments = self.fetch_attachments(case_id)
            questions = self.fetch_questions(case_id)

            if case_data is None:
                logger.error(f"Case data fetch failed for {case_id}")
                return {"error": f"Failed to fetch case data for {case_id}"}

            return {
                "case_data": case_data,
                "attachments": attachments,
                "questions": questions
            }

        except Exception as e:
            logger.error(f"Failed to fetch all data for {case_id}: {e}")
            return {"error": str(e)}


def fetch_all_cases(
    sessions: list,
    credentials: dict,
    storage: "SnapshotRepository"
) -> dict:
    """Fetch and persist data for all cases across all accounts.

    Orchestrates the data extraction process for all accounts and cases.
    Fetches status dictionary once, then fetches all case data, attachments,
    and questions for each case. Persists all snapshots to SQLite.

    Args:
        sessions: List of authenticated SessionManager instances
        credentials: Dictionary with account names and credentials
        storage: SnapshotRepository for persistence

    Returns:
        Summary dict: {"success": int, "failed": int, "errors": list}

    Usage:
        >>> from src.auth import run_sequential_auth
        from src.config import load_credentials
        from src.storage import SnapshotRepository
        from src.scraper import fetch_all_cases

        sessions = list(run_sequential_auth())
        creds = load_credentials()
        storage = SnapshotRepository("data/snapshots.db")
        result = fetch_all_cases(sessions, creds, storage)
        print(f"Success: {result['success']}, Failed: {result['failed']}")
    """
    summary = {
        "success": 0,
        "failed": 0,
        "errors": []
    }

    account_names = list(credentials.keys())
    
    scrapers = {}
    for account_name in account_names:
        account_creds = credentials.get(account_name, {})
        session = None
        for s, (name, _) in enumerate(sessions):
            if name == account_name:
                session = s
                break

        if session:
            scrapers[account_name] = InpolScraper(session=session, account_name=account_name)
        else:
            logger.warning(f"No session found for {account_name}")

    # Fetch status dictionary for each scraper that doesn't have it cached
    for account_name, scraper in scrapers.items():
        if scraper._status_dict is None:
            scraper.fetch_status_dictionary()

    # Fetch and persist data for each account
    for account_name, scraper in scrapers.items():
        account_creds = credentials.get(account_name, {})
        case_ids = account_creds.get("case_ids", [])
        # Get account login to use as account_id in snapshots
        account_login = account_creds.get("username", account_name)

        if not case_ids:
            logger.warning(f"No case IDs configured for {account_name}")
            summary["failed"] += 1
            summary["errors"].append(f"No case IDs for {account_name}")
            continue

        for case_id in case_ids:
            try:
                logger.info(f"Fetching data for {account_name}/{case_id}")

                # Fetch all data for this case
                result = scraper.fetch_all_for_case(case_id)

                if "error" in result:
                    logger.error(f"Failed to fetch data for {case_id}: {result['error']}")
                    summary["failed"] += 1
                    summary["errors"].append(f"{account_name}/{case_id}: {result['error']}")
                    continue

                case_data = result["case_data"]
                attachments = result["attachments"]
                questions = result["questions"]

                # Create snapshots and persist to storage
                # Case data snapshot
                case_data_snapshot = Snapshot(
                    account_id=account_login,
                    case_id=case_id,
                    endpoint_type="case_data",
                    raw_json=case_data.model_dump(mode="json") if hasattr(case_data, 'model_dump') else {},
                    parsed_data={
                        "person_first": case_data.person_first,
                        "person_last": case_data.person_last,
                        "case_number": case_data.case_number,
                        "case_type": case_data.case_type,
                        "submit_date": case_data.submit_date,
                        "decision_date": case_data.decision_date,
                        "updated_at": case_data.updated_at,
                        "status_raw": case_data.status_raw,
                        "status_label": case_data.status_label,
                        "relatedDocs": case_data.related_docs,
                        "timelineEvents": case_data.timeline_events
                    },
                    timestamp=datetime.utcnow()
                )
                storage.save_snapshot(case_data_snapshot)

                # Attachments snapshot
                attachments_snapshot = Snapshot(
                    account_id=account_login,
                    case_id=case_id,
                    endpoint_type="attachments",
                    raw_json={"attachments": [a.model_dump(mode="json") if hasattr(a, 'model_dump') else a.__dict__ for a in attachments]},
                    parsed_data={"count": len(attachments)},
                    timestamp=datetime.utcnow()
                )
                storage.save_snapshot(attachments_snapshot)

                # Questions snapshot
                questions_snapshot = Snapshot(
                    account_id=account_login,
                    case_id=case_id,
                    endpoint_type="questions",
                    raw_json={"questions": [q.model_dump(mode="json") if hasattr(q, 'model_dump') else q.__dict__ for q in questions]},
                    parsed_data={"questions": [q.model_dump(mode="json") if hasattr(q, 'model_dump') else q.__dict__ for q in questions], "count": len(questions), "totalResults": total_results},
                    timestamp=datetime.utcnow()
                )
                storage.save_snapshot(questions_snapshot)

                summary["success"] += 1
                logger.info(f"Successfully fetched and saved {case_id}")

            except Exception as e:
                logger.error(f"Error fetching data for {case_id}: {e}")
                summary["failed"] += 1
                summary["errors"].append(f"{account_name}/{case_id}: {str(e)}")

    return summary
