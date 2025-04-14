from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import sys

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

def test_model_gpu():
    """
    Test for MedAgentReasoner model that explicitly uses GPU if available.
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
        
        # Model name
        model_name = "tossowski/MedAgentReasoner-3B-Chat"
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
        
        # Create a simple prompt for testing
        prompt = "Answer this medical question: What is qSOFA?"
        print(f"\nPrompt: {prompt}")
        
        # Tokenize input and move to device
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        
        # Generate response with minimal settings
        print("Generating response...")
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,  # Shorter to make it faster
                temperature=0.7,
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

if __name__ == "__main__":
    print("=" * 80)
    print("GPU MODEL TEST")
    print("=" * 80)
    print("This script attempts to explicitly use the GPU for the model")
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
    success = test_model_gpu()
    
    if success:
        print("\nTest completed successfully!")
    else:
        print("\nTest failed. Try these steps:")
        print("1. Make sure your GPU drivers are properly installed")
        print("2. Install CUDA toolkit compatible with your PyTorch version")
        print("3. Run: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
        print("   (replace cu118 with your CUDA version)")
        print("4. Check that your GPU has enough memory for this model (at least 6GB)")
        print("5. Try with a smaller model by changing the model name") 
