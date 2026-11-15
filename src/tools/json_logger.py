"""JSON response logger utility for Inpol Monitor.

This module provides a utility for logging raw JSON responses from API endpoints
to enable detailed post-execution analysis.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any


class JSONResponseLogger:
    """Logger for raw JSON responses from API endpoints."""
    
    def __init__(self, enabled: bool = False):
        """Initialize JSON response logger.
        
        Args:
            enabled: Whether JSON logging is enabled
        """
        self.enabled = enabled
        self.logger = logging.getLogger("json_responses")
        
        # Only set up file handler if logging is enabled and not already configured
        if enabled and not self.logger.handlers:
            # Ensure logs directory exists
            import os
            from pathlib import Path
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # Set up file handler for JSON logs
            handler = logging.FileHandler(log_dir / "json_responses.log")
            formatter = logging.Formatter('%(message)s')  # Raw JSON lines
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            self.logger.propagate = False  # Don't propagate to root logger
    
    def log_response(self, account: str, case_id: str, endpoint: str, 
                    url: str, response_data: Dict[Any, Any]) -> None:
        """Log a JSON response with contextual metadata.
        
        Args:
            account: Account identifier (account1/account2)
            case_id: Case identifier
            endpoint: Endpoint type (status_dict, case_data, attachments, questions, question_details)
            url: Full URL endpoint called
            response_data: Parsed JSON response data
        """
        if not self.enabled:
            return
            
        # Create structured log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account": account,
            "case_id": case_id,
            "endpoint": endpoint,
            "url": url,
            "response_size": len(json.dumps(response_data, default=str)),
            "json_data": response_data
        }
        
        # Log as JSON line (one JSON object per line for easy parsing)
        self.logger.info(json.dumps(log_entry, default=str))