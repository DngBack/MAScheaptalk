"""FEVER ground truth verifier."""
import re
from typing import Optional

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.ports.verifier import Verifier
from domain.entities.episode import Episode, VerificationResult
from domain.value_objects.labels import FEVERLabel
from domain.value_objects.role import AgentRole


class FEVERGroundTruthVerifier(Verifier):
    """Verifier that checks FEVER episodes against ground truth."""
    
    def __init__(self, use_semantic_matching: bool = False):
        """
        Initialize verifier.
        
        Args:
            use_semantic_matching: If True, use semantic similarity for evidence matching
                                   (requires sentence-transformers). Otherwise use string matching.
        """
        self.use_semantic_matching = use_semantic_matching
        
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
        
        # Check evidence matching score
        evidence_match_score = self._compute_evidence_match_score(episode)
        
        return VerificationResult(
            label_correct=label_correct,
            evidence_provided=evidence_provided,
            evidence_match_score=evidence_match_score,
            predicted_label=predicted_label,
            additional_info={
                "ground_truth_label": str(episode.task.label),
                "num_ground_truth_evidence": len(episode.task.evidence)
            }
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
    
    def _compute_evidence_match_score(self, episode: Episode) -> float:
        """Compute how well provided evidence matches ground truth."""
        if not self._check_evidence_provided(episode):
            return 0.0
        
        # Get ground truth evidence texts
        gt_evidence_texts = [e.text.lower() for e in episode.task.evidence if e.text != "No evidence available"]
        
        if not gt_evidence_texts:
            # If no ground truth evidence, can't compute match
            return 0.0
        
        # Collect provided evidence from transcript
        provided_evidence = []
        for message in episode.transcript:
            if message.role == AgentRole.SENDER:
                if message.evidence and len(message.evidence) > 0:
                    provided_evidence.extend([e.text.lower() for e in message.evidence])
                
                # Also extract evidence from message content
                evidence_text = self._extract_evidence_from_text(message.content)
                if evidence_text:
                    provided_evidence.append(evidence_text.lower())
        
        if not provided_evidence:
            return 0.0
        
        # Compute matching score
        if self.use_semantic_matching and self.embedding_model:
            return self._semantic_similarity(provided_evidence, gt_evidence_texts)
        else:
            return self._string_matching(provided_evidence, gt_evidence_texts)
    
    def _extract_evidence_from_text(self, text: str) -> Optional[str]:
        """Extract evidence text from message content."""
        # Look for patterns like "Evidence: ..." or "Source: ..."
        patterns = [
            r"Evidence:\s*(.+?)(?:\n|$)",
            r"Source:\s*(.+?)(?:\n|$)",
            r"According to\s+(.+?)(?:\n|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _string_matching(self, provided: list, ground_truth: list) -> float:
        """Simple string matching for evidence."""
        # Check how many ground truth evidence pieces have substantial overlap with provided
        matches = 0
        
        for gt in ground_truth:
            for prov in provided:
                # Check for substantial overlap (>50% of words match)
                gt_words = set(gt.split())
                prov_words = set(prov.split())
                
                if not gt_words or not prov_words:
                    continue
                
                overlap = len(gt_words & prov_words)
                overlap_ratio = overlap / min(len(gt_words), len(prov_words))
                
                if overlap_ratio > 0.5:
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
