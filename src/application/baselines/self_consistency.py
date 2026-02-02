"""Self-Consistency baseline implementation."""
import re
import uuid
from typing import List, Dict
from collections import Counter

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.entities.task import Task
from domain.entities.episode import Episode, VerificationResult
from domain.entities.message import Message
from domain.value_objects.labels import FEVERLabel
from domain.value_objects.role import AgentRole
from application.baselines.base_baseline import BaseBaseline


class SelfConsistency(BaseBaseline):
    """
    Self-Consistency baseline.
    
    Implementation of "Self-Consistency Improves Chain of Thought Reasoning" (Wang et al., 2022).
    
    Method:
    1. Sample K diverse reasoning paths with temperature > 0
    2. Extract final answer from each path
    3. Vote by majority for most consistent answer
    
    This is a strong baseline because:
    - State-of-the-art for reasoning tasks
    - Uses same model, just multiple samples
    - Fair cost comparison (K * single call)
    """
    
    def __init__(self, llm_client, k_samples: int = 5, temperature: float = 0.7, **kwargs):
        """
        Initialize Self-Consistency baseline.
        
        Args:
            llm_client: LLM client for predictions
            k_samples: Number of samples to generate (K)
            temperature: Temperature for diverse sampling
        """
        super().__init__(llm_client, k_samples=k_samples, temperature=temperature, **kwargs)
        self.k_samples = k_samples
        self.temperature = temperature
    
    def get_baseline_id(self) -> str:
        """Get baseline identifier."""
        return f"self_consistency_k{self.k_samples}"
    
    async def execute(self, task: Task) -> Episode:
        """
        Execute Self-Consistency on a task.
        
        Args:
            task: Task to solve
            
        Returns:
            Episode with majority-voted prediction
        """
        episode_id = f"sc_{task.task_id}_{uuid.uuid4().hex[:8]}"
        
        # Generate K diverse samples
        samples = []
        transcript = []
        
        system_prompt = self.get_system_prompt()
        user_prompt = self._create_user_prompt(task)
        
        for i in range(self.k_samples):
            # Sample with temperature
            response = await self.llm_client.generate(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature
            )
            
            samples.append(response)
            
            # Add to transcript
            if i == 0:  # Only add user message once
                transcript.append(Message(
                    role=AgentRole.SENDER,
                    content=user_prompt,
                    evidence=[],
                    metadata={"sample_id": i}
                ))
            
            transcript.append(Message(
                role=AgentRole.SENDER,
                content=response,
                evidence=[],
                metadata={"sample_id": i, "temperature": self.temperature}
            ))
        
        # Extract predictions from samples
        predictions = [self._extract_prediction(sample) for sample in samples]
        
        # Majority vote
        vote_counts = Counter(predictions)
        majority_prediction = vote_counts.most_common(1)[0][0]
        
        # Create verification result
        label_correct = (majority_prediction == task.label)
        
        verifier_result = VerificationResult(
            label_correct=label_correct,
            evidence_provided=False,  # Self-consistency doesn't provide evidence
            evidence_match_score=0.0,
            predicted_label=str(majority_prediction),
            additional_info={
                "k_samples": self.k_samples,
                "predictions": [str(p) for p in predictions],
                "vote_counts": {str(k): v for k, v in vote_counts.items()},
                "majority_votes": vote_counts[majority_prediction],
                "agreement_rate": vote_counts[majority_prediction] / self.k_samples
            }
        )
        
        # Create episode
        episode = Episode(
            episode_id=episode_id,
            task=task,
            protocol_id=self.get_baseline_id(),
            deviation_type="baseline",
            transcript=transcript,
            verifier_result=verifier_result,
            metrics={
                "accuracy": 1.0 if label_correct else 0.0,
                "evidence_compliance": 0.0,
                "k_samples": self.k_samples,
                "agreement_rate": vote_counts[majority_prediction] / self.k_samples
            },
            payoff=0.0  # Will be calculated by payoff calculator
        )
        
        return episode
    
    def _extract_prediction(self, response: str) -> FEVERLabel:
        """
        Extract FEVER label from response.
        
        Args:
            response: LLM response text
            
        Returns:
            Extracted FEVERLabel
        """
        response_upper = response.upper()
        
        # Look for explicit assessment
        if "ASSESSMENT:" in response_upper:
            match = re.search(r'ASSESSMENT:\s*(SUPPORTS|REFUTES|NOT ENOUGH INFO)', response_upper)
            if match:
                return FEVERLabel.from_string(match.group(1))
        
        # Look for any mention of labels
        if "REFUTES" in response_upper:
            return FEVERLabel.REFUTES
        elif "SUPPORTS" in response_upper:
            return FEVERLabel.SUPPORTS
        elif "NOT ENOUGH INFO" in response_upper:
            return FEVERLabel.NOT_ENOUGH_INFO
        
        # Default to NOT_ENOUGH_INFO if unclear
        return FEVERLabel.NOT_ENOUGH_INFO
    
    def get_system_prompt(self) -> str:
        """Get system prompt for Self-Consistency."""
        return """You are an AI assistant helping to verify factual claims.

Your task is to analyze the given FEVER claim and determine if it is:
- SUPPORTS: The claim is supported by evidence
- REFUTES: The claim is refuted by evidence
- NOT ENOUGH INFO: There is not enough information to determine

Think through your reasoning step by step, then provide your final assessment.

Format:
Reasoning: [Think through the claim step by step]
Assessment: [SUPPORTS/REFUTES/NOT ENOUGH INFO]"""
