import re
import torch
import logging
import sys
import io
from typing import List, Dict, Any, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
from app.model_progress import progress_monitor, monitor_stderr_for_progress

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Capture stderr to monitor loading progress
class StderrCapturer:
    def __init__(self):
        self.orig_stderr = sys.stderr
        self.captured_text = []
        
    def __enter__(self):
        sys.stderr = self
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr = self.orig_stderr
        
    def write(self, text):
        self.orig_stderr.write(text)
        self.captured_text.append(text)
        # Check for progress in the line
        monitor_stderr_for_progress(text)
        
    def flush(self):
        self.orig_stderr.flush()

class TransformersModelHandler:
    """
    Transformers-based implementation of model handling - optimized for M1 Macs
    """
    
    def __init__(self, model_name: str):
        """
        Initialize the Transformers model handler
        
        Args:
            model_name: Name of the model to load
        """
        logger.info(f"Initializing Transformers model handler for {model_name}")
        
        # Reset the progress monitor before loading
        progress_monitor.reset()
        
        # Determine the best device to use
        if torch.backends.mps.is_available():
            logger.info("Using MPS (Metal) for acceleration on M1 Mac")
            self.device = torch.device("mps")
            device_map = "auto"  # Use auto device mapping for better memory management
        elif torch.cuda.is_available():
            logger.info("Using CUDA for acceleration")
            self.device = torch.device("cuda")
            device_map = "auto"  # Use auto device mapping for better memory management
        else:
            logger.info("Using CPU for inference (slower)")
            self.device = torch.device("cpu")
            device_map = None  # CPU doesn't need device mapping
            
        # Load model and tokenizer with stderr capture
        try:
            with StderrCapturer():
                logger.info("Loading tokenizer...")
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                
                logger.info("Loading model...")
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16 if self.device.type != "cpu" else torch.float32,
                    device_map=device_map,
                    low_cpu_mem_usage=True
                )
            
            # Mark loading as complete
            progress_monitor.mark_loading_complete()
            logger.info(f"Successfully loaded model on {self.device}")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise RuntimeError(f"Failed to load model: {e}")
            
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages into a prompt the model can understand"""
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                prompt += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                prompt += f"<|im_start|>assistant\n{content}<|im_end|>\n"
            else:
                prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
        
        # Add the final assistant prefix to prime the generation
        prompt += "<|im_start|>assistant\n"
        return prompt
        
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
        try:
            # Format messages into a prompt
            prompt = self._format_messages(messages)
            
            # Set generation parameters
            temperature = kwargs.get('temperature', 0.5)
            max_new_tokens = kwargs.get('max_tokens', 1000)
            
            # Tokenize and generate
            inputs = self.tokenizer(prompt, return_tensors="pt", padding=True)
            
            # Explicitly create attention mask if not present
            if 'attention_mask' not in inputs:
                # Create attention mask (1 for all tokens)
                inputs['attention_mask'] = torch.ones_like(inputs['input_ids'])
                
            # Move inputs to the correct device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate with appropriate parameters
            with torch.no_grad():
                outputs = self.model.generate(
                    input_ids=inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    do_sample=temperature > 0,
                    top_p=0.95,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode the outputs
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
            
            # Extract the generated text after the prompt
            response_text = generated_text[len(prompt):].strip()
            
            return {
                "text": response_text,
                "backend": "transformers"
            }
        except Exception as e:
            logger.error(f"Error during generation: {str(e)}")
            raise RuntimeError(f"Failed to generate response: {e}")
        
    def extract_sections(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract sections from the generated text
        
        Args:
            text: The generated text to extract sections from
            
        Returns:
            Dictionary with extracted sections
        """
        logger.info(f"Extracting sections from text of length: {len(text)}")
        
        # More robust regex patterns that handle whitespace and newlines
        thinking_pattern = r'<think>\s*(.*?)\s*</think>'
        search_pattern = r'<search>\s*(.*?)\s*</search>'
        answer_pattern = r'<answer>\s*(.*?)\s*</answer>'
        
        # Extract sections
        thinking = re.search(thinking_pattern, text, re.DOTALL)
        search = re.search(search_pattern, text, re.DOTALL)
        answer = re.search(answer_pattern, text, re.DOTALL)
        
        # Log the extraction results
        if thinking:
            logger.info("Found <think> section")
        if search:
            logger.info("Found <search> section")
        if answer:
            logger.info("Found <answer> section")
        
        # If no sections are found, check if there might be malformed tags
        if not thinking and not search and not answer:
            logger.warning("No sections found in response, checking for malformed tags")
            logger.debug(f"Response text: {text}")
            
            # Look for partial tags
            has_think_start = "<think>" in text
            has_think_end = "</think>" in text
            has_search_start = "<search>" in text
            has_search_end = "</search>" in text
            has_answer_start = "<answer>" in text
            has_answer_end = "</answer>" in text
            
            if has_think_start or has_think_end or has_search_start or has_search_end or has_answer_start or has_answer_end:
                logger.warning(f"Detected partial tags: think[{has_think_start},{has_think_end}], search[{has_search_start},{has_search_end}], answer[{has_answer_start},{has_answer_end}]")
        
        return {
            "thinking": thinking.group(1).strip() if thinking else None,
            "search_query": search.group(1).strip() if search else None,
            "answer": answer.group(1).strip() if answer else None
        } 
