from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import re
import platform

class SimpleReasonerModel:
    def __init__(self):
        # Check if this is Apple Silicon (M1/M2/M3)
        is_apple_silicon = (platform.system() == "Darwin" and platform.processor() == "arm")
        
        # Check for MPS on Apple Silicon
        mps_available = is_apple_silicon and hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
        
        # Set device based on available hardware
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
            self.dtype = torch.float16  # Use half precision on GPU
            print(f"Using CUDA device: {torch.cuda.get_device_name(0)}")
        elif mps_available:
            self.device = torch.device("mps")
            self.dtype = torch.float16  # Use half precision on MPS too
            print(f"Using Apple Metal Performance Shaders (MPS) for GPU acceleration")
        else:
            self.device = torch.device("cpu")
            self.dtype = torch.float32
            print("⚠️ Using CPU (will be slower)")
            
        model_name = "tossowski/MedAgentReasoner-3B-Chat"
        print(f"Loading model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Set up configuration for model loading
        config = {
            "torch_dtype": self.dtype,
            "low_cpu_mem_usage": True
        }
        
        # Only use device_map on CUDA (not on MPS)
        if torch.cuda.is_available():
            config["device_map"] = "auto"
            print("Loading model with CUDA device_map...")
            self.model = AutoModelForCausalLM.from_pretrained(model_name, **config)
        else:
            print(f"Loading model and moving to {self.device}...")
            self.model = AutoModelForCausalLM.from_pretrained(model_name, **config)
            # Explicitly move the model to device if using MPS or CPU
            self.model = self.model.to(self.device)
        
        # Verify model device
        print(f"Model is on device: {next(self.model.parameters()).device}")
    
    def get_response(self, prompt, previous_context="", max_tokens=150):
        """Generate a response from the model"""
        # If we have previous context, add it to the prompt
        full_prompt = previous_context + prompt if previous_context else prompt
        
        # Debug: Show what we're sending to the model
        print(f"\nDEBUG: Generating response to prompt:")
        print(f"{prompt}")
        
        # Tokenize and move to correct device
        inputs = self.tokenizer(full_prompt, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=0.7,
                do_sample=True,
                # Stop at search or answer tokens to avoid generating too much at once
                stopping_criteria=None
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
        # Remove the input prompt from the response
        result = response.replace(full_prompt, "").strip()
        
        # Debug: Show the raw result
        print(f"\nDEBUG: Raw model output:")
        print(f"{result}")
        
        return result
    
    def extract_first_search_query(self, response):
        """Extract the first search query from the model's response"""
        if "<search>" in response and "</search>" in response:
            search_matches = re.findall(r'<search>(.*?)</search>', response, re.DOTALL)
            if search_matches:
                return search_matches[0].strip()
        return None
    
    def extract_answer(self, response):
        """Extract final answer from the model's response"""
        if "<answer>" in response and "</answer>" in response:
            answers = re.findall(r'<answer>(.*?)</answer>', response, re.DOTALL)
            if answers:
                return answers[0].strip()
        return None
    
    def extract_thinking(self, response):
        """Extract the thinking part from the model's response"""
        if "<think>" in response and "</think>" in response:
            thinking = re.findall(r'<think>(.*?)</think>', response, re.DOTALL)
            if thinking:
                return thinking[0].strip()
        return None

def interactive_session():
    """Run an interactive session with the model"""
    print("=" * 80)
    print("INTERACTIVE MEDICAL REASONER SESSION (GPU/MPS-ACCELERATED)")
    print("=" * 80)
    
    # Initialize model
    model = SimpleReasonerModel()
    
    # Get the initial prompt from the user
    print("\nEnter your medical question:")
    user_prompt = input("> ")
    
    # Create the system prompt - emphasize sequential information gathering
    system_prompt = (
        "Answer the medical question based on the criteria provided below.\n"
        "You must conduct reasoning inside <think> and </think> first every time you get new information.\n"
        "After reasoning, if you find you lack some knowledge, you can ask ONE question at a time using <search> query </search>.\n"
        "Ask for ONE specific piece of information at a time. After receiving this information, analyze it, then ask for the next piece of information.\n"
        "Only provide your final conclusion when you have ALL necessary information.\n"
        "If you find no further external knowledge needed, you can directly provide the answer inside <answer> and </answer>.\n\n"
        f"Question: {user_prompt}"
    )
    
    # Generate the initial response
    response = model.get_response(system_prompt)
    
    # Display thinking if available
    thinking = model.extract_thinking(response)
    if thinking:
        print("\nASSISTANT: <think>" + thinking + "</think>")
    
    # Continue the conversation
    conversation_history = system_prompt + response
    
    # Track the iteration count
    iteration = 0
    max_iterations = 10
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")
        
        # Extract the first search query (if any)
        search_query = model.extract_first_search_query(response)
        
        # Check if we have a search query
        if search_query:
            print("<search>" + search_query + "</search>")
            
            # Get user input for this specific query
            print("\nUSER: ", end="")
            user_info = input()
            
            if user_info.lower() == 'exit':
                break
            
            # Format user input with special tokens and add to history
            formatted_info = f"<information>{user_info}</information>"
            
            # Generate the next response
            response = model.get_response(formatted_info, conversation_history)
            
            # Display thinking if available
            thinking = model.extract_thinking(response)
            if thinking:
                print("\nASSISTANT: <think>" + thinking + "</think>")
            
            # Update the conversation history
            conversation_history += formatted_info + response
            
        # Check if the model provided a final answer
        answer = model.extract_answer(response)
        if answer:
            print("\nASSISTANT: <answer>" + answer + "</answer>")
            break
            
        # If no search query and no answer, something went wrong
        if not search_query and not answer:
            print("\nModel response format unexpected. Full response:")
            print(response)
            
            print("\nLet's prompt the model to continue asking for information...")
            
            # Add a nudge to continue asking questions
            nudge = "\n<information>Please continue asking questions to gather all necessary information before providing a final answer.</information>"
            response = model.get_response(nudge, conversation_history)
            conversation_history += nudge + response
            
            # Check if that worked
            if not model.extract_first_search_query(response) and not model.extract_answer(response):
                print("\nModel still not responding with questions or answers. Do you want to:")
                print("1. Continue anyway")
                print("2. Exit")
                user_choice = input("Enter 1 or 2: ")
                if user_choice != "1":
                    break

if __name__ == "__main__":
    # Check available hardware
    print("=" * 80)
    print("HARDWARE DIAGNOSTICS")
    print("=" * 80)
    
    # Check if this is Apple Silicon (M1/M2/M3)
    is_apple_silicon = (platform.system() == "Darwin" and platform.processor() == "arm")
    print(f"System: {platform.system()} {platform.machine()}")
    
    if is_apple_silicon:
        print("Detected Apple Silicon Mac (M1/M2/M3)")
        # Check for MPS
        mps_available = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
        print(f"MPS available: {mps_available}")
        
        if mps_available:
            print("✅ Apple Metal Performance Shaders (MPS) available for acceleration")
            # Test a small MPS tensor
            try:
                test_tensor = torch.tensor([1, 2, 3]).to("mps")
                print(f"Test Tensor Device: {test_tensor.device}")
                print("✅ Successfully created tensor on MPS device")
            except Exception as e:
                print(f"❌ Error creating tensor on MPS: {e}")
    else:
        # Check CUDA
        cuda_available = torch.cuda.is_available()
        print(f"CUDA Available: {cuda_available}")
        
        if cuda_available:
            device_count = torch.cuda.device_count()
            print(f"CUDA Device Count: {device_count}")
            
            current_device = torch.cuda.current_device()
            print(f"Current CUDA Device: {current_device}")
            
            device_name = torch.cuda.get_device_name(current_device)
            print(f"CUDA Device Name: {device_name}")
    
    interactive_session() 
