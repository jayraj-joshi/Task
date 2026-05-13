import os
import json
import requests

from chunksmith.llm_support.prompts import build_node_selection_prompt

def load_env():
    with open(".env", "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

def llm_call(model: str, prompt: str, token: str) -> str:
    url = "https://router.huggingface.co/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "model": model,
        "max_tokens": 128,
        "stream": False
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error {response.status_code}: {response.text}"

def main():
    load_env()
    token = os.getenv("HF_TOKEN")
    
    with open("First10_output.toon", "r") as f:
        tree_toon = f.read()

    query = "How have the risks to achieving the Committee's employment and inflation goals changed according to the March 2024 Summary?"
    
    prompt = build_node_selection_prompt(tree_toon, query)
    
    models = [
        "Qwen/Qwen2.5-7B-Instruct:together",
        "microsoft/Phi-4-mini-instruct:featherless-ai"
    ]
    
    print(f"Task: Select relevant nodes for query: '{query}'")
    print(f"Expected ID: 0002 (March 2024 Summary)\n")
    
    for model in models:
        print(f"Calling {model}...")
        result = llm_call(model, prompt, token)
        print(f"RESULT: {result}")
        print("-" * 30)

if __name__ == "__main__":
    main()
