import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

print("Testing package compatibility...")

try:
    import numpy
    print(f"✅ NumPy version: {numpy.__version__}")
    
    import torch
    print(f"✅ PyTorch version: {torch.__version__}")
    
    import transformers
    print(f"✅ Transformers version: {transformers.__version__}")
    
    from transformers import AutoTokenizer
    print("✅ AutoTokenizer imported")
    
    from transformers import AutoModelForCausalLM
    print("✅ AutoModelForCausalLM imported")
    
    print("All imports successful, packages are compatible!")
except Exception as e:
    print(f"❌ Error during imports: {e}")
    exit(1)
