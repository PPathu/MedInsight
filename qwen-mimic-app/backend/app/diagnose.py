import asyncio
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.reasoner import LocalReasonerModel
import logging
from pydantic import BaseModel, validator
from typing import Optional, Dict, Any, List, Union
import re
from app.model_progress import progress_monitor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define data models
class DiagnoseRequest(BaseModel):
    query: str

class ProvideInfoRequest(BaseModel):
    user_response: str
    conversation_history: Union[str, List[Dict[str, Any]]]
    
    @validator('conversation_history')
    def validate_conversation_history(cls, v):
        # If it's already a list, return it as is
        if isinstance(v, list):
            return v
        # If it's a string, convert to an empty list (we'll just use the latest response)
        if isinstance(v, str):
            logger.info("Converting string conversation history to empty list")
            return []
        return v

router = APIRouter()

# Initialize the model once
local_reasoner = LocalReasonerModel()

async def generate_response(response_content):
    """
    Generate a streaming response for the frontend.
    """
    try:
        if isinstance(response_content, dict):
            # Send thinking component first if available
            if "thinking" in response_content and response_content.get('thinking'):
                yield f"data: {json.dumps({'type': 'thinking', 'content': response_content.get('thinking', '')})}\n\n"
                await asyncio.sleep(0.1)
            
            # Send search query if available
            if "search_query" in response_content and response_content.get('search_query'):
                yield f"data: {json.dumps({'type': 'search', 'content': response_content.get('search_query', '')})}\n\n"
                await asyncio.sleep(0.1)
            
            # Send answer if available
            if "answer" in response_content and response_content.get('answer'):
                yield f"data: {json.dumps({'type': 'answer', 'content': response_content.get('answer', '')})}\n\n"
                await asyncio.sleep(0.1)
            
            # Send full response
            if "full_response" in response_content:
                yield f"data: {json.dumps({'type': 'full', 'content': response_content.get('full_response', '')})}\n\n"
                await asyncio.sleep(0.1)
                
            # Always send conversation history for state tracking - this part is crucial
            if "conversation_history" in response_content:
                # Log for debugging
                history_count = len(response_content.get('conversation_history', []))
                logger.info(f"Sending conversation history with {history_count} messages in stream")
                yield f"data: {json.dumps({'type': 'conversation', 'content': response_content.get('conversation_history', [])})}\n\n"
                await asyncio.sleep(0.1)
            else:
                logger.warning("Response content missing conversation_history")
        else:
            # Fallback for string responses
            yield f"data: {json.dumps({'type': 'full', 'content': str(response_content)})}\n\n"
        
        # Signal the end of the stream
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except Exception as e:
        logger.error(f"Error in generate_response: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

async def stream_loading_progress():
    """
    Stream model loading progress to the client.
    """
    previous_progress = None
    
    # Create an async queue to receive progress updates
    queue = asyncio.Queue()
    
    # Define a callback to receive progress updates
    def progress_callback(progress_data):
        asyncio.run_coroutine_threadsafe(queue.put(progress_data), asyncio.get_event_loop())
    
    # Subscribe to progress updates
    progress_monitor.subscribe(progress_callback)
    
    try:
        # Send initial progress data
        initial_progress = progress_monitor.get_progress_summary()
        yield f"data: {json.dumps({'type': 'model_progress', 'content': initial_progress})}\n\n"
        
        # Stream progress updates while loading
        while True:
            try:
                # Get progress with timeout to avoid blocking indefinitely
                progress_data = await asyncio.wait_for(queue.get(), timeout=1.0)
                
                # Only send updates when progress changes
                if previous_progress != progress_data:
                    previous_progress = progress_data.copy()
                    yield f"data: {json.dumps({'type': 'model_progress', 'content': progress_data})}\n\n"
                
                # If loading is complete, break the loop
                if not progress_data.get('is_loading', False) and progress_data.get('files', {}):
                    break
                    
            except asyncio.TimeoutError:
                # Check if loading is complete
                if not progress_monitor.is_loading:
                    break
                # Otherwise, just continue the loop
                continue
            except Exception as e:
                logger.error(f"Error streaming progress: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'content': f'Progress streaming error: {str(e)}'})}\n\n"
                break
    finally:
        # Unsubscribe to avoid memory leaks
        progress_monitor.unsubscribe(progress_callback)

@router.get("/diagnose-test")
async def diagnose_test():
    """Test endpoint to verify the diagnose router is working"""
    return {"status": "Diagnose endpoint is working"}

@router.post("/diagnose")
@router.get("/diagnose")
async def diagnose(request: DiagnoseRequest = None, query: str = None):
    # Support both POST body and GET query parameter
    user_query = query or (request.query if request else None)
    
    if not user_query:
        raise HTTPException(status_code=400, detail="No query provided")
    
    try:
        logger.info(f"Processing query: {user_query}")
        
        # Start a streaming response immediately to show progress
        async def response_stream():
            # Send initial loading message
            yield f"data: {json.dumps({'type': 'status', 'content': 'Starting query processing...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Stream model loading progress if models are loading
            if progress_monitor.is_loading or not progress_monitor.current_progress:
                yield f"data: {json.dumps({'type': 'status', 'content': 'Downloading and loading models (this may take a few minutes on first run)...'})}\n\n"
                async for progress_chunk in stream_loading_progress():
                    yield progress_chunk
            
            try:
                # Start the reasoning process using process_reasoning with no history
                response = local_reasoner.process_reasoning(user_query)
                logger.info("Generated initial reasoning response")
                
                # Send the model's response
                async for chunk in generate_response(response):
                    yield chunk
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        
        # Return the streaming response
        return StreamingResponse(
            response_stream(),
            media_type="text/event-stream"
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in /diagnose endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@router.post("/provide_info")
async def provide_info_post(request: ProvideInfoRequest):
    """
    Process the user's response to a question and continue the reasoning.
    Returns a JSON response directly for POST requests.
    """
    try:
        # Extract data from request
        user_input = request.user_response
        conversation_history = request.conversation_history
        
        # Log what we received for debugging
        logger.info(f"Received user_response: {user_input}")
        history_length = len(conversation_history) if isinstance(conversation_history, list) else 0
        logger.info(f"Received conversation_history with {history_length} entries")
        
        if history_length > 0:
            # Log the first message to verify format
            first_msg = conversation_history[0]
            logger.info(f"First message in history: role={first_msg.get('role', 'unknown')}, content_length={len(first_msg.get('content', ''))}")
        
        # Ensure we have valid conversation history
        if not conversation_history or len(conversation_history) == 0:
            logger.warning("Missing conversation history - cannot continue reasoning without context")
            raise HTTPException(status_code=400, detail="Missing conversation history - cannot continue reasoning")
            
        # Check that conversation history items have the correct structure
        valid_items = [
            msg for msg in conversation_history 
            if isinstance(msg, dict) and "role" in msg and "content" in msg
        ]
        
        if len(valid_items) == 0:
            logger.warning("Conversation history exists but contains no valid messages with 'role' and 'content'")
            raise HTTPException(
                status_code=400, 
                detail="Invalid conversation history format. Messages must have 'role' and 'content' fields."
            )
            
        logger.info(f"Processing user response via POST: {user_input}")
        logger.info(f"Proceeding with {len(valid_items)} valid messages in conversation history")
        
        # Continue the reasoning using process_reasoning with conversation history
        response = local_reasoner.process_reasoning(user_input, conversation_history)
        logger.info("Generated continuation response for POST request")
        
        # Return the full response directly as JSON
        return response
        
    except Exception as e:
        logger.error(f"Error in /provide_info POST endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@router.get("/provide_info")
async def provide_info_get(user_response: str = None):
    """
    Process the user's response to a question and continue the reasoning.
    Returns a streaming response for GET requests.
    Note: This endpoint is limited, as query parameters can't easily include complex objects
    like conversation history. Using the POST endpoint is preferred.
    """
    if not user_response:
        raise HTTPException(status_code=400, detail="No user response provided")
    
    # Return instructions to use the POST endpoint instead
    raise HTTPException(
        status_code=400, 
        detail="The GET endpoint for provide_info cannot properly handle conversation history. "
               "Please use the POST endpoint with conversation_history in the request body."
    )
