"""Self-Refine baseline implementation."""
import re
import uuid

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


class SelfRefine(BaseBaseline):
    """
    Self-Refine baseline.
    
    Implementation of "Self-Refine: Iterative Refinement with Self-Feedback" (Madaan et al., 2023).
    
    Method:
    1. Draft: Generate initial prediction
    2. Critique: Model critiques its own answer
    3. Revise: Generate improved answer based on critique
    4. Repeat for N rounds
    
    This is a strong baseline because:
    - Iterative refinement without external feedback
    - Self-correction mechanism
    - Comparable cost to multi-agent protocols
    """
    
    def __init__(self, llm_client, num_rounds: int = 2, temperature: float = 0.3, **kwargs):
        """
        Initialize Self-Refine baseline.
        
        Args:
            llm_client: LLM client for predictions
            num_rounds: Number of refinement rounds
            temperature: Temperature for generation
        """
        super().__init__(llm_client, num_rounds=num_rounds, temperature=temperature, **kwargs)
        self.num_rounds = num_rounds
        self.temperature = temperature
    
    def get_baseline_id(self) -> str:
        """Get baseline identifier."""
        return f"self_refine_r{self.num_rounds}"
    
    async def execute(self, task: Task) -> Episode:
        """
        Execute Self-Refine on a task.
        
        Args:
            task: Task to solve
            
        Returns:
            Episode with refined prediction
        """
        episode_id = f"sr_{task.task_id}_{uuid.uuid4().hex[:8]}"
        
        transcript = []
        current_answer = None
        
        # Initial draft
        draft_prompt = self._create_draft_prompt(task)
        draft_response = await self.llm_client.generate(
            messages=[
                {"role": "system", "content": self.get_draft_system_prompt()},
                {"role": "user", "content": draft_prompt}
            ],
            temperature=self.temperature
        )
        
        current_answer = draft_response
        
        transcript.append(Message(
            role=AgentRole.SENDER,
            content=draft_prompt,
            evidence=[],
            metadata={"stage": "draft"}
        ))
        transcript.append(Message(
            role=AgentRole.SENDER,
            content=draft_response,
            evidence=[],
            metadata={"stage": "draft"}
        ))
        
        # Refinement rounds
        for round_num in range(self.num_rounds):
            # Critique
            critique_prompt = self._create_critique_prompt(task, current_answer)
            critique_response = await self.llm_client.generate(
                messages=[
                    {"role": "system", "content": self.get_critique_system_prompt()},
                    {"role": "user", "content": critique_prompt}
                ],
                temperature=self.temperature
            )
            
            transcript.append(Message(
                role=AgentRole.RECEIVER,
                content=critique_prompt,
                evidence=[],
                metadata={"stage": "critique", "round": round_num}
            ))
            transcript.append(Message(
                role=AgentRole.SENDER,
                content=critique_response,
                evidence=[],
                metadata={"stage": "critique", "round": round_num}
            ))
            
            # Revise
            revise_prompt = self._create_revise_prompt(task, current_answer, critique_response)
            revise_response = await self.llm_client.generate(
                messages=[
                    {"role": "system", "content": self.get_revise_system_prompt()},
                    {"role": "user", "content": revise_prompt}
                ],
                temperature=self.temperature
            )
            
            current_answer = revise_response
            
            transcript.append(Message(
                role=AgentRole.RECEIVER,
                content=revise_prompt,
                evidence=[],
                metadata={"stage": "revise", "round": round_num}
            ))
            transcript.append(Message(
                role=AgentRole.SENDER,
                content=revise_response,
                evidence=[],
                metadata={"stage": "revise", "round": round_num}
            ))
        
        # Extract final prediction
        final_prediction = self._extract_prediction(current_answer)
        
        # Create verification result
        label_correct = (final_prediction == task.label)
        
        verifier_result = VerificationResult(
            label_correct=label_correct,
            evidence_provided=False,  # Self-refine doesn't explicitly provide evidence
            evidence_match_score=0.0,
            predicted_label=str(final_prediction),
            additional_info={
                "num_rounds": self.num_rounds,
                "refinement_steps": self.num_rounds * 2 + 1  # draft + (critique + revise) * rounds
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
                "num_rounds": self.num_rounds,
                "total_turns": len(transcript)
            },
            payoff=0.0  # Will be calculated by payoff calculator
        )
        
        return episode
    
    def _create_draft_prompt(self, task: Task) -> str:
        """Create initial draft prompt."""
        return f"""Please analyze the following claim and provide your initial assessment:

Claim: {task.claim}

Provide your reasoning and assessment."""
    
    def _create_critique_prompt(self, task: Task, current_answer: str) -> str:
        """Create critique prompt."""
        return f"""Review your previous assessment of this claim:

Claim: {task.claim}

Your previous assessment:
{current_answer}

Now critique your own reasoning:
- What are potential weaknesses in your argument?
- What evidence might contradict your assessment?
- What assumptions did you make?
- How confident should you be?

Provide a constructive critique."""
    
    def _create_revise_prompt(self, task: Task, previous_answer: str, critique: str) -> str:
        """Create revision prompt."""
        return f"""Based on the critique, revise your assessment:

Claim: {task.claim}

Your previous assessment:
{previous_answer}

Critique of your assessment:
{critique}

Now provide an improved, revised assessment that addresses the critique.

Format:
Assessment: [SUPPORTS/REFUTES/NOT ENOUGH INFO]
Reasoning: [Your improved reasoning]"""
    
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
        
        # Look for any mention of labels (prefer later mentions as they're more refined)
        last_supports = response_upper.rfind("SUPPORTS")
        last_refutes = response_upper.rfind("REFUTES")
        last_nei = response_upper.rfind("NOT ENOUGH INFO")
        
        positions = {
            "SUPPORTS": last_supports,
            "REFUTES": last_refutes,
            "NOT ENOUGH INFO": last_nei
        }
        
        # Get the label that appears last
        valid_positions = {k: v for k, v in positions.items() if v != -1}
        if valid_positions:
            last_label = max(valid_positions, key=valid_positions.get)
            return FEVERLabel.from_string(last_label)
        
        # Default to NOT_ENOUGH_INFO if unclear
        return FEVERLabel.NOT_ENOUGH_INFO
    
    def get_draft_system_prompt(self) -> str:
        """Get system prompt for draft phase."""
        return """You are an AI assistant helping to verify factual claims.

Analyze the claim carefully and provide your initial assessment with reasoning."""
    
    def get_critique_system_prompt(self) -> str:
        """Get system prompt for critique phase."""
        return """You are a critical reviewer analyzing your own reasoning.

Identify potential weaknesses, assumptions, and areas for improvement in your previous assessment."""
    
    def get_revise_system_prompt(self) -> str:
        """Get system prompt for revision phase."""
        return """You are refining your previous assessment based on critique.

Provide an improved, more accurate assessment that addresses the identified issues."""
