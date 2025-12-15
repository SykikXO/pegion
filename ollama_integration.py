"""
ollama_integration.py
---------------------
Integrates with local Ollama instance to summarize emails.
"""
import ollama
import logging
import asyncio
from functools import partial

def _sync_summarize(body, subject, sender):
    """
    Synchronous call to Ollama. Called via executor to avoid blocking.
    """
    try:
        response = ollama.chat(model='sum', messages=[
            {'role': 'user', 'content': f"sender: {sender}\nsubject: {subject}\nbody: {body}"}
        ])
        return response['message']['content']
    except Exception as e:
        logging.error(f"Ollama summarization failed: {e}")
        # Fallback to raw email if Ollama fails
        return f"📧 *New Email*\n*From:* {sender}\n*Subject:* {subject}\n\n{body[:500]}..."

async def ollama_summarize(body, subject, sender):
    """
    Async wrapper for Ollama summarization.
    Runs the blocking ollama call in a thread pool to avoid freezing the bot.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,  # Default executor
        partial(_sync_summarize, body, subject, sender)
    )