"""LLM-based evidence evaluator: score each evidence sentence then aggregate."""
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@dataclass
class LLMEvidenceResult:
    """Result of LLM evidence evaluation."""
    per_sentence_scores: List[float] = field(default_factory=list)
    aggregate_score: float = 0.0
    raw_response: str = ""
    parse_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "per_sentence_scores": self.per_sentence_scores,
            "aggregate_score": self.aggregate_score,
            "raw_response": self.raw_response[:500] if self.raw_response else "",
            "parse_error": self.parse_error,
        }


class LLMEvidenceEvaluator:
    """
    Use an LLM to score each evidence sentence (relevance/support for the claim),
    then aggregate (e.g. mean) into one score.
    """

    def __init__(
        self,
        llm_client: Any,
        temperature: float = 0.0,
        max_tokens: int = 800,
    ):
        """
        Args:
            llm_client: Object with generate_with_usage(messages, ...) or generate(messages, ...)
                       returning dict with 'content' or str.
            temperature: Low for deterministic scoring.
            max_tokens: Max response length for JSON output.
        """
        self.llm_client = llm_client
        self.temperature = temperature
        self.max_tokens = max_tokens

    def evaluate(
        self,
        claim: str,
        evidence_sentences: List[str],
        predicted_label: Optional[str] = None,
    ) -> LLMEvidenceResult:
        """
        Score each evidence sentence (0.0–1.0) and return per-sentence + aggregate.

        Criteria: relevance to the claim, support for the stated label (if given),
        factual consistency. One LLM call with all sentences; response must be JSON.
        """
        if not evidence_sentences:
            return LLMEvidenceResult(aggregate_score=0.0)

        numbered = "\n".join(
            f"{i+1}. {s[:500]}{'...' if len(s) > 500 else ''}"
            for i, s in enumerate(evidence_sentences)
        )
        label_line = ""
        if predicted_label:
            label_line = f"\nStated assessment: {predicted_label}."

        prompt = f"""You are an evidence evaluator for fact-checking. For each evidence sentence below, score from 0.0 to 1.0:
- How relevant is this evidence to the claim?
- How well does it support or refute the claim (or the stated assessment)?
- How factual and verifiable does it seem?

Claim: "{claim}"{label_line}

Evidence sentences:
{numbered}

Respond with ONLY a valid JSON object, no other text. Use this exact shape:
{{"scores": [<float>, <float>, ...]}}

One float per sentence in order (1 = first sentence, 2 = second, etc.). Example: {{"scores": [0.8, 0.6, 0.9]}}"""

        messages = [
            {"role": "system", "content": "You output only valid JSON. No markdown, no explanation."},
            {"role": "user", "content": prompt},
        ]

        try:
            if hasattr(self.llm_client, "generate_with_usage"):
                out = self.llm_client.generate_with_usage(
                    messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            else:
                out = self.llm_client.generate(
                    messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            content = out.get("content", out) if isinstance(out, dict) else out
            if not isinstance(content, str):
                content = str(content)
            raw_response = content.strip()
        except Exception as e:
            return LLMEvidenceResult(
                aggregate_score=0.0,
                raw_response="",
                parse_error=f"LLM call failed: {e}",
            )

        # Parse JSON (allow markdown code block)
        scores, parse_error = self._parse_scores_json(raw_response, len(evidence_sentences))
        if parse_error:
            return LLMEvidenceResult(
                per_sentence_scores=scores,
                aggregate_score=sum(scores) / len(scores) if scores else 0.0,
                raw_response=raw_response[:500],
                parse_error=parse_error,
            )

        aggregate = sum(scores) / len(scores) if scores else 0.0
        return LLMEvidenceResult(
            per_sentence_scores=scores,
            aggregate_score=aggregate,
            raw_response=raw_response[:500],
        )

    def _parse_scores_json(self, raw: str, expected_count: int) -> tuple[List[float], Optional[str]]:
        """Extract scores list from raw LLM response. Returns (scores, parse_error)."""
        s = raw.strip()
        # Remove optional markdown code block
        if "```" in s:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL)
            if m:
                s = m.group(1)
        m = re.search(r"\{[^{}]*\"scores\"\s*:\s*\[[^\]]*\]\s*\}", s, re.DOTALL)
        if m:
            s = m.group(0)
        try:
            data = json.loads(s)
            scores = data.get("scores", [])
            if not isinstance(scores, list):
                return [], "scores is not a list"
            out = []
            for i, x in enumerate(scores):
                if i >= expected_count:
                    break
                try:
                    v = float(x)
                    v = max(0.0, min(1.0, v))
                    out.append(v)
                except (TypeError, ValueError):
                    out.append(0.0)
            while len(out) < expected_count:
                out.append(0.0)
            return out[:expected_count], None
        except json.JSONDecodeError as e:
            # Fallback: find first bracket list of numbers
            m = re.search(r"\[\s*([0-9.,\s]+)\s*\]", s)
            if m:
                parts = re.findall(r"0?\.\d+|[01]", m.group(1))
                out = []
                for p in parts[:expected_count]:
                    try:
                        out.append(max(0.0, min(1.0, float(p))))
                    except ValueError:
                        out.append(0.0)
                while len(out) < expected_count:
                    out.append(0.0)
                return out[:expected_count], f"JSON failed, used regex: {e}"
            return [], str(e)
