"""Local LLM client implementation."""
from typing import List, Dict, Any, Optional

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.ports.llm_client import LLMClient


class LocalClient(LLMClient):
    """LLM client for local models using transformers or vllm."""
    
    def __init__(
        self,
        model_path: str,
        use_vllm: bool = False,
        device: str = "cuda"
    ):
        """
        Initialize local model client.
        
        Args:
            model_path: Path or name of the model (e.g., "meta-llama/Llama-2-7b-chat-hf")
            use_vllm: If True, use vLLM for faster inference (requires vllm package)
            device: Device to use ("cuda", "cpu", "mps")
        """
        self.model_path = model_path
        self.use_vllm = use_vllm
        self.device = device
        
        if use_vllm:
            self._init_vllm()
        else:
            self._init_transformers()
    
    def _init_transformers(self):
        """Initialize using HuggingFace transformers."""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            print(f"Loading model {self.model_path} with transformers...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None
            )
            
            if self.device != "cuda":
                self.model = self.model.to(self.device)
            
            self.model.eval()
            
            print("Model loaded successfully")
        
        except ImportError:
            raise ImportError("transformers and torch are required for local models. Install with: pip install transformers torch")
    
    def _init_vllm(self):
        """Initialize using vLLM."""
        try:
            from vllm import LLM, SamplingParams
            
            print(f"Loading model {self.model_path} with vLLM...")
            
            self.llm = LLM(model=self.model_path)
            
            print("Model loaded successfully")
        
        except ImportError:
            raise ImportError("vllm is required for vLLM backend. Install with: pip install vllm")
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a response using local model."""
        if self.use_vllm:
            return self._generate_vllm(messages, temperature, max_tokens, **kwargs)
        else:
            return self._generate_transformers(messages, temperature, max_tokens, **kwargs)
    
    def _generate_transformers(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """Generate using transformers."""
        import torch
        
        # Convert messages to prompt (simple concatenation for now)
        prompt = self._format_messages(messages)
        
        # Tokenize
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        prompt_tokens = inputs.input_ids.shape[1]
        
        # Generate
        max_new_tokens = max_tokens if max_tokens else 512
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs.input_ids,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                **kwargs
            )
        
        # Decode
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Remove prompt from generated text
        response_text = generated_text[len(prompt):].strip()
        
        completion_tokens = outputs.shape[1] - prompt_tokens
        
        return {
            "content": response_text,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            "model": self.model_path
        }
    
    def _generate_vllm(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """Generate using vLLM."""
        from vllm import SamplingParams
        
        # Convert messages to prompt
        prompt = self._format_messages(messages)
        
        # Set sampling parameters
        sampling_params = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens if max_tokens else 512,
            **kwargs
        )
        
        # Generate
        outputs = self.llm.generate([prompt], sampling_params)
        
        # Extract response
        output = outputs[0]
        response_text = output.outputs[0].text
        
        # Estimate token counts (vLLM doesn't provide exact counts in simple API)
        prompt_tokens = len(prompt.split()) * 1.3  # rough estimate
        completion_tokens = len(response_text.split()) * 1.3
        
        return {
            "content": response_text,
            "usage": {
                "prompt_tokens": int(prompt_tokens),
                "completion_tokens": int(completion_tokens),
                "total_tokens": int(prompt_tokens + completion_tokens)
            },
            "model": self.model_path
        }
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages into a prompt string."""
        # Simple formatting for chat models
        formatted = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                formatted += f"System: {content}\n\n"
            elif role == "user":
                formatted += f"User: {content}\n\n"
            elif role == "assistant":
                formatted += f"Assistant: {content}\n\n"
        
        formatted += "Assistant: "
        return formatted
    
    def get_model_name(self) -> str:
        """Return the model name."""
        return self.model_path
