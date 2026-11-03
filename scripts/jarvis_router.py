#!/usr/bin/env python3
"""
Jarvis Model Router
Routes prompts to local Ollama (0 token cost) for routine tasks,
or to Cloud APIs for high-precision reasoning.
"""

import json
import os
import sys
import urllib.request
import urllib.error

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "jarvis_config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

def check_ollama_health(base_url="http://localhost:11434"):
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", headers={"User-Agent": "JarvisRouter/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                models = [m.get('name') for m in data.get('models', [])]
                return True, models
    except Exception as e:
        return False, []
    return False, []

def query_local_ollama(prompt, system_prompt="You are Jarvis, a helpful AI startup assistant.", model="qwen2.5-coder:7b", base_url="http://localhost:11434"):
    url = f"{base_url}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            res_data = json.loads(resp.read().decode('utf-8'))
            return res_data['choices'][0]['message']['content']
    except urllib.error.URLError as e:
        return f"Error connecting to Ollama: {e}"

if __name__ == "__main__":
    config = load_config()
    ollama_url = config.get("endpoints", {}).get("local_ollama", {}).get("base_url", "http://localhost:11434/v1").replace("/v1", "")
    healthy, models = check_ollama_health(ollama_url)
    
    print(f"🤖 Jarvis Router initialized.")
    if healthy:
        print(f"✅ Local Ollama is RUNNING at {ollama_url}")
        print(f"📦 Installed local models: {models if models else 'None (downloading...)'}")
    else:
        print(f"⚠️ Local Ollama is NOT running yet on {ollama_url}")
