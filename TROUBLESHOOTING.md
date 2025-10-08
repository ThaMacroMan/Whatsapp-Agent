# 🔧 Troubleshooting Guide

## Issue: Messages Not Being Received

### Problem

The Docker container is running, WhatsApp is connected, but the agent is not seeing messages from groups.

### Root Cause

The WAHA session was started **without webhook configuration**. WAHA needs to be explicitly configured to send webhooks to your Python application.

### Solution

#### 1. Verify Current Webhook Configuration

```bash
curl -s http://localhost:3000/api/sessions/default | jq '.config.webhooks'
```

If this returns `null`, your webhooks are NOT configured.

#### 2. Reconfigure WAHA Session with Webhooks

```bash
# Stop the current session
curl -X POST http://localhost:3000/api/sessions/default/stop

# Start session with webhook configuration
curl -X POST http://localhost:3000/api/sessions/start \
  -H "Content-Type: application/json" \
  -d '{
    "name": "default",
    "config": {
      "webhooks": [{
        "url": "http://host.docker.internal:8000/webhook",
        "events": ["message", "message.any"]
      }]
    }
  }'
```

#### 3. Verify Webhooks Are Configured

```bash
curl -s http://localhost:3000/api/sessions/default | jq '{name, status, webhooks: .config.webhooks}'
```

You should see:

```json
{
  "name": "default",
  "status": "WORKING",
  "webhooks": [
    {
      "url": "http://host.docker.internal:8000/webhook",
      "events": ["message", "message.any"]
    }
  ]
}
```

#### 4. Test the Bot

Send a message in a WhatsApp group starting with `gg`:

```
gg hello
```

The bot should respond with a formatted AI-generated message.

---

## Common Issues

### Issue: "Connection refused" errors

**Problem:** Python app is not running or not accessible from Docker.

**Solution:**

1. Make sure your Python app is running: `python main.py api`
2. Verify it's healthy: `curl http://localhost:8000/health`
3. Check that Docker can reach it via `host.docker.internal`

### Issue: Bot only responds to your own messages

**Problem:** The bot is configured to ignore messages from yourself.

**Solution:** Check the `fromMe` filter in `main.py` around line 418. You may need to adjust the logic.

### Issue: Bot doesn't respond to messages without "gg"

**Problem:** The bot is configured with a keyword trigger.

**Solution:** This is by design! Messages must start with `gg` to trigger the bot. See line 476 in `main.py`:

```python
if not message_text.lower().startswith("gg"):
    logger.info(f"🚫 Message doesn't start with 'gg', skipping")
    return
```

To change this behavior, modify or remove this check.

---

## Monitoring

### Check Application Logs

```bash
tail -f logs/app.log
```

Look for:

- `📨 Received webhook: message` - Webhooks are being received
- `✅ Processing message event` - Messages are being processed
- `🚫 Message doesn't start with 'gg'` - Message was filtered out
- `🎉 SUCCESS: Responded to 'gg' message` - Bot successfully responded

### Check WAHA Docker Logs

```bash
docker logs waha -f
```

### Check Docker Container Status

```bash
docker ps
```

Should show the `waha` container as `Up`.

---

## Environment Variables

Make sure your `.env` file has:

```ini
WAHA_BASE_URL=http://localhost:3000
WAHA_SESSION_NAME=default
WEBHOOK_URL=http://host.docker.internal:8000/webhook
OPENAI_API_KEY=your_openai_api_key
```

---

## API Endpoints

### Test Webhook Endpoint

```bash
curl http://localhost:8000/webhook
```

Should return:

```json
{ "status": "ok", "message": "Webhook endpoint is ready" }
```

### Check WAHA Session Status

```bash
curl http://localhost:3000/api/sessions/default
```

### Get WhatsApp Groups

```bash
curl "http://localhost:3000/api/groups?session=default"
```
