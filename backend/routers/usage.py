import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import DatabaseManager
from pathlib import Path
import os
from dotenv import load_dotenv

router = APIRouter(prefix="/usage", tags=["Usage"])
db = DatabaseManager(str(Path(__file__).parent.parent.parent / "data.db"))

# Load environment variables
root_dir = Path(__file__).parent.parent.parent
load_dotenv(root_dir / ".env")


class LLMUsageResponse(BaseModel):
    provider: str = "OpenRouter"
    usage: Optional[float] = None
    usage_monthly: Optional[float] = None
    usage_daily: Optional[float] = None
    usage_weekly: Optional[float] = None
    total_credits: Optional[float] = None
    total_usage: Optional[float] = None
    remaining: Optional[float] = None
    is_low_balance: bool = False
    has_credits: bool = False


@router.get("/llm", response_model=LLMUsageResponse)
async def get_llm_usage():
    """
    OpenRouter API key kullanım bilgilerini getir.
    OpenRouter /api/v1/credits ve /api/v1/key endpoint'lerini kullanır.
    Kalan kredi = total_credits - total_usage
    """
    # Get warning threshold from settings
    warning_threshold_str = db.get_setting("llm_warning_threshold")
    try:
        warning_threshold = float(warning_threshold_str) if warning_threshold_str else 5.00
    except (ValueError, TypeError):
        warning_threshold = 5.00

    # Get API key only from environment (.env)
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        return LLMUsageResponse(
            provider="OpenRouter",
            usage=None,
            usage_monthly=None,
            usage_daily=None,
            usage_weekly=None,
            total_credits=None,
            total_usage=None,
            remaining=None,
            is_low_balance=False,
            has_credits=False
        )

    try:
        async with httpx.AsyncClient() as client:
            # Get credits info (total_credits, total_usage)
            credits_response = await client.get(
                "https://openrouter.ai/api/v1/credits",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://approximatecostpro.com",
                    "X-Title": "Approximate Cost Pro"
                },
                timeout=10.0
            )
            credits_response.raise_for_status()
            credits_data = credits_response.json().get("data", {})
            total_credits = credits_data.get("total_credits")
            total_usage = credits_data.get("total_usage")

            # Get detailed usage info (monthly, daily, weekly)
            key_response = await client.get(
                "https://openrouter.ai/api/v1/key",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://approximatecostpro.com",
                    "X-Title": "Approximate Cost Pro"
                },
                timeout=10.0
            )
            key_response.raise_for_status()
            key_data = key_response.json().get("data", {})
            usage_monthly = key_data.get("usage_monthly")
            usage_daily = key_data.get("usage_daily")
            usage_weekly = key_data.get("usage_weekly")

            # Calculate remaining balance
            has_credits = total_credits is not None
            remaining = None
            is_low_balance = False

            if has_credits and total_usage is not None:
                remaining = total_credits - total_usage
                is_low_balance = remaining <= warning_threshold

            return LLMUsageResponse(
                provider="OpenRouter",
                usage=total_usage,
                usage_monthly=usage_monthly,
                usage_daily=usage_daily,
                usage_weekly=usage_weekly,
                total_credits=total_credits,
                total_usage=total_usage,
                remaining=remaining,
                is_low_balance=is_low_balance,
                has_credits=has_credits
            )

    except httpx.HTTPError as e:
        print(f"OpenRouter API error: {e}")
        return LLMUsageResponse(
            provider="OpenRouter",
            usage=None,
            usage_monthly=None,
            usage_daily=None,
            usage_weekly=None,
            total_credits=None,
            total_usage=None,
            remaining=None,
            is_low_balance=False,
            has_credits=False
        )
    except Exception as e:
        print(f"Unexpected error fetching LLM usage: {e}")
        return LLMUsageResponse(
            provider="OpenRouter",
            usage=None,
            usage_monthly=None,
            usage_daily=None,
            usage_weekly=None,
            total_credits=None,
            total_usage=None,
            remaining=None,
            is_low_balance=False,
            has_credits=False
        )
