import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.deepseek import DeepSeekModel
from app.query import get_qwen_generated_code, execute_sql_query

router = APIRouter()
deepseek = DeepSeekModel()

async def generate_response(user_prompt: str):
    """
    Streams a progressive response:
    1. Sends a 'thinking' message.
    2. Generates the special token–wrapped query via DeepSeek.
    3. Passes that query to Qwen to generate a SQL query.
    4. Executes the SQL query.
    5. Feeds the SQL result back to DeepSeek to produce a reasoned explanation.
    6. Returns the final response.
    """
    if not user_prompt:
        yield '{"error": "No prompt provided."}\n'
        return

    # Step 1: Get reasoning steps and generated queries from DeepSeek.
    reasoning_steps = deepseek.reason_about_prompt(user_prompt)
    queries = reasoning_steps.get("queries", [])
    if not queries:
        yield '{"status": "error", "message": "Failed to generate a valid database query."}\n'
        return

    # Extract the first generated query (wrapped with special tokens)
    query_token = queries[0]

    # Use partial reasoning if available.
    partial_reasoning = reasoning_steps.get("partial_reasoning", ["The AI is processing your request..."])
    response_text = " ".join(partial_reasoning)

    # Immediately send a 'thinking' message.
    yield f'{{"status": "thinking", "message": "{response_text}"}}\n'
    await asyncio.sleep(1)  # Simulate slight delay

    # Step 2: Send the special token–wrapped query to Qwen (Qwen code will strip markers).
    qwen_sql_query = get_qwen_generated_code(query_token)
    print("DEBUG: Qwen generated SQL query:", qwen_sql_query)

    # Step 3: Execute the generated SQL query.
    qwen_result = execute_sql_query(qwen_sql_query)
    print("DEBUG: Qwen query result:", qwen_result)

    # Step 4: Feed the SQL result back into DeepSeek to generate a final, reasoned response.
    final_reasoned_response = deepseek.generate_reasoned_response(qwen_result, user_prompt)

    # Step 5: Return the final response.
    yield f'{{"status": "complete", "message": "{final_reasoned_response}"}}\n'

@router.post("/diagnose")
async def diagnose_patient(request: dict):
    """
    Diagnose endpoint that streams responses.
    """
    user_prompt = request.get("prompt", "")
    return StreamingResponse(generate_response(user_prompt), media_type="text/event-stream")
