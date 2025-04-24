import re
import logging
from typing import List, Dict, Any, Optional
from vllm import LLM, SamplingParams

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VLLMModelHandler:
    """
    VLLM-based implementation of model handling - optimized for NVIDIA GPUs
    """
    
    def __init__(self, model_name: str, use_cpu: bool = False):
        """
        Initialize the VLLM model handler
        
        Args:
            model_name: Name of the model to load
            use_cpu: Whether to force CPU usage (slower, but works without GPU)
        """
        logger.info(f"Initializing VLLM model handler for {model_name}")
        
        if use_cpu:
            logger.info("Using CPU for VLLM (will be slower)")
            # CPU-only configuration for vllm
            self.llm = LLM(
                model=model_name,
                tensor_parallel_size=1,
                trust_remote_code=True,
                gpu_memory_utilization=0.0,  # 0.0 to avoid using GPU
                max_model_len=10000,
                disable_log_stats=True,
                dtype="float16",
                cpu_only=True     # Force CPU-only mode
            )
        else:
            # Standard initialization for systems with GPU
            logger.info("Using GPU for VLLM")
            self.llm = LLM(
                model=model_name,
                tensor_parallel_size=1,
                trust_remote_code=True,
                gpu_memory_utilization=0.96,
                max_model_len=10000,
                disable_log_stats=True,
                dtype="float16"
            )
            
        # Initialize sampling parameters for generation
        self.sampling_params = SamplingParams(
            temperature=0.5,
            max_tokens=10000,
            n=1,
            top_p=1,
            skip_special_tokens=False,
            spaces_between_special_tokens=False,
            stop_token_ids=[151668, 151672]  # </search>, </answer>
        )
        
    def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Generate a response from the model
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters for generation
                temperature: Float temperature for generation
                max_tokens: Maximum number of tokens to generate
                
        Returns:
            Dictionary with generated text and metadata
        """
        # Override sampling parameters if provided
        if 'temperature' in kwargs or 'max_tokens' in kwargs:
            params = SamplingParams(
                temperature=kwargs.get('temperature', self.sampling_params.temperature),
                max_tokens=kwargs.get('max_tokens', self.sampling_params.max_tokens),
                n=self.sampling_params.n,
                top_p=self.sampling_params.top_p,
                skip_special_tokens=self.sampling_params.skip_special_tokens,
                spaces_between_special_tokens=self.sampling_params.spaces_between_special_tokens,
                stop_token_ids=self.sampling_params.stop_token_ids
            )
        else:
            params = self.sampling_params
            
        # Generate text with VLLM
        output = self.llm.chat(messages, sampling_params=params)
        
        # Extract the text from VLLM output format
        generated_text = output[0].outputs[0].text
        
        return {
            "text": generated_text,
            "backend": "vllm"
        }
        
    def extract_sections(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract sections from the generated text
        
        Args:
            text: The generated text to extract sections from
            
        Returns:
            Dictionary with extracted sections
        """
        thinking = re.search(r'<think>(.*?)</think>', text, re.DOTALL)
        search = re.search(r'<search>(.*?)</search>', text, re.DOTALL)
        answer = re.search(r'<answer>(.*?)</answer>', text, re.DOTALL)
        
        return {
            "thinking": thinking.group(1) if thinking else None,
            "search_query": search.group(1) if search else None,
            "answer": answer.group(1) if answer else None
        } 
