#!/usr/bin/env python3
from jarvis_router import query_local_ollama

prompt = "Draft a 2-sentence elevator pitch for an AI platform called Stellar that helps solo founders scale their startups using autonomous agents."
print("🚀 Sending prompt to local Qwen 2.5 Coder (0 token cost)...")
response = query_local_ollama(prompt, model="qwen2.5-coder:1.5b")
print("\n--- Local Model Response ---")
print(response)
print("----------------------------")
