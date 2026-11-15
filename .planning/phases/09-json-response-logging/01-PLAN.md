--- 
phase: 09-json-response-logging 
plan: 01 
type: execute 
depends_on: 
  - 01-overview.md 
files_modified: 
  - src/config.py 
  - src/tools/json_logger.py 
  - src/scraper.py 
  - .env.example 
autonomous: true 
requirements: 
  - JSON-LOG-01: JSON logging configuration 
  - JSON-LOG-02: JSON response logger utility 
  - JSON-LOG-03: Scraper integration at 5 endpoints 
  - JSON-LOG-04: Environment variable documentation 
  - JSON-LOG-05: Backward compatibility 
user_setup: 
  - service: json logging 
  - why: "Need to enable JSON logging via environment variable" 
  - manual_steps: 
    - "Add JSON_LOGGING_ENABLED=true to .env to enable logging" 
    - "Set JSON_LOGGING_ENABLED=false or omit to disable (default)" 
must_haves: 
  truths: 
    - "JSON logs created in logs/json_responses.log when enabled" 
    - "Log entries contain timestamp, account, case_id, endpoint, url, response_size, json_data" 
    - "All 5 API endpoints log JSON responses when logging enabled" 
    - "No logging occurs when JSON_LOGGING_ENABLED=false or unset" 
    - "Existing functionality unchanged regardless of logging setting" 
    - "Log format is valid JSON Lines (one JSON object per line)" 
  artifacts: 
    - path: "src/config.py" 
      provides: "JSON logging configuration function" 
      exports: ["get_json_logging_enabled"] 
    - path: "src/tools/json_logger.py" 
      provides: "JSON response logger utility class" 
      exports: ["JSONResponseLogger"] 
    - path: "src/scraper.py" 
      provides: "Modified scraper with JSON logging integration" 
      exports: ["InpolScraper.__init__", "InpolScraper._get_status_dict", "InpolScraper.fetch_case_data", "InpolScraper.fetch_attachments", "InpolScraper.fetch_questions", "InpolScraper._fetch_question_details"] 
    - path: "logs/json_responses.log" 
      provides: "Structured JSON log file (when enabled)" 
    - path: ".env.example" 
      provides: "Updated example environment file" 
      exports: ["JSON_LOGGING_ENABLED"] 
key_links: 
  - from: "src/config.py:get_json_logging_enabled" 
    to: "src/scraper.py:InpolScraper.__init__" 
    via: "configuration check" 
    pattern: "get_json_logging_enabled\(\)" 
  - from: "src/tools/json_logger.py:JSONResponseLogger" 
    to: "src/scraper.py:InpolScraper.__init__" 
    via: "logger initialization" 
    pattern: "JSONResponseLogger" 
  - from: "src/scraper.py:InpolScraper._get_status_dict" 
    to: "src/tools/json_logger.py:JSONResponseLogger.log_response" 
    via: "status dictionary logging" 
    pattern: "log_response.*status_dict" 
  - from: "src/scraper.py:InpolScraper.fetch_case_data" 
    to: "src/tools/json_logger.py:JSONResponseLogger.log_response" 
    via: "case data logging" 
    pattern: "log_response.*case_data" 
  - from: "src/scraper.py:InpolScraper.fetch_attachments" 
    to: "src/tools/json_logger.py:JSONResponseLogger.log_response" 
    via: "attachments logging" 
    pattern: "log_response.*attachments" 
  - from: "src/scraper.py:InpolScraper.fetch_questions" 
    to: "src/tools/json_logger.py:JSONResponseLogger.log_response" 
    via: "questions list logging" 
    pattern: "log_response.*questions" 
  - from: "src/scraper.py:InpolScraper._fetch_question_details" 
    to: "src/tools/json_logger.py:JSONResponseLogger.log_response" 
    via: "question details logging" 
    pattern: "log_response.*question_details" 
--- 

# Phase 09 JSON Response Logging - Plan 

## Objective 
Implement comprehensive logging of raw JSON responses received from inpol.mazowieckie.pl API endpoints to enable detailed post-execution analysis and debugging. 

## Context 
Phase 08 validation complete - System validated and ready for production. Phase 09 enhances observability by capturing raw API responses for offline analysis. 

## Tasks 

### Task 1: Implement JSON logging configuration 

**Files**: src/config.py 

**Action**: 
- Add get_json_logging_enabled() function to check JSON_LOGGING_ENABLED environment variable 
- Return True when set to "true" (case-insensitive), False otherwise 
- Follow existing configuration patterns in the file 

**Verify**: 
- Function exists and returns correct boolean values 
- Defaults to False when variable unset or invalid 
- Returns True when set to "true", "True", "TRUE" 

### Task 2: Create JSON response logger utility 

**Files**: src/tools/json_logger.py 

**Action**: 
- Create JSONResponseLogger class 
- Initialize logging to logs/json_responses.log when enabled 
- Format log entries as JSON Lines (one JSON object per line) 
- Include metadata: timestamp, account, case_id, endpoint, url, response_size, json_data 
- Ensure thread-safe operation 
- Prevent duplicate logger initialization 

**Verify**: 
- Class exists and initializes correctly 
- Logging only occurs when enabled 
- Log entries are valid JSON Lines 
- All required metadata fields present 
- No interference with existing logging 

### Task 3: Integrate JSON logging into scraper 

**Files**: src/scraper.py 

**Action**: 
- Import JSONResponseLogger and configuration 
- Initialize logger in __init__ method 
- Add logging calls after each successful response.json(): 
  1. Status dictionary fetch (_get_status_dict method) 
  2. Case data fetch (fetch_case_data method) 
  3. Attachments fetch (fetch_attachments method) 
  4. Questions list fetch (fetch_questions method) 
  5. Question details fetch (_fetch_question_details method) 
- Pass appropriate context for each endpoint 
- Handle case where case_id may not be available (status dictionary) 

**Verify**: 
- Logger initialized in scraper constructor 
- Logging occurs at all 5 JSON response points 
- Context includes correct account, case_id, endpoint information 
- Logging gracefully handles missing context 
- No impact on existing functionality or error handling 

### Task 4: Update environment documentation 

**Files**: .env.example 

**Action**: 
- Add JSON_LOGGING_ENABLED variable to example file 
- Include description and default value 
- Follow existing comment style 

**Verify**: 
- Variable documented in .env.example 
- Clear explanation of purpose and values 
- Consistent with existing environment variables 

### Task 5: Verify backward compatibility 

**Files**: All modified files 

**Action**: 
- Ensure existing functionality works when JSON_LOGGING_ENABLED=false or unset 
- Test that log file is not created when disabled 
- Verify no performance impact when disabled 
- Confirm all existing tests pass 

**Verify**: 
- System operates identically when logging disabled 
- Log file only created when explicitly enabled 
- No changes to existing behavior or outputs 
- All validation tests continue to pass 

## Acceptance Criteria 

| Criterion | Status | 
|-----------|--------| 
| JSON-LOG-01: JSON logging configuration | ☑ Complete | 
| JSON-LOG-02: JSON response logger utility | ☑ Complete | 
| JSON-LOG-03: Scraper integration at 5 endpoints | ☑ Complete | 
| JSON-LOG-04: Environment variable documentation | ☑ Complete | 
| JSON-LOG-05: Backward compatibility | ☑ Complete | 

## Test Coverage 

- Unit tests for JSON logging configuration 
- Validation of JSON logger output format 
- Integration tests for scraper logging points 
- Backward compatibility verification 
- Performance impact assessment 

## Known Edge Cases 

1. **Disabled logging**: No log file created, zero performance impact 
2. **Missing context**: Graceful handling when account/case_id unavailable 
3. **Large responses**: Proper sizing regardless of response size 
4. **Concurrent access**: Thread-safe logging operations 
5. **Log file permissions**: Proper file creation and access rights 

## Output 

After completion: 
- JSON logging configurable via JSON_LOGGING_ENABLED environment variable 
- Structured JSON logs created in logs/json_responses.log when enabled 
- All 5 API endpoint responses logged with contextual metadata 
- No impact on existing functionality when disabled 
- Existing tests continue to pass 
- Ready for production deployment with enhanced observability 