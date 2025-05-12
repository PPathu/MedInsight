from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import sys
import os
import time
import logging
from app.prompts import TEST_SQL_QUESTION

def check_gpu():
    """Check if CUDA is available and print detailed information"""
    print("=" * 80)
    print("GPU DIAGNOSTICS")
    print("=" * 80)
    
    # Check if CUDA is available
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")
    
    if cuda_available:
        # Get CUDA device count
        device_count = torch.cuda.device_count()
        print(f"CUDA Device Count: {device_count}")
        
        # Get current device
        current_device = torch.cuda.current_device()
        print(f"Current CUDA Device: {current_device}")
        
        # Get device name
        device_name = torch.cuda.get_device_name(current_device)
        print(f"CUDA Device Name: {device_name}")
        
        # Get device properties
        device_props = torch.cuda.get_device_properties(current_device)
        print(f"Total Memory: {device_props.total_memory / (1024**3):.2f} GB")
        
        # Test a small tensor on GPU
        try:
            test_tensor = torch.tensor([1, 2, 3]).cuda()
            print(f"Test Tensor Device: {test_tensor.device}")
            print("✅ Successfully created tensor on CUDA device")
        except Exception as e:
            print(f"❌ Error creating tensor on CUDA: {e}")
    
    return cuda_available

def test_qwen_gpu():
    """
    Test for Qwen model that explicitly uses GPU if available.
    """
    try:
        # Explicitly set dtype and device
        if torch.cuda.is_available():
            device = torch.device("cuda")
            dtype = torch.float16  # Use half precision on GPU
            print(f"Using CUDA device: {torch.cuda.get_device_name(0)}")
        else:
            device = torch.device("cpu")
            dtype = torch.float32
            print("⚠️ CUDA not available, falling back to CPU (will be very slow)")
        
        # Model name - using a smaller model to reduce memory requirements
        # You can try "Qwen/Qwen2.5-Coder-7B" if you have enough GPU memory
        model_name = "Qwen/Qwen2-1.5B"
        print(f"Loading model: {model_name}")
        
        # Load tokenizer
        print("Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Load model with explicit GPU settings
        print("Loading model (this may take a while)...")
        config = {
            "torch_dtype": dtype,
            "low_cpu_mem_usage": True
        }
        
        # Only use device_map on CUDA
        if torch.cuda.is_available():
            config["device_map"] = "auto"  # or "cuda:0" for specific device
        
        model = AutoModelForCausalLM.from_pretrained(model_name, **config)
        
        # Verify model device
        print(f"Model is on device: {next(model.parameters()).device}")
        
        # Create a SQL prompt for testing
        prompt = TEST_SQL_QUESTION
        print(f"\nPrompt: {prompt}")
        
        # Tokenize input and move to device
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        
        # Generate response with minimal settings
        print("Generating response...")
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,  # Shorter to make it faster
                temperature=0.2,
                do_sample=True
            )
        
        # Decode the response
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print("\nResponse:")
        print(response)
        
        return True
    
    except Exception as e:
        print(f"Error during model test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Test loading a Qwen model on the GPU"""
    start_time = time.time()
    
    # Get model name from environment variable or use default
    model_name = os.environ.get("MODEL_NAME", "Qwen/Qwen1.5-7B-Chat")
    print(f"\nTesting model: {model_name}")
    
    # Check for GPU
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"Using CUDA - {torch.cuda.get_device_name(0)}")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
        print("Using MPS (Metal Performance Shaders)")
    else:
        device = torch.device("cpu")
        print("WARNING: Using CPU (slow) - no GPU detected")
    
    try:
        print("\nLoading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        print("Loading model...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto" if device.type == "cuda" else None,
            low_cpu_mem_usage=True
        )
        
        # Move model to device if not using device_map="auto"
        if device.type != "cuda":
            model = model.to(device)
            
        print(f"Model loaded in {time.time() - start_time:.2f} seconds")
        
        # Create a SQL prompt for testing
        prompt = TEST_SQL_QUESTION
        print(f"\nPrompt: {prompt}")
        
        # Generate text
        start_gen = time.time()
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        
        output = model.generate(
            **inputs, 
            max_new_tokens=150,
            temperature=0.7,
            top_p=0.9
        )
        
        output_text = tokenizer.decode(output[0], skip_special_tokens=True)
        gen_time = time.time() - start_gen
        
        print(f"\nGenerated text in {gen_time:.2f} seconds:")
        print(output_text)
        print(f"\nTotal tokens: {len(output[0])}, Tokens per second: {len(output[0])/gen_time:.2f}")
        
        print(f"\nTotal runtime: {time.time() - start_time:.2f} seconds")
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error during test: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    print("=" * 80)
    print("QWEN GPU MODEL TEST")
    print("=" * 80)
    print("This script attempts to explicitly use the GPU for the Qwen model")
    print("=" * 80)
    
    # First check GPU
    has_gpu = check_gpu()
    
    if not has_gpu:
        print("\n⚠️ No GPU detected. This will run VERY slowly on CPU.")
        user_input = input("Continue anyway? (y/n): ")
        if user_input.lower() != 'y':
            print("Exiting...")
            sys.exit(0)
    
    # Run the test
    success = test_qwen_gpu()
    
    if success:
        print("\nTest completed successfully!")
    else:
        print("\nTest failed. Try these steps:")
        print("1. Make sure your GPU drivers are properly installed")
        print("2. Install CUDA toolkit compatible with your PyTorch version")
        print("3. Run: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
        print("   (replace cu118 with your CUDA version)")
        print("4. Check that your GPU has enough memory (try a smaller model if needed)")
        print("5. If using CUDA out of memory, try a smaller model like:")
        print("   model_name = \"Qwen/Qwen2-0.5B\"")
    
    sys.exit(main()) 
