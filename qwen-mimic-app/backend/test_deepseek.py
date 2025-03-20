from app.deepseek import DeepSeekModel

def test_deepseek():
    # Sample prompt to test DeepSeek
    prompt = "What medications has patient 10000032 been prescribed?"
    
    # Instantiate the DeepSeek model
    model = DeepSeekModel()
    
    # Get the reasoning output (which includes extracted fields and generated queries)
    result = model.reason_about_prompt(prompt)
    
    # Print the result for debugging
    print("Result from DeepSeek:")
    print("Needed Fields:", result.get("needed_fields"))
    print("Partial Reasoning:", result.get("partial_reasoning"))
    print("Generated Queries:", result.get("queries"))

if __name__ == "__main__":
    test_deepseek()
