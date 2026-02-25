import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"

class OllamaError(Exception):
    pass


def generate_text(prompt: str, model: str = "mistral") -> str:
    """Call local Ollama HTTP API and return the generated text.

    Falls back with descriptive error if Ollama not reachable or API returns unexpected structure.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens": 512,
        "temperature": 0.2
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=15)
    except requests.RequestException as e:
        raise OllamaError(f"Could not contact Ollama at {OLLAMA_URL}: {e}")

    if resp.status_code != 200:
        raise OllamaError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")

    data = resp.json()

    # Ollama returns a structured result. Try to extract textual output.
    if isinstance(data, dict):
        # Newer Ollama responses include a 'result' array with content items
        result = data.get('result') or data.get('output')
        if result:
            # result may be list of messages; find text pieces
            texts = []
            if isinstance(result, list):
                for item in result:
                    # item may contain 'content' array
                    content = item.get('content') if isinstance(item, dict) else None
                    if content and isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get('type') == 'output_text':
                                texts.append(c.get('text', ''))
                    # older formats might have 'text' directly
                    if isinstance(item, dict) and item.get('text'):
                        texts.append(item.get('text'))
            elif isinstance(result, str):
                texts.append(result)

            final = '\n'.join(t for t in texts if t)
            return final

        # As fallback, try 'text' or 'output'
        if 'text' in data:
            return str(data['text'])
        if 'output' in data:
            return str(data['output'])

    # If we got here, return raw body
    return resp.text
