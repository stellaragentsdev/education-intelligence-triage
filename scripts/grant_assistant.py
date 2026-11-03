#!/usr/bin/env python3
"""
Startup Grant & Application Assistant
Generates polished, high-converting grant and application answers using startup profile data.
"""

import json
import os
import sys
from jarvis_router import query_local_ollama

PROFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "startup_profile.json")

def load_profile():
    if os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH, "r") as f:
            return json.load(f)
    return {}

def generate_answer(question, word_limit=None, model="qwen2.5-coder:1.5b"):
    profile = load_profile()
    
    system_prompt = f"""You are the Startup Grant & Application Assistant for {profile.get('startup_name', 'Stellar')}.
Your role is to write clear, persuasive, concise, founder-centric answers for startup grants, accelerators (like Y C, Techstars), and Cloud Startup Credit applications.

Startup Context:
- One liner: {profile.get('one_liner')}
- Problem: {profile.get('problem')}
- Solution: {profile.get('solution')}
- Target Market: {profile.get('target_market')}
- Tech Stack: {json.dumps(profile.get('tech_stack'))}
- Active Credits: {json.dumps(profile.get('credits_available'))}

Rules:
1. Keep tone direct, ambitious, and grounded in technical facts.
2. Strictly respect word/character limits if specified.
3. Highlight how AI automation enables a solo founder to scale rapidly.
"""
    
    user_prompt = f"Question: {question}"
    if word_limit:
        user_prompt += f"\nNote: Keep response strictly under {word_limit} words."
        
    return query_local_ollama(user_prompt, system_prompt=system_prompt, model=model)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "Describe what your company does, the problem you are solving, and why your team is uniquely qualified."
        
    print(f"📝 Grant Assistant generating answer for question:\n'{question}'\n")
    response = generate_answer(question)
    print("--- Draft Answer ---")
    print(response)
    print("--------------------")
