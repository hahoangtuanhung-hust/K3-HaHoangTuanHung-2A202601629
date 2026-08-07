"""
Lab 11 — Configuration & API Key Setup
"""
import os


def setup_api_key():
    """Load Google API key from environment or prompt."""
    from dotenv import load_dotenv
    from pathlib import Path
    
    # Load .env from project root
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    if "GOOGLE_API_KEY" not in os.environ or not os.environ["GOOGLE_API_KEY"]:
        try:
            import sys
            if sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
                os.environ["GOOGLE_API_KEY"] = input("Enter Google API Key: ")
        except Exception:
            pass
    if "OPENAI_API_KEY" not in os.environ or not os.environ["OPENAI_API_KEY"]:
        try:
            import sys
            if sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
                os.environ["OPENAI_API_KEY"] = input("Enter OpenAI API Key: ")
        except Exception:
            pass
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"
    print("API keys loaded.")


# Allowed banking topics (used by topic_filter)
ALLOWED_TOPICS = [
    "banking", "account", "transaction", "transfer",
    "loan", "interest", "savings", "credit",
    "deposit", "withdrawal", "balance", "payment",
    "tai khoan", "giao dich", "tiet kiem", "lai suat",
    "chuyen tien", "the tin dung", "so du", "vay",
    "ngan hang", "atm",
]

# Blocked topics (immediate reject)
BLOCKED_TOPICS = [
    "hack", "exploit", "weapon", "drug", "illegal",
    "violence", "gambling", "bomb", "kill", "steal",
]
