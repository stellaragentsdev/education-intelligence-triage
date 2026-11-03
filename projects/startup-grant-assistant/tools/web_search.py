#!/usr/bin/env python3
"""Local Web Search & URL Fetcher Tool."""
import sys
import json
import urllib.request
import urllib.parse
import re

def search(query):
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8', errors='ignore')
            results = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html)
            clean = [re.sub(r'<[^>]+>', '', r).strip() for r in results[:3]]
            return clean if clean else ["No snippet results found."]
    except Exception as e:
        return [f"Search error: {str(e)}"]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    else:
        q = "AWS startup grant requirements 2026"
    res = search(q)
    print(json.dumps({"query": q, "results": res}, indent=2))
