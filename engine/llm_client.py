import os
import sys
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# Reconfigure stdout/stderr to utf-8 for Windows compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def get_llm_client_and_model(default_model="gemini-3.1-flash-lite"):
    """
    Trả về OpenAI client tương thích và tên model tương ứng.
    Ưu tiên cấu hình GEMINI_API_KEY và base_url của Google AI Studio,
    sau đó fallback sang OPENAI_API_KEY.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if gemini_key:
        # Sử dụng API tương thích OpenAI của Gemini
        model = os.getenv("GEMINI_MODEL", default_model)
        client = AsyncOpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        return client, model
    elif openai_key:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        client = AsyncOpenAI(api_key=openai_key)
        return client, model
    else:
        return None, None

def get_multi_judge_models():
    """
    Trả về client và 2 model Judge khác nhau phục vụ cho Multi-Judge Consensus.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if gemini_key:
        model_a = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        # Sử dụng model Gemini 1.5 Flash làm Judge thứ hai để có sự đối sánh độc lập
        model_b = "gemini-1.5-flash" if model_a != "gemini-1.5-flash" else "gemini-3.1-flash-lite"
        client = AsyncOpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        return client, model_a, model_b
    elif openai_key:
        model_a = os.getenv("OPENAI_MODEL", "gpt-4o")
        model_b = "gpt-4o-mini"
        client = AsyncOpenAI(api_key=openai_key)
        return client, model_a, model_b
    else:
        return None, None, None
