"""OpenAI LLM client implementation."""
import os
from typing import List, Dict, Any, Optional
import openai

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.ports.llm_client import LLMClient


class OpenAIClient(LLMClient):
    """LLM client for OpenAI models."""
    
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None
    ):
        """
        Initialize OpenAI client.
        
        Args:
            model: Model name (e.g., "gpt-4o", "gpt-4", "gpt-3.5-turbo")
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
        """
        self.model = model
        
        # Set API key
        if api_key:
            openai.api_key = api_key
        elif "OPENAI_API_KEY" in os.environ:
            openai.api_key = os.environ["OPENAI_API_KEY"]
        else:
            raise ValueError("OpenAI API key not provided and OPENAI_API_KEY not set in environment")
        
        self.client = openai.OpenAI(api_key=openai.api_key)
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a response using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # Extract response
            content = response.choices[0].message.content
            
            # Extract usage info
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            return {
                "content": content,
                "usage": usage,
                "model": response.model
            }
        
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            raise
    
    def get_model_name(self) -> str:
        """Return the model name."""
        return self.model
