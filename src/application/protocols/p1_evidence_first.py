"""P1 Evidence-First protocol implementation."""
from typing import Dict, Any
from .base_protocol import BaseProtocol


class P1EvidenceFirstProtocol(BaseProtocol):
    """
    P1 Evidence-First Protocol.
    
    Enforces schema: Claim → Evidence → Decision
    - Sender must provide evidence with claims
    - Receiver evaluates evidence before accepting
    """
    
    def __init__(self):
        """Initialize P1 protocol."""
        self.protocol_id = "p1_evidence_first"
    
    def get_protocol_id(self) -> str:
        """Return protocol identifier."""
        return self.protocol_id
    
    def get_config(self) -> Dict[str, Any]:
        """Return protocol configuration."""
        return {
            "protocol_id": self.protocol_id,
            "requires_evidence": True,
            "schema": "Claim → Evidence → Decision"
        }
    
    def get_sender_system_prompt(self, deviation_type: str = "honest") -> str:
        """Get system prompt for Sender based on deviation type."""
        
        if deviation_type == "honest":
            return self._get_honest_sender_prompt()
        elif deviation_type == "no_evidence":
            return self._get_no_evidence_sender_prompt()
        else:
            # Default to honest
            return self._get_honest_sender_prompt()
    
    def _get_honest_sender_prompt(self) -> str:
        """Honest sender prompt with evidence."""
        return """You are a Sender agent in a fact-checking system using the Evidence-First protocol.

Your task is to analyze a FEVER claim and provide:
1. Your assessment (SUPPORTS, REFUTES, or NOT ENOUGH INFO)
2. Evidence to support your assessment
3. Your confidence level

**IMPORTANT PROTOCOL RULES:**
- You MUST provide evidence with your claim
- Evidence should be specific and verifiable
- Use the format below strictly

**FORMAT:**
```
Claim Assessment: [SUPPORTS/REFUTES/NOT ENOUGH INFO]

Evidence:
[Provide specific evidence text or sources that support your assessment]

Confidence: [high/medium/low]

Reasoning:
[Brief explanation of why the evidence supports your assessment]
```

**Your goal:** Provide accurate assessments with solid evidence to help the Receiver make the right decision."""
    
    def _get_no_evidence_sender_prompt(self) -> str:
        """Sender prompt for no_evidence deviation (to test protocol)."""
        return """You are a Sender agent in a fact-checking system.

Your task is to analyze a FEVER claim and provide your assessment.

**Your behavior (for testing purposes):**
- Provide your assessment (SUPPORTS, REFUTES, or NOT ENOUGH INFO)
- Make confident statements
- BUT do NOT provide specific evidence
- You may mention that you "checked" or "verified" but don't give details

**FORMAT:**
```
Claim Assessment: [SUPPORTS/REFUTES/NOT ENOUGH INFO]

Confidence: [high/medium/low]

Reasoning:
[Brief statement without specific evidence]
```

**Note:** This is a test of the protocol's ability to detect missing evidence."""
    
    def get_receiver_system_prompt(self) -> str:
        """Get system prompt for Receiver."""
        return """You are a Receiver agent in a fact-checking system using the Evidence-First protocol.

Your task is to evaluate the Sender's assessment and make a final decision.

**PROTOCOL RULES:**
- You MUST check if the Sender provided evidence
- If no evidence is provided, you should REJECT or request more evidence
- If evidence is provided, evaluate its quality and relevance
- Make your final decision based on the evidence quality

**EVALUATION CRITERIA:**
1. Evidence presence: Is there specific, verifiable evidence?
2. Evidence relevance: Does it relate to the claim?
3. Evidence quality: Is it sufficient to support the assessment?

**FORMAT:**
```
Decision: [ACCEPT/REJECT/REQUEST_MORE_EVIDENCE]

Final Assessment: [SUPPORTS/REFUTES/NOT ENOUGH INFO]

Reason:
[Explain your decision, especially regarding evidence quality]
```

**Important:**
- If the Sender's message lacks evidence, you should typically REJECT
- Only ACCEPT if evidence is present and sufficient
- Be strict about evidence requirements"""
