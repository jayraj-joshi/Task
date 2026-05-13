import os
import json
import requests
from typing import List

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
        "max_tokens": 1024,
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
    
    context = """
March 2024 Summary
While inflation remains above the Federal Open Market Committee’s (FOMC) objective of 2 percent, it has eased substantially over the past year, and the slowing in inflation has occurred without a significant increase in unemployment. The labor market remains relatively tight, with the unemployment rate near historically low levels and job vacancies still elevated. Real gross domestic product (GDP) growth has also been strong, supported by solid increases in consumer spending.
The FOMC has maintained the target range for the federal funds rate at 5-1/4 to 5-1/2 percent since its July 2023 meeting. The Committee views the policy rate as likely at its peak for this tightening cycle, which began in early 2022. The Federal Reserve has also continued to reduce its holdings of Treasury and agency mortgage-backed securities.
As labor market tightness has eased and progress on inflation has continued, the risks to achieving the Committee’s employment and inflation goals have been moving into better balance. Even so, the Committee remains highly attentive to inflation risks and is acutely aware that high inflation imposes significant hardship, especially on those least able to meet the higher costs of essentials.
The FOMC is strongly committed to returning inflation to its 2 percent objective. In considering any adjustments to the target range for the federal funds rate, the Committee will carefully assess incoming data, the evolving outlook, and the balance of risks. The Committee does not expect it will be appropriate to reduce the target range until it has gained greater confidence that inflation is moving sustainably toward 2 percent.
"""
    query = "How have the risks to achieving the Committee's employment and inflation goals changed according to the March 2024 Summary?"
    
    prompt = f"""
You are an expert document assistant. Use the provided context from the document to answer the user's query.

CONTEXT:
{context}

USER QUERY: {query}

Instructions:
- Answer the query accurately based ONLY on the provided context.
- If the context doesn't contain the answer, explicitly state that the information is not available in the selected sections.
- Use a professional and helpful tone.
- If relevant, mention which parts of the context you are using.
"""
    
    models = [
        "Qwen/Qwen2.5-7B-Instruct:together",
        "microsoft/Phi-4-mini-instruct:featherless-ai"
    ]
    
    results = {}
    for model in models:
        print(f"Calling {model}...")
        results[model] = llm_call(model, prompt, token)
    
    print("\n" + "="*50)
    for model, result in results.items():
        print(f"MODEL: {model}")
        print("-" * 20)
        print(result)
        print("=" * 50)

if __name__ == "__main__":
    main()
