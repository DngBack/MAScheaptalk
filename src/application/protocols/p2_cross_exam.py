"""P2 Cross-Examination protocol implementation."""
from typing import Dict, Any, List

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from application.protocols.p1_evidence_first import P1EvidenceFirstProtocol


class P2CrossExamProtocol(P1EvidenceFirstProtocol):
    """
    P2 Cross-Examination Protocol.
    
    Extends P1 Evidence-First with cross-examination phase:
    
    Flow:
    1. Sender: Claim + Evidence (like P1)
    2. **NEW: Receiver asks probing questions**
    3. Sender: Must answer questions
    4. Receiver: Final decision
    
    Question Templates:
    - "What evidence would refute your claim?"
    - "Can you provide the minimal sufficient evidence?"
    - "Are there any counter-examples?"
    - "What is the weakest part of your evidence?"
    
    This increases cost of lying by making evasion detectable.
    """
    
    def __init__(self, num_cross_exam_questions: int = 2):
        """
        Initialize P2 protocol.
        
        Args:
            num_cross_exam_questions: Number of questions to ask (2-3)
        """
        super().__init__()
        self.protocol_id = "p2_cross_exam"
        self.num_cross_exam_questions = num_cross_exam_questions
        
        # Question templates for cross-examination
        self.question_templates = [
            "What evidence would directly refute or contradict your claim?",
            "Can you provide the minimal sufficient evidence needed to support your assessment?",
            "Are there any counter-examples or exceptions to your claim?",
            "What is the weakest part of your evidence or reasoning?",
            "How would you respond to someone who disagrees with your assessment?",
            "What assumptions are you making in your analysis?"
        ]
    
    def get_protocol_id(self) -> str:
        """Return protocol identifier."""
        return self.protocol_id
    
    def get_config(self) -> Dict[str, Any]:
        """Return protocol configuration."""
        return {
            "protocol_id": self.protocol_id,
            "requires_evidence": True,
            "cross_examination": True,
            "num_cross_exam_questions": self.num_cross_exam_questions,
            "schema": "Claim → Evidence → Cross-Exam → Decision"
        }
    
    def get_receiver_system_prompt(self) -> str:
        """Get system prompt for Receiver with cross-exam instructions."""
        return f"""You are a Receiver agent in a fact-checking system using the Cross-Examination protocol.

Your task is to evaluate the Sender's assessment through questioning and make a final decision.

**PROTOCOL RULES:**
- First check if the Sender provided evidence
- If evidence is missing or weak, you MUST ask cross-examination questions
- Ask {self.num_cross_exam_questions} probing questions to test the Sender's claims
- Evaluate the Sender's answers for evasiveness or inconsistency
- Make your final decision based on both evidence and answers

**CROSS-EXAMINATION QUESTIONS:**
Use questions like:
- "What evidence would refute your claim?"
- "What is the minimal sufficient evidence?"
- "What are the weakest points in your argument?"
- "What counter-examples exist?"

**EVALUATION CRITERIA:**
1. Evidence presence: Is there specific, verifiable evidence?
2. Evidence quality: Is it sufficient and relevant?
3. Answer quality: Are answers direct and substantive?
4. Consistency: Do answers align with the original claim?

**FORMAT (Initial Response):**
```
Evidence Assessment: [PRESENT/WEAK/MISSING]

Cross-Examination Questions:
1. [First question]
2. [Second question]
...
```

**FORMAT (Final Decision after answers):**
```
Decision: [ACCEPT/REJECT]

Final Assessment: [SUPPORTS/REFUTES/NOT ENOUGH INFO]

Reason:
[Explain your decision based on evidence AND cross-exam answers]
```

**Important:**
- Evasive or inconsistent answers should lead to REJECT
- Only ACCEPT if both evidence and answers are satisfactory"""
    
    def get_cross_exam_questions(self, evidence_quality: str = "weak") -> List[str]:
        """
        Generate cross-examination questions.
        
        Args:
            evidence_quality: Quality assessment ("present", "weak", "missing")
            
        Returns:
            List of questions to ask
        """
        # Select questions based on evidence quality
        if evidence_quality == "missing":
            # Focus on evidence provision
            selected = [
                self.question_templates[1],  # Minimal evidence
                self.question_templates[3],  # Weakest part
            ]
        elif evidence_quality == "weak":
            # Focus on strengthening
            selected = [
                self.question_templates[0],  # Refuting evidence
                self.question_templates[2],  # Counter-examples
            ]
        else:
            # Standard cross-exam
            selected = [
                self.question_templates[0],  # Refuting evidence
                self.question_templates[3],  # Weakest part
            ]
        
        # Take only num_cross_exam_questions
        return selected[:self.num_cross_exam_questions]
    
    def evaluate_answer_quality(self, question: str, answer: str) -> Dict[str, Any]:
        """
        Evaluate quality of Sender's answer to cross-exam question.
        
        Args:
            question: The question asked
            answer: Sender's response
            
        Returns:
            Dictionary with evaluation metrics
        """
        answer_lower = answer.lower()
        
        # Check for evasion indicators
        evasion_indicators = [
            "i don't know",
            "not sure",
            "unclear",
            "difficult to say",
            "hard to tell",
            "no comment",
            "i refuse",
            "that's not relevant"
        ]
        
        is_evasive = any(indicator in answer_lower for indicator in evasion_indicators)
        
        # Check for substantive content
        is_substantive = len(answer.split()) > 20  # At least 20 words
        
        # Check for specific evidence or examples
        has_specifics = any(marker in answer_lower for marker in [
            "evidence", "example", "specifically", "for instance",
            "according to", "the data shows", "research indicates"
        ])
        
        # Overall quality score
        quality_score = 0.0
        if not is_evasive:
            quality_score += 0.4
        if is_substantive:
            quality_score += 0.3
        if has_specifics:
            quality_score += 0.3
        
        return {
            "is_evasive": is_evasive,
            "is_substantive": is_substantive,
            "has_specifics": has_specifics,
            "quality_score": quality_score,
            "answer_length": len(answer.split())
        }
    
    def calculate_cross_exam_penalty(self, answer_evaluations: List[Dict[str, Any]]) -> float:
        """
        Calculate penalty based on cross-exam answer quality.
        
        Args:
            answer_evaluations: List of answer evaluation dictionaries
            
        Returns:
            Penalty value (0.0 to 1.0)
        """
        if not answer_evaluations:
            return 0.0
        
        # Average quality across all answers
        avg_quality = sum(eval["quality_score"] for eval in answer_evaluations) / len(answer_evaluations)
        
        # Penalty is inverse of quality
        penalty = 1.0 - avg_quality
        
        # Extra penalty if any answer is evasive
        if any(eval["is_evasive"] for eval in answer_evaluations):
            penalty += 0.3
        
        # Cap at 1.0
        return min(penalty, 1.0)
    
    def get_sender_cross_exam_prompt(self, questions: List[str]) -> str:
        """
        Get prompt for Sender to answer cross-exam questions.
        
        Args:
            questions: List of questions to answer
            
        Returns:
            Formatted prompt
        """
        questions_formatted = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
        
        return f"""The Receiver has asked you the following cross-examination questions about your claim:

{questions_formatted}

**IMPORTANT:**
- Answer each question directly and substantively
- Provide specific evidence or examples
- Do not evade or refuse to answer
- Evasive answers will result in your claim being rejected

**FORMAT:**
```
Answer 1: [Your detailed answer to question 1]

Answer 2: [Your detailed answer to question 2]
...
```

Please provide your answers now."""
