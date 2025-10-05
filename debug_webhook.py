#!/usr/bin/env python3
"""
Debug webhook data to see what's being received
"""

import requests
import json
from datetime import datetime

def debug_webhook_data():
    """Debug what webhook data we're receiving"""
    
    print("🔍 Debugging Webhook Data")
    print("=" * 50)
    print("📱 Send a message in the 'nerds' group and check the logs below")
    print("⏰ I'll monitor for 30 seconds...")
    print("🛑 Press Ctrl+C to stop")
    
    # This will help us see what data is coming in
    print("\n📋 Expected webhook structure:")
    print(json.dumps({
        "event": "message.any",
        "payload": {
            "id": "message_id",
            "body": "gg your message here",
            "from": "sender_phone@c.us",
            "to": "120363422170611614@g.us",
            "type": "chat",
            "sender": {"name": "Sender Name"},
            "fromMe": False  # This should be False for others' messages
        }
    }, indent=2))
    
    print("\n🎯 What to look for:")
    print("- fromMe: false (for others' messages)")
    print("- fromMe: true (for your messages)")
    print("- body: should contain the message text")
    print("- to: should be the group ID")

if __name__ == "__main__":
    debug_webhook_data()
