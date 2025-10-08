import os
import uvicorn
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from masumi.config import Config
from masumi.payment import Payment, Amount  
from crew_definition import AIEducationCrew
from logging_config import setup_logging
from waha_client import WAHAClient
from typing import Optional

# Configure logging
logger = setup_logging()

# Load environment variables
load_dotenv(override=True)

# Retrieve API Keys and URLs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL")
PAYMENT_API_KEY = os.getenv("PAYMENT_API_KEY")
NETWORK = os.getenv("NETWORK")

# WAHA Configuration
WAHA_BASE_URL = os.getenv("WAHA_BASE_URL", "http://localhost:3000")
WAHA_SESSION_NAME = os.getenv("WAHA_SESSION_NAME", "default")

logger.info("Starting application with configuration:")
logger.info(f"PAYMENT_SERVICE_URL: {PAYMENT_SERVICE_URL}")
logger.info(f"WAHA_BASE_URL: {WAHA_BASE_URL}")

# Initialize WAHA Client
waha_client: Optional[WAHAClient] = None
try:
    waha_client = WAHAClient()
    logger.info("WAHA client initialized successfully")
except Exception as e:
    logger.warning(f"WAHA client not initialized: {e}")
    logger.warning("WAHA webhooks will not be available")

# Initialize FastAPI
app = FastAPI(
    title="API following the Masumi API Standard",
    description="API for running Agentic Services tasks with Masumi payment integration",
    version="1.0.0"
)

# Track processed message IDs to prevent duplicates
processed_message_ids = set()

# ─────────────────────────────────────────────────────────────────────────────
# Temporary in-memory job store (DO NOT USE IN PRODUCTION)
# ─────────────────────────────────────────────────────────────────────────────
jobs = {}
payment_instances = {}

# ─────────────────────────────────────────────────────────────────────────────
# Initialize Masumi Payment Config
# ─────────────────────────────────────────────────────────────────────────────
config = Config(
    payment_service_url=PAYMENT_SERVICE_URL,
    payment_api_key=PAYMENT_API_KEY
)

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────
class StartJobRequest(BaseModel):
    identifier_from_purchaser: str
    input_data: dict[str, str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "identifier_from_purchaser": "example_purchaser_123",
                "input_data": {
                    "text": "Write a story about a robot learning to paint"
                }
            }
        }

class ProvideInputRequest(BaseModel):
    job_id: str

# ─────────────────────────────────────────────────────────────────────────────
# CrewAI Task Execution
# ─────────────────────────────────────────────────────────────────────────────
async def execute_crew_task(input_data: str) -> str:
    """ Execute a CrewAI task with Versatile AI Assistant Agents """
    logger.info(f"Starting AI assistant task with input: {input_data}")
    crew = AIEducationCrew(logger=logger)
    result = crew.crew.kickoff(inputs={"text": input_data})
    logger.info("AI assistant task completed successfully")
    return result

# ─────────────────────────────────────────────────────────────────────────────
# 1) Start Job (MIP-003: /start_job)
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/start_job")
async def start_job(data: StartJobRequest):
    """ Initiates a job and creates a payment request """
    print(f"Received data: {data}")
    print(f"Received data.input_data: {data.input_data}")
    try:
        job_id = str(uuid.uuid4())
        agent_identifier = os.getenv("AGENT_IDENTIFIER")
        
        # Log the input text (truncate if too long)
        input_text = data.input_data["text"]
        truncated_input = input_text[:100] + "..." if len(input_text) > 100 else input_text
        logger.info(f"Received job request with input: '{truncated_input}'")
        logger.info(f"Starting job {job_id} with agent {agent_identifier}")

        # Define payment amounts
        payment_amount = os.getenv("PAYMENT_AMOUNT", "10000000")  # Default 10 ADA
        payment_unit = os.getenv("PAYMENT_UNIT", "lovelace") # Default lovelace

        amounts = [Amount(amount=payment_amount, unit=payment_unit)]
        logger.info(f"Using payment amount: {payment_amount} {payment_unit}")
        
        # Create a payment request using Masumi
        payment = Payment(
            agent_identifier=agent_identifier,
            #amounts=amounts,
            config=config,
            identifier_from_purchaser=data.identifier_from_purchaser,
            input_data=data.input_data,
            network=NETWORK
        )
        
        logger.info("Creating payment request...")
        payment_request = await payment.create_payment_request()
        payment_id = payment_request["data"]["blockchainIdentifier"]
        payment.payment_ids.add(payment_id)
        logger.info(f"Created payment request with ID: {payment_id}")

        # Store job info (Awaiting payment)
        jobs[job_id] = {
            "status": "awaiting_payment",
            "payment_status": "pending",
            "payment_id": payment_id,
            "input_data": data.input_data,
            "result": None,
            "identifier_from_purchaser": data.identifier_from_purchaser
        }

        async def payment_callback(payment_id: str):
            await handle_payment_status(job_id, payment_id)

        # Start monitoring the payment status
        payment_instances[job_id] = payment
        logger.info(f"Starting payment status monitoring for job {job_id}")
        await payment.start_status_monitoring(payment_callback)

        # Return the response in the required format
        return {
            "status": "success",
            "job_id": job_id,
            "blockchainIdentifier": payment_request["data"]["blockchainIdentifier"],
            "submitResultTime": payment_request["data"]["submitResultTime"],
            "unlockTime": payment_request["data"]["unlockTime"],
            "externalDisputeUnlockTime": payment_request["data"]["externalDisputeUnlockTime"],
            "agentIdentifier": agent_identifier,
            "sellerVkey": os.getenv("SELLER_VKEY"),
            "identifierFromPurchaser": data.identifier_from_purchaser,
            "amounts": amounts,
            "input_hash": payment.input_hash,
            "payByTime": payment_request["data"]["payByTime"],
        }
    except KeyError as e:
        logger.error(f"Missing required field in request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Bad Request: If input_data or identifier_from_purchaser is missing, invalid, or does not adhere to the schema."
        )
    except Exception as e:
        logger.error(f"Error in start_job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Input_data or identifier_from_purchaser is missing, invalid, or does not adhere to the schema."
        )

# ─────────────────────────────────────────────────────────────────────────────
# 2) Process Payment and Execute AI Task
# ─────────────────────────────────────────────────────────────────────────────
async def handle_payment_status(job_id: str, payment_id: str) -> None:
    """ Executes CrewAI task after payment confirmation """
    try:
        logger.info(f"Payment {payment_id} completed for job {job_id}, executing task...")
        
        # Update job status to running
        jobs[job_id]["status"] = "running"
        logger.info(f"Input data: {jobs[job_id]["input_data"]}")

        # Execute the AI task
        result = await execute_crew_task(jobs[job_id]["input_data"])
        result_dict = result.json_dict
        logger.info(f"Crew task completed for job {job_id}")
        
        # Mark payment as completed on Masumi
        # Use a shorter string for the result hash
        await payment_instances[job_id].complete_payment(payment_id, result_dict)
        logger.info(f"Payment completed for job {job_id}")

        # Update job status
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["payment_status"] = "completed"
        jobs[job_id]["result"] = result

        # Stop monitoring payment status
        if job_id in payment_instances:
            payment_instances[job_id].stop_status_monitoring()
            del payment_instances[job_id]
    except Exception as e:
        logger.error(f"Error processing payment {payment_id} for job {job_id}: {str(e)}", exc_info=True)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        
        # Still stop monitoring to prevent repeated failures
        if job_id in payment_instances:
            payment_instances[job_id].stop_status_monitoring()
            del payment_instances[job_id]

# ─────────────────────────────────────────────────────────────────────────────
# 3) Check Job and Payment Status (MIP-003: /status)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/status")
async def get_status(job_id: str):
    """ Retrieves the current status of a specific job """
    logger.info(f"Checking status for job {job_id}")
    if job_id not in jobs:
        logger.warning(f"Job {job_id} not found")
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # Check latest payment status if payment instance exists
    if job_id in payment_instances:
        try:
            status = await payment_instances[job_id].check_payment_status()
            job["payment_status"] = status.get("data", {}).get("status")
            logger.info(f"Updated payment status for job {job_id}: {job['payment_status']}")
        except ValueError as e:
            logger.warning(f"Error checking payment status: {str(e)}")
            job["payment_status"] = "unknown"
        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}", exc_info=True)
            job["payment_status"] = "error"


    result_data = job.get("result")
    result = result_data.raw if result_data and hasattr(result_data, "raw") else None

    return {
        "job_id": job_id,
        "status": job["status"],
        "payment_status": job["payment_status"],
        "result": result
    }

# ─────────────────────────────────────────────────────────────────────────────
# 4) Check Server Availability (MIP-003: /availability)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/availability")
async def check_availability():
    """ Checks if the server is operational """

    return {"status": "available", "type": "masumi-agent", "message": "Server operational."}
    # Commented out for simplicity sake but its recommended to include the agentIdentifier
    #return {"status": "available","agentIdentifier": os.getenv("AGENT_IDENTIFIER"), "message": "The server is running smoothly."}

# ─────────────────────────────────────────────────────────────────────────────
# 5) Retrieve Input Schema (MIP-003: /input_schema)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/input_schema")
async def input_schema():
    """
    Returns the expected input schema for the /start_job endpoint.
    Fulfills MIP-003 /input_schema endpoint.
    """
    return {
        "input_data": [
            {
                "id": "text",
                "type": "string",
                "name": "Task Description",
                "data": {
                    "description": "The text input for the AI task",
                    "placeholder": "Enter your task description here"
                }
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 6) Health Check
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """
    Returns the health of the server.
    """
    return {
        "status": "healthy"
    }

# ─────────────────────────────────────────────────────────────────────────────
# 7) WAHA Webhook Verification (GET)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/webhook")
async def verify_webhook():
    """
    Webhook verification endpoint for WAHA.
    This endpoint is called by WAHA to verify the webhook URL.
    """
    logger.info("WAHA webhook verification requested")
    return {"status": "ok", "message": "Webhook endpoint is ready"}

# ─────────────────────────────────────────────────────────────────────────────
# 8) WAHA Webhook Handler (POST)
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Receives incoming WhatsApp messages from WAHA and triggers the AI agent.
    Handles both individual and group chat messages.
    """
    try:
        body = await request.json()
        
        # Log incoming webhook
        logger.info(f"📨 Received webhook: {body.get('event', 'unknown')}")
        
        # Debug: Log the event type
        event_type = body.get("event")
        logger.info(f"🔍 Event type: {event_type}")
        
        # WAHA sends message.any events (not just "message")
        if event_type in ["message", "message.any"]:
            logger.info("✅ Processing message event")
            await process_waha_message(body)
        else:
            logger.info(f"❌ Received non-message event: {event_type}")
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Error processing WAHA webhook: {str(e)}", exc_info=True)
        # Still return 200 to prevent WAHA from retrying
        return {"status": "error", "message": str(e)}

# ─────────────────────────────────────────────────────────────────────────────
# Group ID Mapping
# ─────────────────────────────────────────────────────────────────────────────
def map_waha_internal_id_to_group_id(internal_id: str, webhook_data: dict) -> str:
    """Map WAHA internal chat ID to real WhatsApp group ID."""
    # Known group mappings
    known_groups = {
        "nerds": "120363422170611614@g.us",
        "BTC-svip-76": "120363038777117231@g.us",
        "Golfing ⛳": "13065365236-1631906035@g.us",
        "Uber": "17059848341-1629060796@g.us",
        "Apple Tree-ers": "17059848341-1626995520@g.us"
    }
    
    # Try to find group name in webhook data
    webhook_str = str(webhook_data).lower()
    for group_name, group_id in known_groups.items():
        if group_name.lower() in webhook_str:
            logger.info(f"Mapped '{group_name}' to {group_id}")
            return group_id
    
    # Try to find group ID directly in webhook data
    import re
    group_matches = re.findall(r'(\d+@g\.us)', str(webhook_data))
    if group_matches:
        return group_matches[0]
    
    # Fallback: return original ID
    logger.warning(f"Could not map WAHA internal ID {internal_id} to real group ID")
    return internal_id

# ─────────────────────────────────────────────────────────────────────────────
# WAHA Message Processing Logic
# ─────────────────────────────────────────────────────────────────────────────
async def process_waha_message(webhook_data: dict):
    """
    Process an incoming WAHA message and respond with AI agent output.
    
    Args:
        webhook_data: The webhook data from WAHA
    """
    if not waha_client:
        logger.error("WAHA client not initialized, cannot process message")
        return
    
    try:
        message_data = webhook_data.get("payload", {})
        message_id = message_data.get("id")
        
        # Skip if we've already processed this message
        if message_id in processed_message_ids:
            logger.info(f"Skipping duplicate message: {message_id}")
            return
        
        processed_message_ids.add(message_id)
        
        # Keep memory usage reasonable (clear old IDs after 1000 messages)
        if len(processed_message_ids) > 1000:
            processed_message_ids.clear()
            logger.info("Cleared old message IDs from memory")
        
        from_number = message_data.get("from")
        message_type = message_data.get("type", "chat")  # Default to "chat" if not specified
        from_me = message_data.get("fromMe", False)
        
        # 🎯 FIX: Determine correct chat ID for group messages
        # For group messages:
        #   - When YOU send: "from" = your number, "to" = group ID
        #   - When OTHERS send: "from" = group ID, "to" = your number
        # So we need to check which field contains @g.us
        to_field = message_data.get("to")
        from_field = message_data.get("from")
        
        if from_field and "@g.us" in from_field:
            # Message FROM a group (someone else sent it)
            chat_id = from_field
            logger.info(f"📍 Group message FROM others: {chat_id}")
        elif to_field and "@g.us" in to_field:
            # Message TO a group (you sent it)
            chat_id = to_field
            logger.info(f"📍 Group message FROM you: {chat_id}")
        else:
            # Direct message
            chat_id = to_field
            logger.info(f"📍 Direct message: {chat_id}")
        
        # Extract sender name
        sender_name = message_data.get("sender", {}).get("name", "User")
        
        # Check if this is a group message
        is_group = chat_id and "@g.us" in chat_id
        
        logger.info(f"Processing message from {sender_name}, type: {message_type}, group: {is_group}")
        logger.info(f"🔍 DEBUG: fromMe={from_me}, chat_id={chat_id}, message_body='{message_data.get('body', '')[:50]}...'")
        
        # Map WAHA internal IDs to real group IDs
        if chat_id and not chat_id.endswith(('@c.us', '@g.us')):
            logger.info(f"Mapping WAHA internal ID to real group ID")
            chat_id = map_waha_internal_id_to_group_id(chat_id, webhook_data)
        
        logger.info(f"✅ Final chat ID for response: {chat_id}")
        
        # Mark message as read (reactions disabled - WAHA doesn't support this endpoint)
        try:
            await waha_client.mark_as_read(message_id, chat_id)
        except Exception as e:
            logger.warning(f"Could not mark as read: {e}")
        
        # Only process text messages
        if message_type not in ["text", "chat"]:
            logger.info(f"🚫 Skipping non-text message type: {message_type}")
            return
        
        logger.info(f"✅ Message type OK: {message_type}")
        
        # Extract message text
        message_text = message_data.get("body", "")
        if not message_text.strip():
            logger.info("🚫 Empty message, skipping")
            return
        
        logger.info(f"📝 Message text: '{message_text}'")
        
        # 🎯 KEYWORD TRIGGER: Only respond to messages starting with "gg"
        if not message_text.lower().startswith("gg"):
            logger.info(f"🚫 Message doesn't start with 'gg', skipping: '{message_text[:30]}...'")
            return
        
        logger.info(f"✅ Message starts with 'gg' - PROCESSING!")
        
        # Remove the "gg" prefix for processing
        clean_message = message_text[2:].strip()
        if not clean_message:
            logger.info("No message after 'gg', skipping")
            return
        
        logger.info(f"Processing triggered message: {clean_message[:100]}...")
        
        # Execute the versatile AI assistant
        logger.info("Executing AI assistant...")
        import asyncio
        await asyncio.sleep(1)  # Prevent rapid-fire responses
        
        result = await execute_crew_task(clean_message)
        response_text = result.raw if hasattr(result, "raw") else str(result)
        
        # 📏 SHORT RESPONSES: Limit response length and add italics
        max_response_length = 200  # Keep responses under 200 characters
        if len(response_text) > max_response_length:
            response_text = response_text[:max_response_length].rsplit(' ', 1)[0] + "..."
            logger.info(f"Truncated response to {len(response_text)} characters")
        
        # 🎨 FORMAT: Add emoji and italics to make it clear it's the AI agent
        # Always add just the robot emoji and italics (remove any existing emojis from AI response)
        import re
        # Remove any emojis from the start of the response
        clean_response = re.sub(r'^[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF\U0001F018-\U0001F0FF\U0001F200-\U0001F2FF\s]*', '', response_text.strip())
        formatted_response = f"🤖 _{clean_response}_"
        
        logger.info(f"Formatted response: {formatted_response[:50]}...")
        
        # Success reaction disabled - WAHA doesn't support this endpoint
        
        # Send the AI response back to WhatsApp
        try:
            logger.info(f"📤 Attempting to send response to chat_id: {chat_id}")
            logger.info(f"📤 Message content: {formatted_response[:100]}...")
            logger.info(f"📤 Reply to message_id: {message_id}")
            
            await waha_client.send_text_message(
                to=chat_id,
                message=formatted_response,
                reply_to_message_id=message_id
            )
            logger.info("✅ Response sent successfully!")
        except Exception as send_error:
            logger.error(f"❌ Failed to send response: {str(send_error)}")
            logger.error(f"❌ Chat ID was: {chat_id}")
            logger.error(f"❌ Message was: {formatted_response[:100]}...")
            raise
        
        logger.info(f"🎉 SUCCESS: Responded to 'gg' message from {sender_name} in group!")
    
    except Exception as e:
        logger.error(f"Error processing WAHA message: {str(e)}", exc_info=True)
        # Try to send an error message to the user
        try:
            message_data = webhook_data.get("payload", {})
            message_id = message_data.get("id")
            
            # Extract chat_id the same way as in main processing
            to_field = message_data.get("to")
            from_field = message_data.get("from")
            
            if from_field and "@g.us" in from_field:
                chat_id = from_field
            elif to_field and "@g.us" in to_field:
                chat_id = to_field
            else:
                chat_id = to_field
            
            if chat_id:
                await waha_client.send_text_message(
                    to=chat_id,
                    message="❌ Sorry, I encountered an error processing your message. Please try again later.",
                    reply_to_message_id=message_id
                )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {str(send_error)}")

# ─────────────────────────────────────────────────────────────────────────────
# WAHA Management Endpoints
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/waha/start-session")
async def start_waha_session():
    """Start a new WAHA session"""
    if not waha_client:
        raise HTTPException(status_code=500, detail="WAHA client not initialized")
    
    try:
        result = await waha_client.start_session()
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error starting WAHA session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/waha/session-status")
async def get_waha_session_status():
    """Get WAHA session status"""
    if not waha_client:
        raise HTTPException(status_code=500, detail="WAHA client not initialized")
    
    try:
        status = await waha_client.get_session_status()
        return {"status": "success", "data": status}
    except Exception as e:
        logger.error(f"Error getting WAHA session status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/waha/qr-code")
async def get_waha_qr_code():
    """Get QR code for WhatsApp authentication"""
    if not waha_client:
        raise HTTPException(status_code=500, detail="WAHA client not initialized")
    
    try:
        qr_code = await waha_client.get_qr_code()
        return {"status": "success", "qr_code": qr_code}
    except Exception as e:
        logger.error(f"Error getting QR code: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/waha/groups")
async def get_waha_groups():
    """Get list of WhatsApp groups"""
    if not waha_client:
        raise HTTPException(status_code=500, detail="WAHA client not initialized")
    
    try:
        groups = await waha_client.get_groups()
        return {"status": "success", "groups": groups}
    except Exception as e:
        logger.error(f"Error getting groups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/waha/join-group")
async def join_waha_group(group_invite: str):
    """Join a WhatsApp group using invite link"""
    if not waha_client:
        raise HTTPException(status_code=500, detail="WAHA client not initialized")
    
    try:
        result = await waha_client.join_group(group_invite)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error joining group: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/waha/send-message")
async def send_waha_message(chat_id: str, message: str, reply_to: str = None):
    """Send a message to a WhatsApp chat (individual or group)"""
    if not waha_client:
        raise HTTPException(status_code=500, detail="WAHA client not initialized")
    
    try:
        result = await waha_client.send_text_message(
            to=chat_id,
            message=message,
            reply_to_message_id=reply_to
        )
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────────────────────────────────
# Main Logic if Called as a Script
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("Running CrewAI as standalone script is not supported when using payments.")
    print("Start the API using `python main.py api` instead.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        print("Starting FastAPI server with Masumi integration...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        main()
