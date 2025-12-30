"""
history.py
----------
Handles loading and saving of email processing history.
This ensures we don't notify the user about the same email twice.
"""

import os
import json
from config import HISTORY_DIR

def load_history(chat_id, email=None):
    """
    Loads the list of processed email IDs for a specific user account.
    If email is provided, uses histories/{chat_id}/{email}.json.
    Otherwise uses histories/{chat_id}.json.
    Returns an empty list if no history exists.
    """
    if email:
        path = os.path.join(HISTORY_DIR, str(chat_id), f"{email}.json")
    else:
        path = os.path.join(HISTORY_DIR, f"{chat_id}.json")

    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else list(data)
        except:
            return []
    return []

def save_history(chat_id, history, email=None):
    """
    Saves the list of processed email IDs.
    """
    if email:
        target_dir = os.path.join(HISTORY_DIR, str(chat_id))
        os.makedirs(target_dir, exist_ok=True)
        path = os.path.join(target_dir, f"{email}.json")
    else:
        path = os.path.join(HISTORY_DIR, f"{chat_id}.json")

    with open(path, 'w') as f:
        json.dump(history, f)
