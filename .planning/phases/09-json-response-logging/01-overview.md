# Phase 09: JSON Response Logging - Overview

## Goal
Implement comprehensive logging of raw JSON responses received from inpol.mazowieckie.pl API endpoints to enable detailed post-execution analysis and debugging.

## Scope (Locked)

### JSON Response Logging
- **Status Dictionary Endpoint** - Log raw JSON from /assets/i18n/{lang}.json
- **Case Data Endpoint** - Log raw JSON from /api/proceedings/{case_id}
- **Attachments Endpoint** - Log raw JSON from /api/proceedings/getRequiredAttachments
- **Questions List Endpoint** - Log raw JSON from /api/proceedings/{case_id}/questions
- **Question Details Endpoint** - Log raw JSON from /api/proceeding-question/{question_id}

### Implementation Requirements
- Create structured JSON log files in logs/ directory
- One JSON object per line format for easy parsing
- Include contextual metadata (timestamp, account, case_id, endpoint)
- Respect existing logging infrastructure and patterns
- Enable/disable via environment variable JSON_LOGGING_ENABLED
- No impact on existing functionality when disabled

### Deliverables
1. JSON logging configuration in src/config.py
2. JSON response logger utility in src/tools/json_logger.py
3. Modified scraper.py with JSON logging integration at 5 response points
4. Updated .env.example with JSON_LOGGING_ENABLED variable
5. Documentation in phase overview

## Acceptance Criteria
- JSON logs created when JSON_LOGGING_ENABLED=true
- Structured log format with all required metadata
- All 5 API endpoint responses logged appropriately
- No performance impact when JSON_LOGGING_ENABLED=false
- Existing tests continue to pass
- Manual verification shows usable log format for analysis

## Notes
This phase focuses purely on enhancing observability by capturing the raw API responses that drive the system. The logged data will enable:
- Post-execution analysis of API behavior
- Debugging of parsing issues
- Validation against expected API schemas
- Historical tracking of API changes
- Offline reproduction of issues