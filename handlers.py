"""
handlers.py
-----------
Contains Telegram Bot command handlers:
- /start: Welcome message
- /grant: Allow Admin to generate OAuth links
- Message Handler: Handles email input (requests) and auth code verification.
"""

import os
import re
import json
import time
from telegram import Update
from telegram.ext import ContextTypes
from google_auth_oauthlib.flow import InstalledAppFlow

from config import ADMIN_CHAT_ID, SCOPES, USERS_DIR

# Temporary storage for OAuth flows: {chat_id: flow_object}
pending_flows = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /start command.
    """
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Welcome! To start using the Gmail Bot, please reply with your email address."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles generic text messages.
    1. Looks for Email Address -> Triggers access request to Admin.
    2. Looks for Auth Code (/code ...) -> Completes authentication.
    """
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    
    # CASE 1: Check for email address (Requesting Access)
    if re.match(r"[^@]+@[^@]+\.[^@]+", text):
        # Notify Admin
        admin_msg = f"New access request:\nEmail: {text}\nChat ID: {chat_id}\n\nTo approve, send:\n`/grant {chat_id}`"
        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode='Markdown')
            await update.message.reply_text("Request sent to developer. Please wait for approval.")
        except Exception as e:
            await update.message.reply_text(f"Error contacting admin: {e}")
        return

    # CASE 2: Check for Auth Code (Finishing Access)
    if chat_id in pending_flows:
        # Allow user to send just the code or "/code <code>"
        if text.startswith("/code"):
             code = text.replace("/code", "").strip()
        else:
             code = text
             
        try:
            flow = pending_flows.pop(chat_id)
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            # Save credentials to users/ directory
            with open(os.path.join(USERS_DIR, f"{chat_id}.json"), 'w') as f:
                f.write(creds.to_json())
            
            # Save startup timestamp to ignore old emails
            with open(os.path.join(USERS_DIR, f"{chat_id}_meta.json"), 'w') as f:
                 json.dump({"start_time": int(time.time())}, f)

            await update.message.reply_text("Setup complete! You will now receive email notifications.")
        except Exception as e:
            await update.message.reply_text(f"Authentication failed: {e}. Please ask admin for a new link.")
        return

    await update.message.reply_text("I didn't understand that. Send your email to request access.")

import asyncio
import requests
from google.oauth2.credentials import Credentials

# ... (imports remain)

async def grant_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /grant <chat_id>.
    Initiates Google Device Flow (TV style).
    """
    # Security Check
    if str(update.effective_chat.id) != str(ADMIN_CHAT_ID):
        return
        
    try:
        target_chat_id = context.args[0]
    except IndexError:
        await update.message.reply_text("Usage: /grant <chat_id>")
        return
        
    # Load Client ID from credentials.json
    if not os.path.exists('credentials.json'):
        await update.message.reply_text("Error: credentials.json missing.")
        return
        
    try:
        with open('credentials.json', 'r') as f:
            data = json.load(f)
            # Support both "installed" and "web" keys, or "client_id" directly
            cs = data.get('installed') or data.get('web') or data
            client_id = cs.get('client_id')
            client_secret = cs.get('client_secret')
            
        if not client_id:
            await update.message.reply_text("Error: client_id not found in credentials.json")
            return

        # 1. Request Device Code
        resp = requests.post('https://oauth2.googleapis.com/device/code', data={
            'client_id': client_id,
            'scope': ' '.join(SCOPES)
        })
        
        if resp.status_code != 200:
            await update.message.reply_text(f"Failed to init device flow: {resp.text}")
            return
            
        device_data = resp.json()
        device_code = device_data['device_code']
        user_code = device_data['user_code']
        verification_url = device_data['verification_url']
        interval = device_data.get('interval', 5)
        
        # 2. Show Code to User
        msg = (
            f"🔑 **Authorization Required**\n\n"
            f"1. Go to: [google.com/device]({verification_url})\n"
            f"2. Enter Code: `{user_code}`\n\n"
            f"I will check for approval automatically..."
        )
        
        await context.bot.send_message(chat_id=target_chat_id, text=msg, parse_mode='Markdown')
        await update.message.reply_text(f"Code sent to {target_chat_id}. Polling for completion...")
        
        # 3. Poll for Token (Background Task)
        asyncio.create_task(poll_for_token(context, target_chat_id, client_id, client_secret, device_code, interval))
        
    except Exception as e:
        await update.message.reply_text(f"Error starting flow: {e}")

async def poll_for_token(context, chat_id, client_id, client_secret, device_code, interval):
    """
    Polls Google's token endpoint until user authorizes or code expires.
    """
    token_url = "https://oauth2.googleapis.com/token"
    
    # Poll for up to 10 minutes (600s)
    for _ in range(0, 600, interval):
        await asyncio.sleep(interval)
        
        resp = requests.post(token_url, data={
            'client_id': client_id,
            'client_secret': client_secret,
            'device_code': device_code,
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
        })
        
        data = resp.json()
        
        if resp.status_code == 200:
            # Success!
            creds = Credentials(
                token=data['access_token'],
                refresh_token=data.get('refresh_token'),
                token_uri=token_url,
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES
            )
            
            # Save Credentials
            with open(os.path.join(USERS_DIR, f"{chat_id}.json"), 'w') as f:
                f.write(creds.to_json())
            
            # Save timestamp
            with open(os.path.join(USERS_DIR, f"{chat_id}_meta.json"), 'w') as f:
                 json.dump({"start_time": int(time.time())}, f)
                 
            await context.bot.send_message(chat_id=chat_id, text="✅ **Setup Complete!**\nYou will now receive email notifications.")
            return
            
        if data.get('error') == 'authorization_pending':
            continue # specific error returned while waiting
        
        if data.get('error') == 'slow_down':
            interval += 2 # Back off
            continue
            
        # Any other error is fatal (expired, denied)
        await context.bot.send_message(chat_id=chat_id, text=f"Authorization failed or expired: {data.get('error')}")
        return
