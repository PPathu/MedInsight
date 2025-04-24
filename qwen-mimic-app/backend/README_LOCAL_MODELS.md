# Local LLM Models for Medical Reasoning and SQL Generation

This README provides instructions on how to use the local LLM models implemented in this project. These models replace the API-based implementations previously used.

## Overview

The project uses two local models:
- **MedAgentReasoner-3B-Chat**: A medical reasoning model that processes information in a step-by-step, turn-based manner
- **Qwen2.5-Coder-7B**: A code generation model used to generate SQL queries

Both models run locally on your machine without requiring API keys or external services.

## Prerequisites

Make sure you have the required dependencies installed from requirements.txt:

```bash
pip install -r requirements.txt
```

For GPU acceleration:
- NVIDIA GPUs: CUDA toolkit and appropriate drivers
- Apple Silicon Macs: PyTorch 2.0+ with MPS support

## Model Implementation

### TransformersModelHandler

The core implementation for model handling is in `app/model_transformers.py`. This class:

1. **Automatically detects hardware**:
   - Checks for CUDA availability (NVIDIA GPUs)
   - Checks for MPS availability (Apple Silicon M1/M2/M3)
   - Falls back to CPU if no acceleration is available

2. **Optimizes model loading**:
   - Uses half-precision (float16) when supported
   - Configures appropriate device mapping
   - Manages memory efficiently

3. **Handles prompt formatting**:
   - Formats conversation history into appropriate prompts
   - Maintains conversation context between queries
   - Extracts structured responses (<think>, <search>, <answer>)

4. **Provides debug information**:
   - Timing for model loading and inference
   - Device information and memory usage
   - Step-by-step reasoning process

## Available Test Scripts

Three test scripts are available to test the local models:

### 1. Interactive Test (Main Testing Script)

Provides an interactive CLI interface to test the MedAgentReasoner model with a conversation:

```bash
python interactive_test.py
```

This script:
- Detects your hardware (CUDA, Apple MPS, or CPU)
- Loads the MedAgentReasoner model with appropriate settings
- Allows you to have a turn-based conversation with the model
- Shows the model's reasoning process step by step

### 2. GPU Testing Scripts

For testing GPU acceleration specifically:

```bash
python gpu_test.py        # Test MedAgentReasoner with GPU
python gpu_qwen_test.py   # Test Qwen model with GPU
```

These scripts provide detailed diagnostics about GPU usage and acceleration.

## Interactive Testing Example

1. Run the interactive test:
   ```bash
   python interactive_test.py
   ```

2. Enter a medical question when prompted:
   ```
   Enter your medical question:
   > Evaluate qSOFA for patient 12345
   ```

3. The model will think, then ask for specific information:
   ```
   ASSISTANT: <think>I need to check the patient's vital signs to evaluate qSOFA criteria.</think>
   <search>What is the patient's respiratory rate?</search>
   
   USER: 
   ```

4. Provide the requested information:
   ```
   USER: The respiratory rate is 25 breaths/min
   ```

5. The model will continue asking for necessary information one piece at a time:
   ```
   ASSISTANT: <think>The respiratory rate is 25 breaths/min, which is ≥22 breaths/min. 
   This meets one qSOFA criterion (respiratory rate ≥ 22 breaths/min).</think>
   <search>What is the patient's systolic blood pressure?</search>
   
   USER: 
   ```

6. The conversation continues until the model has all the necessary information to provide a final answer.

## Conversation History Support

The system now supports maintaining conversation history across multiple queries:

1. **History Storage**:
   - Messages are stored with user/assistant roles
   - Context from previous questions is maintained
   - Follow-up questions can reference previous information

2. **Implementation**:
   - Backend: `reasoner.py` maintains and processes conversation history
   - Frontend: `Layout.js` stores conversation in localStorage
   - API: `/provide_info` endpoint handles both GET and POST for history retrieval/update

3. **Example Multi-turn Conversation**:
   ```
   USER: What are the criteria for sepsis?
   AI: [Provides sepsis criteria]
   
   USER: How does it differ from SIRS?
   AI: [Provides comparison based on previous context]
   ```

## FastAPI Integration

The models are integrated into the FastAPI backend:

1. `/diagnose` endpoint: Initiates a medical reasoning session
2. `/provide_info` endpoint: 
   - POST: Allows providing additional information to continue reasoning
   - GET: Retrieves current conversation state for follow-ups

To test the FastAPI endpoints using curl:

1. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Send a request to the diagnose endpoint:
   ```bash
   curl -X POST http://localhost:8000/diagnose \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Evaluate qSOFA for patient 12345"}'
   ```

3. Provide additional information using the provide_info endpoint:
   ```bash
   curl -X POST http://localhost:8000/provide_info \
     -H "Content-Type: application/json" \
     -d '{
       "info": "The respiratory rate is 25 breaths/min", 
       "state": {
         "original_prompt": "Evaluate qSOFA for patient 12345",
         "messages": [
           {"role": "user", "content": "Evaluate qSOFA for patient 12345"},
           {"role": "assistant", "content": "<think>I need to check for qSOFA criteria.</think><search>What is the respiratory rate?</search>"}
         ],
         "last_output": "<think>I need to check for qSOFA criteria.</think><search>What is the respiratory rate?</search>"
       }
     }'
   ```

## Hardware Acceleration

The system provides detailed hardware detection and optimization:

### NVIDIA GPUs
```python
if torch.cuda.is_available():
    device = "cuda"
    # Get GPU details
    gpu_name = torch.cuda.get_device_name(0)
    gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
    
    # Use half-precision for NVIDIA GPUs
    model = model.half()
    # Enable TensorFloat-32 for better performance on A100/A10G/RTX30xx+
    torch.backends.cuda.matmul.allow_tf32 = True
```

### Apple Silicon
```python
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device = "mps"
    # Use MPS for Apple Silicon acceleration
    model = model.to("mps")
    # Optimize for memory usage
    torch.mps.empty_cache()
```

### CPU Fallback
```python
else:
    device = "cpu"
    # Configure CPU threads
    torch.set_num_threads(max(4, min(16, os.cpu_count() or 4)))
```

For optimal performance, a GPU with at least 6GB VRAM is recommended.

## Implementation Details

- **app/model_transformers.py**: Core model handler with hardware detection and optimization
- **app/reasoner.py**: Contains the reasoning implementation with conversation history support
- **app/query.py**: Contains the SQL generation implementation
- **app/diagnose.py**: Integrates the models with FastAPI endpoints
