"""
Assessment Agent — multi-turn repayment capacity chat.

AssessmentSession manages a Claude conversation that acts as a loan advisor
(Priya). Each call to `chat()` appends the user message and returns the
assistant's next reply. When the LLM signals assessment_complete in its JSON,
`finalize()` parses and returns the structured result.
"""

import json
import logging
import re
from pathlib import Path

import anthropic
from jinja2 import Environment, FileSystemLoader

from config.settings import settings

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


def _build_system_prompt(applicant_data: dict) -> str:
    env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)))
    env.filters["format_inr"] = _format_inr
    template = env.get_template("assessment.j2")

    monthly_income = float(applicant_data.get("monthly_income", 0))
    loan_amount = float(applicant_data.get("loan_amount", 0))
    tenure = int(applicant_data.get("tenure_months", 12))
    existing_emi = float(applicant_data.get("existing_emi_amount", 0))

    # Rough EMI estimate: flat interest ~12% p.a.
    rate_monthly = 0.12 / 12
    if rate_monthly > 0 and tenure > 0:
        estimated_emi = loan_amount * rate_monthly / (1 - (1 + rate_monthly) ** -tenure)
    else:
        estimated_emi = loan_amount / tenure if tenure else 0

    total_obligations = existing_emi + estimated_emi
    dti_ratio = round(total_obligations / monthly_income * 100, 1) if monthly_income else 0

    return template.render(
        **applicant_data,
        estimated_emi=estimated_emi,
        total_obligations=total_obligations,
        dti_ratio=dti_ratio,
    )


class AssessmentSession:
    """Stateful multi-turn assessment conversation."""

    def __init__(self, session_id: str, application_id: str, applicant_data: dict):
        self.session_id = session_id
        self.application_id = application_id
        self.history: list[dict] = []
        self._system_prompt = _build_system_prompt(applicant_data)
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.assessment_result: dict | None = None
        self.opening: str = ""

    async def start(self) -> str:
        """Send the opening greeting from the advisor."""
        opening = (
            "Hi! I'm Priya from LoanFlow. I just need to have a quick chat before we "
            "finalise your loan. It'll only take a couple of minutes — just a few questions "
            "to make sure everything goes smoothly. Ready to start?"
        )
        self.opening = opening
        self.history.append({"role": "assistant", "content": opening})
        return opening

    async def chat(self, user_message: str) -> tuple[str, bool]:
        """
        Append user message, get assistant reply.
        Returns (reply_text, is_complete).
        is_complete=True means the LLM embedded the final JSON.
        """
        self.history.append({"role": "user", "content": user_message})

        response = await self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=self._system_prompt,
            messages=self.history,
        )
        reply = response.content[0].text.strip()
        self.history.append({"role": "assistant", "content": reply})

        # Check if the LLM embedded the final JSON
        is_complete = self._try_parse_result(reply)
        return reply, is_complete

    def _try_parse_result(self, text: str) -> bool:
        """Attempt to extract and cache assessment JSON. Returns True if found."""
        m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if not m:
            m = re.search(r"\{.*?\"assessment_complete\"\s*:\s*true.*?\}", text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1) if "```" in text else m.group(0))
                if data.get("assessment_complete"):
                    self.assessment_result = data
                    return True
            except Exception:
                pass
        return False

    def get_result(self) -> dict | None:
        return self.assessment_result

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "application_id": self.application_id,
            "history": self.history,
            "assessment_result": self.assessment_result,
        }
