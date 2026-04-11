"""
Negotiation Agent

Takes an application's credit/offer state and returns structured advice
for the RM: which offer to recommend, risk analysis per option, DTI impact,
and counter-offer guidance.
"""

import logging
from pathlib import Path

import anthropic
from jinja2 import Environment, FileSystemLoader

from config.settings import settings
from services.json_parser import parse_llm_json

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"


def _format_inr(value) -> str:
    s = str(int(value))
    if len(s) <= 3:
        return s
    result = s[-3:]
    s = s[:-3]
    while len(s) > 2:
        result = s[-2:] + "," + result
        s = s[:-2]
    if s:
        result = s + "," + result
    return result


def _render_prompt(context: dict) -> str:
    env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)))
    env.filters["format_inr"] = _format_inr
    template = env.get_template("negotiation.j2")
    return template.render(**context)


async def run_negotiation_analysis(application_data: dict) -> dict:
    """
    Generate offer recommendation advice for the RM.

    application_data should include:
      full_name, monthly_income, existing_emi_amount, employment_type,
      loan_amount, tenure_months, credit_score, offers (list of A/B/C dicts)
    """
    prompt = _render_prompt(application_data)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    result = parse_llm_json(raw)

    logger.info(
        "Negotiation advice: recommend=%s affordability=%s",
        result.get("recommended_option"),
        result.get("affordability_verdict"),
    )
    return result
