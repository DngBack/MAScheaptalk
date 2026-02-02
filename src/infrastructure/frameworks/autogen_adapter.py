"""AutoGen framework adapter."""
from typing import List, Dict, Any, Optional
from datetime import datetime

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import ChatMessage, TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.entities.message import Message
from domain.entities.task import Task
from domain.value_objects.role import AgentRole
from application.protocols.base_protocol import BaseProtocol


class AutoGenAdapter:
    """Adapter for AutoGen framework to run protocols."""
    
    def __init__(
        self,
        protocol: BaseProtocol,
        model_name: str = "gpt-4o",
        api_key: Optional[str] = None
    ):
        """
        Initialize AutoGen adapter.
        
        Args:
            protocol: Protocol to use for conversation
            model_name: Model name for AutoGen agents
            api_key: OpenAI API key (if None, uses environment variable)
        """
        self.protocol = protocol
        self.model_name = model_name
        self.api_key = api_key
    
    async def run_conversation(
        self,
        task: Task,
        deviation_type: str = "honest",
        max_turns: int = 2
    ) -> tuple[List[Message], Dict[str, Any]]:
        """
        Run a conversation between Sender and Receiver agents.
        
        Args:
            task: Task to discuss
            deviation_type: Deviation strategy for Sender
            max_turns: Maximum number of conversation turns
            
        Returns:
            Tuple of (transcript, usage_info)
        """
        # Create model client
        model_client = OpenAIChatCompletionClient(
            model=self.model_name,
            api_key=self.api_key
        )
        
        # Create agents
        sender_agent = AssistantAgent(
            name="Sender",
            model_client=model_client,
            system_message=self.protocol.get_sender_system_prompt(deviation_type)
        )
        
        receiver_agent = AssistantAgent(
            name="Receiver",
            model_client=model_client,
            system_message=self.protocol.get_receiver_system_prompt()
        )
        
        # Start conversation
        transcript = []
        total_tokens = 0
        
        # Sender's initial message with the claim
        sender_prompt = f"""Please analyze the following claim:

Claim: "{task.claim}"

Provide your assessment following the protocol format."""
        
        # Get Sender's response
        sender_response = await sender_agent.on_messages(
            [TextMessage(content=sender_prompt, source="user")],
            cancellation_token=None
        )
        
        sender_message = Message(
            role=AgentRole.SENDER,
            content=sender_response.chat_message.content,
            evidence=[],
            timestamp=datetime.now(),
            metadata={}
        )
        transcript.append(sender_message)
        
        # Track tokens if available
        if hasattr(sender_response, 'usage'):
            total_tokens += getattr(sender_response.usage, 'total_tokens', 0)
        
        # Receiver's response
        receiver_prompt = f"""The Sender has provided the following assessment:

{sender_response.chat_message.content}

Please evaluate this according to the protocol and make your decision."""
        
        receiver_response = await receiver_agent.on_messages(
            [TextMessage(content=receiver_prompt, source="user")],
            cancellation_token=None
        )
        
        receiver_message = Message(
            role=AgentRole.RECEIVER,
            content=receiver_response.chat_message.content,
            evidence=[],
            timestamp=datetime.now(),
            metadata={}
        )
        transcript.append(receiver_message)
        
        # Track tokens
        if hasattr(receiver_response, 'usage'):
            total_tokens += getattr(receiver_response.usage, 'total_tokens', 0)
        
        usage_info = {
            "total_tokens": total_tokens,
            "model": self.model_name
        }
        
        return transcript, usage_info
