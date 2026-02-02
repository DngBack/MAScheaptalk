"""Run episode use case."""
import asyncio
import uuid
from typing import Optional, Dict, Any

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.entities.task import Task
from domain.entities.episode import Episode
from domain.ports.verifier import Verifier
from application.protocols.base_protocol import BaseProtocol
from infrastructure.frameworks.autogen_adapter import AutoGenAdapter


class RunEpisode:
    """Use case for running a single episode."""
    
    def __init__(
        self,
        protocol: BaseProtocol,
        verifier: Verifier,
        model_name: str = "gpt-4o",
        api_key: Optional[str] = None,
        lambda_cost: float = 0.01,
        mu_penalty: float = 0.5
    ):
        """
        Initialize run episode use case.
        
        Args:
            protocol: Protocol to use
            verifier: Verifier for checking correctness
            model_name: Model name for LLM
            api_key: API key for LLM
            lambda_cost: Cost weight in payoff function
            mu_penalty: Penalty weight in payoff function
        """
        self.protocol = protocol
        self.verifier = verifier
        self.model_name = model_name
        self.api_key = api_key
        self.lambda_cost = lambda_cost
        self.mu_penalty = mu_penalty
        
        # Create AutoGen adapter
        self.adapter = AutoGenAdapter(
            protocol=protocol,
            model_name=model_name,
            api_key=api_key
        )
    
    async def execute(
        self,
        task: Task,
        deviation_type: str = "honest"
    ) -> Episode:
        """
        Execute a single episode.
        
        Args:
            task: Task to execute
            deviation_type: Deviation strategy ("honest", "no_evidence", etc.)
            
        Returns:
            Episode with results
        """
        # Generate episode ID
        episode_id = f"ep_{task.task_id}_{deviation_type}_{uuid.uuid4().hex[:8]}"
        
        # Run conversation
        transcript, usage_info = await self.adapter.run_conversation(
            task=task,
            deviation_type=deviation_type
        )
        
        # Create episode
        episode = Episode(
            episode_id=episode_id,
            task=task,
            protocol_id=self.protocol.get_protocol_id(),
            deviation_type=deviation_type,
            transcript=transcript
        )
        
        # Verify episode
        verifier_result = self.verifier.verify(episode)
        episode.verifier_result = verifier_result
        
        # Compute metrics
        metrics = self._compute_metrics(episode, usage_info)
        episode.metrics = metrics
        
        # Compute payoff
        episode.payoff = self._compute_payoff(episode)
        
        return episode
    
    def _compute_metrics(self, episode: Episode, usage_info: Dict[str, Any]) -> Dict[str, float]:
        """Compute episode metrics."""
        metrics = {}
        
        # Cost metrics (based on token usage)
        total_tokens = usage_info.get("total_tokens", 0)
        # Rough cost estimate: $0.01 per 1K tokens for GPT-4o
        cost_per_token = 0.00001
        total_cost = total_tokens * cost_per_token
        
        metrics["total_tokens"] = float(total_tokens)
        metrics["total_cost"] = total_cost
        
        # Quality metrics from verifier
        if episode.verifier_result:
            metrics["label_correct"] = 1.0 if episode.verifier_result.label_correct else 0.0
            metrics["evidence_provided"] = 1.0 if episode.verifier_result.evidence_provided else 0.0
            metrics["evidence_match_score"] = episode.verifier_result.evidence_match_score
        
        return metrics
    
    def _compute_payoff(self, episode: Episode) -> float:
        """
        Compute payoff for episode.
        
        Payoff = quality - λ * cost - μ * penalty
        
        Where:
        - quality: weighted combination of accuracy and evidence match
        - cost: normalized token cost
        - penalty: penalty for protocol violations
        """
        # Quality score
        label_correct = episode.metrics.get("label_correct", 0.0)
        evidence_match = episode.metrics.get("evidence_match_score", 0.0)
        evidence_provided = episode.metrics.get("evidence_provided", 0.0)
        
        # Quality = 0.6 * accuracy + 0.3 * evidence_match + 0.1 * evidence_provided
        quality = 0.6 * label_correct + 0.3 * evidence_match + 0.1 * evidence_provided
        
        # Cost (normalized)
        cost = episode.metrics.get("total_cost", 0.0)
        
        # Penalty for protocol violations
        penalty = 0.0
        if not evidence_provided:
            # Major penalty for not providing evidence in P1 protocol
            penalty = 1.0
        elif evidence_match < 0.3 and label_correct == 0:
            # Penalty for poor evidence with wrong label
            penalty = 0.5
        
        # Compute payoff
        payoff = quality - self.lambda_cost * cost - self.mu_penalty * penalty
        
        return payoff
    
    def execute_sync(self, task: Task, deviation_type: str = "honest") -> Episode:
        """Synchronous wrapper for execute."""
        return asyncio.run(self.execute(task, deviation_type))
