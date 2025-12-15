import ollama

def ollama_integration(body, subject, sender):
    response = ollama.chat(model='smollm2:135m', messages=[
        {'role': 'user', 'content': f"task: summarize the email\n subject: {subject}\n sender: {sender}\n body: {body}"}
    ])
    return response['message']['content']