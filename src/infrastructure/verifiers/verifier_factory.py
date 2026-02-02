"""Factory to create FEVER verifier with optional LLM evidence evaluation."""
import os
from typing import Optional, Any, Dict

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from infrastructure.verifiers.fever_groundtruth_verifier import FEVERGroundTruthVerifier
from infrastructure.verifiers.llm_evidence_evaluator import LLMEvidenceEvaluator
from infrastructure.llm.openai_client import OpenAIClient


def create_fever_verifier(
    use_semantic_matching: bool = False,
    overlap_threshold: float = 0.3,
    use_llm_evidence_eval: Optional[bool] = None,
    llm_model: Optional[str] = None,
    api_key: Optional[str] = None,
    evidence_score_weights: Optional[Dict[str, float]] = None,
) -> FEVERGroundTruthVerifier:
    """
    Create FEVERGroundTruthVerifier with optional LLM-based evidence scoring.

    Evidence score = string/semantic match vs ground truth + optional LLM score
    (LLM scores each evidence sentence 0–1, then aggregate; combined with weights).

    Args:
        use_semantic_matching: Use sentence-transformers for evidence match.
        overlap_threshold: Word-overlap threshold for string match (default 0.3).
        use_llm_evidence_eval: If True, add LLM evaluator. If None, read from env USE_LLM_EVIDENCE_EVAL.
        llm_model: Model name for LLM evaluator (default from OPENAI_MODEL or gpt-4o-mini).
        api_key: OpenAI API key for LLM evaluator (default from OPENAI_API_KEY).
        evidence_score_weights: e.g. {"string_match": 0.5, "llm": 0.5}. Default 0.5/0.5 when LLM enabled.

    Returns:
        FEVERGroundTruthVerifier instance.
    """
    if use_llm_evidence_eval is None:
        use_llm_evidence_eval = os.getenv("USE_LLM_EVIDENCE_EVAL", "").strip().lower() in ("1", "true", "yes")

    llm_evaluator = None
    weights = evidence_score_weights
    if use_llm_evidence_eval:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if key:
            model = llm_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            eval_client = OpenAIClient(model=model, api_key=key)
            llm_evaluator = LLMEvidenceEvaluator(llm_client=eval_client, temperature=0.0, max_tokens=800)
            if weights is None:
                weights = {"string_match": 0.5, "llm": 0.5}

    return FEVERGroundTruthVerifier(
        use_semantic_matching=use_semantic_matching,
        overlap_threshold=overlap_threshold,
        llm_evidence_evaluator=llm_evaluator,
        evidence_score_weights=weights,
    )
