#!/usr/bin/env python3
"""
Save all WAHA chats to JSON file for easy viewing
"""

import requests
import json
from datetime import datetime

WAHA_BASE_URL = "http://localhost:3000"
SESSION_NAME = "default"

def save_chats_to_json():
    """Get all chats and save to JSON file"""
    
    print("🔍 Getting All Chats from WAHA")
    print("=" * 50)
    
    # Get all chats
    url = f"{WAHA_BASE_URL}/api/{SESSION_NAME}/chats"
    
    try:
        response = requests.get(url)
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            chats = response.json()
            print(f"✅ SUCCESS! Found {len(chats)} chats")
            
            # Create timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"waha_chats_{timestamp}.json"
            
            # Save to JSON file
            with open(filename, 'w') as f:
                json.dump(chats, f, indent=2)
            
            print(f"💾 Saved all chats to: {filename}")
            
            # Also create a simplified summary
            summary_filename = f"waha_chats_summary_{timestamp}.json"
            summary = []
            
            for chat in chats:
                chat_info = {
                    "name": chat.get("name", "Unknown"),
                    "id": chat.get("id", {}).get("_serialized", "Unknown"),
                    "isGroup": chat.get("isGroup", False),
                    "unreadCount": chat.get("unreadCount", 0),
                    "archived": chat.get("archived", False),
                    "pinned": chat.get("pinned", False)
                }
                
                # Add group-specific info
                if chat_info["isGroup"] and "groupMetadata" in chat:
                    group_meta = chat["groupMetadata"]
                    chat_info["groupInfo"] = {
                        "subject": group_meta.get("subject", ""),
                        "participants": len(group_meta.get("participants", [])),
                        "isAdmin": any(p.get("id", {}).get("_serialized") == "13065505040@c.us" and p.get("isAdmin", False) 
                                     for p in group_meta.get("participants", []))
                    }
                
                summary.append(chat_info)
            
            # Save summary
            with open(summary_filename, 'w') as f:
                json.dump(summary, f, indent=2)
            
            print(f"📋 Saved summary to: {summary_filename}")
            
            # Print groups found
            groups = [chat for chat in summary if chat["isGroup"]]
            print(f"\n👥 GROUPS FOUND ({len(groups)}):")
            print("=" * 40)
            
            for group in groups:
                print(f"📱 {group['name']}")
                print(f"   ID: {group['id']}")
                print(f"   Unread: {group['unreadCount']}")
                print(f"   Archived: {group['archived']}")
                if "groupInfo" in group:
                    print(f"   Participants: {group['groupInfo']['participants']}")
                    print(f"   You're Admin: {group['groupInfo']['isAdmin']}")
                print()
            
            return groups
            
        else:
            print(f"❌ Failed: {response.text}")
            return []
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return []

def test_group_message(groups):
    """Test sending message to each group"""
    
    if not groups:
        print("❌ No groups to test with")
        return
    
    print(f"\n🚀 Testing Group Messages")
    print("=" * 50)
    
    for group in groups:
        group_id = group['id']
        group_name = group['name']
        
        print(f"\n📱 Testing: {group_name}")
        print(f"🆔 ID: {group_id}")
        
        url = f"{WAHA_BASE_URL}/api/sendText"
        data = {
            "session": SESSION_NAME,
            "chatId": group_id,
            "text": f"🤖 Hello {group_name}! This is a test message from your bot!"
        }
        
        try:
            response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 201:
                print(f"   ✅ SUCCESS!")
            else:
                print(f"   ❌ Failed: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   💥 Error: {e}")

if __name__ == "__main__":
    groups = save_chats_to_json()
    
    if groups:
        print(f"\n🎉 Found {len(groups)} groups!")
        print(f"\n💡 You can now:")
        print(f"   1. Open the JSON files to see all chat data")
        print(f"   2. Use any group ID to send messages")
        print(f"   3. Update your bot to use the real group IDs")
        
        # Ask if user wants to test
        test = input(f"\n🚀 Test sending messages to all groups? (y/n): ")
        if test.lower() == 'y':
            test_group_message(groups)
    else:
        print(f"\n❌ No groups found")
