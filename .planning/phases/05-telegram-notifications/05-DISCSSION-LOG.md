# Phase 05: Telegram Notifications - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 05-telegram-notifications
**Areas discussed:** Telegram library, Message format, Error notifications, Bot setup

---

## Telegram Library Selection

| Option | Description | Selected |
|--------|-------------|----------|
| aiogram 3.x | Modern, async-first, actively maintained | ✓ |
| python-telegram-bot | Mature, widely used, good documentation | |
| Other | Let me describe a different approach | |

**User's choice:** aiogram 3.x
- Async-first architecture
- Active development and good documentation
- Recommended in ARCHITECTURE.md
- Built-in bot handlers and error handling

**Notes:** aiogram 3.x was selected because it's recommended in the architecture research and provides async support which is beneficial for handling multiple checks concurrently.

---

## Message Format

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown | Bold, italic, lists - standard for Telegram alerts | ✓ |
| HTML | More styling options (colors, emojis) | |
| Plain text only | Simplest, most reliable delivery | |

**User's choice:** Markdown
- Bold text (`**text**`)
- Italic text (`*text*`)
- Lists (`- items`)

**Notes:** Markdown was selected as it's the standard for Telegram alerts and provides good readability without the overhead of HTML parsing.

---

## Error Notification Conditions

| Option | Description | Selected |
|--------|-------------|----------|
| Only when changes detected | Standard monitoring behavior | |
| Only on errors | ERROR-01 requirement - notify when check fails | |
| Both changes and errors | Comprehensive - notify for any issue | ✓ |

**User's choice:** Both changes and errors
- Send notification when status changes detected
- Send notification when check fails (site down, login fails, API errors)
- ERROR-01 requirement: Send error notification to Telegram when check fails

**Notes:** Both changes and errors was selected to ensure comprehensive notification coverage. This satisfies the ERROR-01 requirement while also providing visibility into case status changes.

---

## Telegram Bot Setup

| Option | Description | Selected |
|--------|-------------|----------|
| Use existing Telegram bot | User has existing Telegram bot | |
| Create new bot | Fresh bot via @BotFather | ✓ |
| Other | Let me describe a different approach | |

**User's choice:** Create new bot
- Full control over bot configuration
- Clean separation from user's existing Telegram setup
- New bot token stored in `.env` file

**Notes:** A new bot was created to provide clean separation from any user's existing Telegram setup. The bot token will be stored in the `.env` file.

---

## Claude's Discretion

None — all decisions captured above

---

## Deferred Ideas

None — discussion stayed within phase scope
