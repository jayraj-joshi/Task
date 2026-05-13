"""OpenAI chat client, token counting, and JSON extraction from assistant text."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, List, Optional, Tuple

import openai
import tiktoken

from chunksmith.config import RuntimeSettings

logger = logging.getLogger(__name__)


def _tiktoken_encoding_for(model: str | None) -> tiktoken.Encoding:
    try:
        return tiktoken.encoding_for_model(model or "gpt-4o")
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str | None, model: str | None = None) -> int:
    if not text:
        return 0
    enc = _tiktoken_encoding_for(model)
    return len(enc.encode(text))


def get_openai_client(settings: RuntimeSettings):
    if settings.hf_token:
        return openai.OpenAI(
            api_key=settings.hf_token,
            base_url="https://router.huggingface.co/v1",
        )
    if settings.azure_openai_endpoint:
        from openai import AzureOpenAI

        return AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version ,
            azure_deployment=settings.azure_openai_chat_model or settings.pageindex_model,
        )
    key = settings.openai_api_key
    if not key:
        raise ValueError("No API key: set HF_TOKEN, OPENAI_API_KEY, CHATGPT_API_KEY, or Azure variables.")
    return openai.OpenAI(api_key=key)


def ChatGPT_API_with_finish_reason(
    settings: RuntimeSettings,
    model: str,
    prompt: str,
    chat_history: Optional[List[dict]] = None,
    max_tokens: int = 4096,
) -> Tuple[str, str]:
    max_retries = 10
    client = get_openai_client(settings)
    for i in range(max_retries):
        try:
            if chat_history:
                messages = list(chat_history)
                messages.append({"role": "user", "content": prompt})
            else:
                messages = [{"role": "user", "content": prompt}]

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
                max_tokens=max_tokens,
            )
            choice = response.choices[0]
            if choice.finish_reason == "length":
                return choice.message.content or "", "max_output_reached"
            return choice.message.content or "", "finished"
        except Exception as e:
            logger.warning("Chat completion retry %s: %s", i + 1, e)
            if i < max_retries - 1:
                time.sleep(1)
            else:
                logger.error("Max retries reached for chat completion")
                return "Error", "error"
    return "Error", "error"


def ChatGPT_API(
    settings: RuntimeSettings,
    model: str,
    prompt: str,
    chat_history: Optional[List[dict]] = None,
    max_tokens: int = 4096,
) -> str:
    text, _ = ChatGPT_API_with_finish_reason(settings, model, prompt, chat_history, max_tokens=max_tokens)
    return text


def extract_json(content: str) -> Any:
    try:
        start_idx = content.find("```json")
        if start_idx != -1:
            start_idx += 7
            end_idx = content.rfind("```")
            json_content = content[start_idx:end_idx].strip()
        else:
            json_content = content.strip()

        json_content = json_content.replace("None", "null")
        json_content = " ".join(json_content.replace("\n", " ").replace("\r", " ").split())

        return json.loads(json_content)
    except json.JSONDecodeError:
        try:
            json_content = json_content.replace(",]", "]").replace(",}", "}")
            return json.loads(json_content)
        except Exception:
            logger.exception("Failed to parse JSON from model output")
            return {}
    except Exception:
        logger.exception("Unexpected error while extracting JSON")
        return {}


def llm_completion(
    settings: RuntimeSettings,
    model: str | None,
    prompt: str,
    chat_history: Optional[List[dict]] = None,
    return_finish_reason: bool = False,
    max_tokens: int = 4096,
):
    m = model or settings.pageindex_model
    if return_finish_reason:
        return ChatGPT_API_with_finish_reason(settings, m, prompt, chat_history=chat_history, max_tokens=max_tokens)
    return ChatGPT_API(settings, m, prompt, chat_history=chat_history, max_tokens=max_tokens)
