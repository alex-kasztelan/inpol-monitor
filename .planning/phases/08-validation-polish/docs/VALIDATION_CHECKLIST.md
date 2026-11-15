# Phase 08: Validation & Polish - Manual Verification Checklist

## ✅ Prerequisites
- [ ] All Phase 01-07 tests passing (147 tests)
- [ ] Development environment set up with Python 3.11+
- [ ] Valid `.env` file with Telegram bot token (can be test token)
- [ ] Valid `credentials.json` with test accounts

## 🔧 Setup Verification
- [ ] Run `python -m pytest tests/ -q` → should show 147 passed
- [ ] Verify `check.py -v` runs without authentication errors
- [ ] Confirm database file created at `data/snapshots.db`

## 📊 Change Detection Validation
### Core Functionality
- [ ] Status changes detected correctly (numeric ID ↔ label translation)
- [ ] New document detection works (relatedDocs addition)
- [ ] Removed document detection works (relatedDocs removal)
- [ ] Date changes detected (decision_date, submit_date, updated_at)
- [ ] Timeline event detection works (new timelineEvents)
- [ ] Question detection works (new questions and status 1→2 transitions)

### Edge Cases
- [ ] First check (no previous snapshot) → returns empty changes
- [ ] Empty data arrays → handled gracefully
- [ ] Unknown status IDs → falls back to "Unknown (ID)" format
- [ ] Missing fields → handled with None/default values
- [ ] Multiple simultaneous changes → all detected and reported

## 📱 Notification Validation
### Format Verification
- [ ] Change notifications use MarkdownV2 formatting
- [ ] Messages grouped by change type (status → docs → dates)
- [ ] Case ID and account ID included in notifications
- [ ] Descriptive text includes both ID and label where applicable
- [ ] Error notifications follow format: "Error checking case X: [message]"

### Delivery Verification
- [ ] Notifications sent via Telegram when changes detected
- [ ] Error notifications sent on system failures
- [ ] Rate limiting handled gracefully (no crash on 429)
- [ ] Network failures handled without breaking main loop
- [ ] Message length respects Telegram 4096 character limit

## ⚡ Performance & Reliability
### Resource Usage
- [ ] Memory usage stable during extended runs
- [ ] Database connections properly closed
- [ ] HTTP sessions cleaned up after use
- [ ] No file handle leaks in storage layer

### Error Handling
- [ ] Authentication failures don't crash the system
- [ ] Scraper errors logged but don't halt processing
- [ ] Storage errors handled gracefully
- [ ] Detector errors logged but processing continues

## 🔄 Integration Testing
### End-to-End Flows
- [ ] Auth → Scrape → Detect → Notify → Store pipeline works
- [ ] Multiple accounts processed sequentially
- [ ] Multiple cases per account processed correctly
- [ ] Notifier batching works (one notification per account)
- [ ] Snapshot saving works after change detection

### Configuration Validation
- [ ] `.env` overrides work correctly
- [ ] Default values used when config missing
- [ ] Credentials loading handles malformed JSON
- [ ] Database path configurable via SnapshotRepository

## 📋 Final Sign-off
- [ ] All automated tests pass (running `pytest -q`)
- [ ] Manual verification checklist completed
- [ ] Golden file validation script runs without diffs
- [ ] Documentation reviewed and accurate
- [ ] Ready for production deployment consideration

## 📝 Notes
```
Validation performed by: ________________________
Date: ________________________
Environment: ________________________
Git commit: ________________________
```