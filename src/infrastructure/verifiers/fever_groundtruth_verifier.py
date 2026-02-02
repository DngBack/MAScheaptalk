"""FEVER ground truth verifier."""
import re
import string
from typing import Optional, List, Any, Dict

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.ports.verifier import Verifier
from domain.entities.episode import Episode, VerificationResult
from domain.value_objects.labels import FEVERLabel
from domain.value_objects.role import AgentRole


def _normalize_text(s: str) -> str:
    """Normalize text for matching: lowercase, collapse whitespace, strip."""
    if not s:
        return ""
    return " ".join(s.lower().split()).strip()


def _tokenize_for_overlap(s: str) -> set:
    """
    Tokenize text for overlap: lowercase words, strip leading/trailing punctuation.
    So 'season.' and 'season' both become 'season'; '49ers'' becomes '49ers'.
    """
    if not s:
        return set()
    out = set()
    for w in s.lower().split():
        w = w.strip(string.punctuation)
        if w:
            out.add(w)
    return out


class FEVERGroundTruthVerifier(Verifier):
    """Verifier that checks FEVER episodes against ground truth."""
    
    # Overlap ratio threshold: gt words that must appear in provided (or vice versa)
    # 0.3 = partial match (e.g. paraphrased evidence); 0.5 = stricter
    EVIDENCE_OVERLAP_THRESHOLD = 0.3
    
    def __init__(
        self,
        use_semantic_matching: bool = False,
        overlap_threshold: float = 0.3,
        llm_evidence_evaluator: Optional[Any] = None,
        evidence_score_weights: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize verifier.
        
        Args:
            use_semantic_matching: If True, use semantic similarity for evidence matching
                                   (requires sentence-transformers). Otherwise use string matching.
            overlap_threshold: Min word-overlap ratio for string match (default 0.3).
            llm_evidence_evaluator: Optional LLMEvidenceEvaluator to score each evidence sentence
                                   via LLM; scores are aggregated and combined with string/semantic score.
            evidence_score_weights: Weights for combining scores, e.g. {"string_match": 0.5, "llm": 0.5}.
                                   If only one source is available, that score is used. Default: no LLM.
        """
        self.use_semantic_matching = use_semantic_matching
        self.overlap_threshold = overlap_threshold
        self.llm_evidence_evaluator = llm_evidence_evaluator
        if evidence_score_weights is not None:
            self.evidence_score_weights = evidence_score_weights
        elif llm_evidence_evaluator is not None:
            self.evidence_score_weights = {"string_match": 0.5, "llm": 0.5}
        else:
            self.evidence_score_weights = {}
        
        if use_semantic_matching:
            try:
                from sentence_transformers import SentenceTransformer
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                print("Warning: sentence-transformers not available, falling back to string matching")
                self.use_semantic_matching = False
                self.embedding_model = None
        else:
            self.embedding_model = None
    
    def verify(self, episode: Episode) -> VerificationResult:
        """Verify an episode against ground truth."""
        # Extract predicted label from transcript
        predicted_label = self._extract_predicted_label(episode)
        
        # Check label correctness
        label_correct = False
        if predicted_label:
            try:
                pred_label_enum = FEVERLabel.from_string(predicted_label)
                label_correct = (pred_label_enum == episode.task.label)
            except ValueError:
                label_correct = False
        
        # Check if evidence was provided
        evidence_provided = self._check_evidence_provided(episode)
        
        # Check evidence matching score (and collect debug info)
        evidence_match_score, match_debug = self._compute_evidence_match_score_with_debug(episode)
        
        additional_info = {
            "ground_truth_label": str(episode.task.label),
            "num_ground_truth_evidence": len(episode.task.evidence),
            **match_debug
        }
        
        return VerificationResult(
            label_correct=label_correct,
            evidence_provided=evidence_provided,
            evidence_match_score=evidence_match_score,
            predicted_label=predicted_label,
            additional_info=additional_info
        )
    
    def _extract_predicted_label(self, episode: Episode) -> Optional[str]:
        """Extract predicted label from episode transcript."""
        # Look for label in Receiver's decision message
        for message in reversed(episode.transcript):
            if message.role == AgentRole.RECEIVER:
                content = message.content.upper()
                
                # Look for explicit labels
                if "SUPPORTS" in content or "SUPPORTED" in content:
                    return "SUPPORTS"
                elif "REFUTES" in content or "REFUTED" in content:
                    return "REFUTES"
                elif "NOT ENOUGH INFO" in content or "NEI" in content:
                    return "NOT ENOUGH INFO"
        
        # If not found in Receiver, check Sender messages
        for message in episode.transcript:
            if message.role == AgentRole.SENDER:
                content = message.content.upper()
                
                if "SUPPORTS" in content or "SUPPORTED" in content:
                    return "SUPPORTS"
                elif "REFUTES" in content or "REFUTED" in content:
                    return "REFUTES"
                elif "NOT ENOUGH INFO" in content or "NEI" in content:
                    return "NOT ENOUGH INFO"
        
        return None
    
    def _check_evidence_provided(self, episode: Episode) -> bool:
        """Check if evidence was provided in the episode."""
        for message in episode.transcript:
            if message.role == AgentRole.SENDER:
                # Check if message has evidence attached
                if message.evidence and len(message.evidence) > 0:
                    return True
                
                # Check if message content mentions evidence
                content_lower = message.content.lower()
                if any(keyword in content_lower for keyword in ["evidence:", "source:", "from wikipedia", "according to"]):
                    return True
        
        return False
    
    def _compute_evidence_match_score_with_debug(self, episode: Episode) -> tuple[float, dict]:
        """
        Compute how well provided evidence matches ground truth.
        Optionally adds LLM-based per-sentence evaluation, then aggregates.
        Returns (score, debug_dict) for reporting evidence validity.
        """
        debug: dict = {}
        
        if not self._check_evidence_provided(episode):
            debug["evidence_validity_skipped_reason"] = "no_evidence_provided"
            return 0.0, debug
        
        # Get ground truth evidence texts (exclude placeholders from repo)
        gt_evidence_texts: List[str] = []
        for e in episode.task.evidence:
            if not e.text or not e.text.strip():
                continue
            t = _normalize_text(e.text)
            if t == "no evidence available" or t == "evidence":
                continue
            if t.startswith("evidence from http") or (len(t) < 30 and "evidence from" in t):
                continue
            if len(t) > 10:
                gt_evidence_texts.append(t)
        
        # Collect provided evidence from transcript (both Message.evidence and parsed content)
        provided_evidence: List[str] = []
        for message in episode.transcript:
            if message.role != AgentRole.SENDER:
                continue
            if message.evidence and len(message.evidence) > 0:
                provided_evidence.extend([_normalize_text(e.text) for e in message.evidence])
            for block in self._extract_all_evidence_from_text(message.content):
                if block and len(block) > 5:
                    provided_evidence.append(_normalize_text(block))
        
        seen = set()
        unique_provided = []
        for p in provided_evidence:
            if p not in seen and len(p) > 5:
                seen.add(p)
                unique_provided.append(p)
        provided_evidence = unique_provided
        
        debug["num_gt_sentences"] = len(gt_evidence_texts)
        debug["num_provided_sentences"] = len(provided_evidence)
        
        if not provided_evidence:
            debug["evidence_validity_skipped_reason"] = "no_evidence_parsed_from_content"
            return 0.0, debug
        
        # 1) String/semantic match score (only when we have ground truth)
        string_match_score = 0.0
        if gt_evidence_texts:
            if self.use_semantic_matching and self.embedding_model:
                string_match_score = self._semantic_similarity(provided_evidence, gt_evidence_texts)
            else:
                string_match_score = self._string_matching(provided_evidence, gt_evidence_texts)
        else:
            debug["evidence_validity_skipped_reason"] = "no_ground_truth_text"
        
        # 2) Optional LLM evaluation: score each evidence sentence, then aggregate
        llm_score: Optional[float] = None
        if self.llm_evidence_evaluator:
            predicted_label = self._extract_predicted_label(episode)
            llm_result = self.llm_evidence_evaluator.evaluate(
                claim=episode.task.claim,
                evidence_sentences=provided_evidence,
                predicted_label=predicted_label,
            )
            llm_score = llm_result.aggregate_score
            debug["llm_evidence_score"] = llm_score
            debug["llm_per_sentence_scores"] = llm_result.per_sentence_scores
            if llm_result.parse_error:
                debug["llm_evidence_parse_error"] = llm_result.parse_error
        
        # 3) Combine scores with weights
        weights = self.evidence_score_weights
        w_string = weights.get("string_match", 0.5)
        w_llm = weights.get("llm", 0.5)
        
        if llm_score is not None and gt_evidence_texts:
            total = w_string + w_llm
            score = (w_string * string_match_score + w_llm * llm_score) / total if total > 0 else llm_score
        elif llm_score is not None:
            score = llm_score
        else:
            score = string_match_score
        
        debug["evidence_match_score"] = score
        if llm_score is not None:
            debug["string_match_score"] = string_match_score
        return score, debug
    
    def _compute_evidence_match_score(self, episode: Episode) -> float:
        """Compute evidence match score (legacy interface)."""
        score, _ = self._compute_evidence_match_score_with_debug(episode)
        return score
    
    def _extract_all_evidence_from_text(self, text: str) -> List[str]:
        """
        Extract all evidence blocks from message content.
        Supports: Evidence: ... (multiline until Confidence/Reasoning/next section), bullet lists, Evidence 1/2.
        """
        blocks: List[str] = []
        
        # 1) Explicit "Evidence:" block — capture until next section (Confidence, Reasoning, Decision, empty line then title case)
        evidence_section = re.search(
            r"\bEvidence\s*:\s*(.+?)"
            r"(?=\s*(?:Confidence|Reasoning|Decision|Final|Assessment|$))",
            text,
            re.IGNORECASE | re.DOTALL
        )
        if evidence_section:
            raw = evidence_section.group(1).strip()
            # Split by numbered items (1., 2., - ) or double newline
            for part in re.split(r"\n\s*(?:\d+[.)]\s*|[-*]\s*)", raw):
                part = part.strip()
                if len(part) > 15:
                    blocks.append(part)
            if not blocks and len(raw) > 15:
                blocks.append(raw)
        
        # 2) Single-line Evidence: ... (original pattern)
        if not blocks:
            for m in re.finditer(r"Evidence\s*:\s*(.+?)(?=\n|$)", text, re.IGNORECASE | re.MULTILINE):
                b = m.group(1).strip()
                if len(b) > 15:
                    blocks.append(b)
        
        # 3) Source: ... or According to ...
        for m in re.finditer(r"(?:Source|According to)\s*[:\s]+(.+?)(?=\n\n|\n\w+[\s:]|$)", text, re.IGNORECASE | re.DOTALL):
            b = m.group(1).strip()
            if len(b) > 15:
                blocks.append(b)
        
        return blocks
    
    def _extract_evidence_from_text(self, text: str) -> Optional[str]:
        """Extract first evidence block (legacy: single string)."""
        blocks = self._extract_all_evidence_from_text(text)
        return blocks[0] if blocks else None
    
    def _string_matching(self, provided: List[str], ground_truth: List[str]) -> float:
        """String matching: fraction of GT sentences with overlap >= overlap_threshold.
        Uses tokenization that strips punctuation so 'season.' matches 'season'.
        """
        threshold = getattr(self, "overlap_threshold", self.EVIDENCE_OVERLAP_THRESHOLD)
        matches = 0
        
        for gt in ground_truth:
            gt_words = _tokenize_for_overlap(gt)
            if not gt_words:
                continue
            for prov in provided:
                prov_words = _tokenize_for_overlap(prov)
                if not prov_words:
                    continue
                overlap = len(gt_words & prov_words)
                overlap_ratio_gt = overlap / len(gt_words)
                overlap_ratio_prov = overlap / len(prov_words)
                if overlap_ratio_gt >= threshold or overlap_ratio_prov >= threshold:
                    matches += 1
                    break
        
        return matches / len(ground_truth) if ground_truth else 0.0
    
    def _semantic_similarity(self, provided: list, ground_truth: list) -> float:
        """Semantic similarity matching using embeddings."""
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Encode all texts
        prov_embeddings = self.embedding_model.encode(provided)
        gt_embeddings = self.embedding_model.encode(ground_truth)
        
        # Compute pairwise similarities
        similarities = cosine_similarity(gt_embeddings, prov_embeddings)
        
        # For each ground truth, take max similarity to any provided evidence
        max_similarities = similarities.max(axis=1)
        
        # Average the max similarities
        return float(max_similarities.mean())
