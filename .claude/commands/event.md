---
description: Inspect, replay, or publish a Redis Streams event for debugging the event-driven pipeline
argument-hint: "list | inspect <stream> | replay <stream> <message_id> | publish <event_name> <application_id>"
allowed-tools: Bash(docker compose exec:*)
---

## Context

- Redis Streams: !`docker compose exec redis redis-cli --no-auth-warning KEYS "*.created" "*.completed" "*.requested" "*.paused" "*.approved" "*.rejected" 2>/dev/null || echo "Redis not running"`
- Arguments: $ARGUMENTS

## Your task

Interact with Redis Streams events for the Loan pipeline.

Parse `$ARGUMENTS` to determine the action. If empty, default to `list`.

### `list` — Show all streams and their lengths
```
docker compose exec redis redis-cli XLEN application.created
docker compose exec redis redis-cli XLEN node.completed
docker compose exec redis redis-cli XLEN hitl.requested
docker compose exec redis redis-cli XLEN pipeline.paused
docker compose exec redis redis-cli XLEN hitl.approved
docker compose exec redis redis-cli XLEN hitl.rejected
docker compose exec redis redis-cli XLEN pipeline.completed
docker compose exec redis redis-cli XLEN pipeline.rejected
```
Display as a table with stream name, message count, last message ID, and last message timestamp.

Also show consumer group lag:
```
docker compose exec redis redis-cli XINFO GROUPS <stream_name>
```

### `inspect <stream>` — Show recent messages from a stream
```
docker compose exec redis redis-cli XREVRANGE <stream> + - COUNT 5
```
Format each message as a readable JSON-like block with timestamp.

### `replay <stream> <message_id>` — Re-deliver a specific message
Read the message from the stream:
```
docker compose exec redis redis-cli XRANGE <stream> <message_id> <message_id>
```
Then republish it to the same stream (useful for retrying failed processing):
```
docker compose exec redis redis-cli XADD <stream> "*" <field1> <value1> ...
```
Warn the user this will cause the event to be processed again.

### `publish <event_name> <application_id>` — Manually publish an event

Valid event names: `application.created`, `hitl.approved`, `hitl.rejected`, `pipeline.completed`

Build the appropriate payload and publish:
```
docker compose exec redis redis-cli XADD <event_name> "*" \
  application_id <application_id> \
  timestamp <now_iso> \
  source manual
```

Confirm: "Published `<event_name>` for application `<application_id>`"
Then watch for a response event (e.g. `node.completed`) for 10 seconds.

### Notes
- Replaying events can cause duplicate processing. Always warn the user.
- Pending messages in consumer groups are separate from stream length — show both.
