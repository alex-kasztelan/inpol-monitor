---
phase: 01
slug: project-foundation-authentication
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds (2 test files) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | AUTH-02 | unit | `pytest tests/test_config.py -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | AUTH-02 | unit | `pytest tests/test_config.py -x` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | AUTH-01 | integration | `pytest tests/test_auth.py -x` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | AUTH-01 | integration | `pytest tests/test_auth.py -x` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 3 | AUTH-01, AUTH-02 | integration | `pytest tests/ -x` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 3 | AUTH-01, AUTH-02 | integration | `pytest tests/ -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (sample login HTML, mock sessions)
- [ ] `tests/test_config.py` — credential loading and config tests
- [ ] `tests/test_auth.py` — authentication flow tests with recorded HTML
- [ ] `pytest.ini` — pytest configuration
- [ ] `pip install pytest` — if not already installed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real login to inpol.mazowieckie.pl | AUTH-01 | Requires live credentials and network | After automated tests pass, run `python check.py -v` with real credentials and verify successful login |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
