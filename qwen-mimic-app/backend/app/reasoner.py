import re
import json
import logging
from typing import Dict, Any, List, Optional

from app.model_factory import ModelFactory

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LocalReasonerModel:
    """
    A model for medical reasoning using a step-by-step Q&A approach.
    This model skips database queries and instead directly asks the user for information.
    """
    
    def __init__(self):
        """Initialize the reasoner model, using the optimal backend for this hardware"""
        model_name = "tossowski/MedAgentReasoner-3B-Chat"
        logger.info(f"Initializing LocalReasonerModel with model: {model_name}")
        
        # Use model factory to create the appropriate model handler
        self.model_handler = ModelFactory.create_model(model_name, model_type="reasoning")
        logger.info(f"Using backend: {self.model_handler.__class__.__name__}")
    
    def extract_patient_id(self, user_prompt: str) -> str:
        """
        Extracts the patient ID from the prompt.
        Supports both formats:
        - 'patient 12345'
        - 'admission=12345'
        """
        # Try both patterns
        patient_match = re.search(r"patient\s+(\d+)", user_prompt, re.IGNORECASE)
        admission_match = re.search(r"admission=(\d+)", user_prompt, re.IGNORECASE)
        
        # Use whichever pattern matched
        match = patient_match or admission_match
        
        if not match:
            raise ValueError("No patient ID found in prompt. Please specify a patient ID (e.g., 'patient 12345' or 'admission=12345').")
        
        patient_id = match.group(1)
        logger.info(f"Successfully extracted patient ID: {patient_id}")
        return patient_id
    
    def process_reasoning(self, user_input: str, conversation_history: List[Dict[str, str]] = None) -> dict:
        """
        Process reasoning for both initial queries and follow-up information.
        
        Args:
            user_input: The user's query or response
            conversation_history: Optional conversation history for continuing an existing session
            
        Returns:
            Dictionary with reasoning results
        """
        # Validate and clean conversation history
        if conversation_history is None:
            conversation_history = []
        
        # More robust check for a valid conversation history
        valid_history = [
            msg for msg in conversation_history 
            if isinstance(msg, dict) and "role" in msg and "content" in msg
        ]
        
        # Determine if this is a new conversation or a continuation
        is_new_conversation = len(valid_history) == 0
        
        # Log the conversation type for debugging
        logger.info(f"Processing as {'new conversation' if is_new_conversation else 'continuation'}")
        
        if is_new_conversation:
            logger.info(f"Starting new reasoning process for: {user_input}")
            # Extract patient ID for validation (only needed for new conversations)
            patient_id = self.extract_patient_id(user_input)
        else:
            logger.info(f"Continuing reasoning with additional information: {user_input}")
            # For continuations, try to extract a patient ID from the conversation history
            patient_id = self._extract_patient_id_from_history(valid_history)
            logger.info(f"Retrieved patient ID from history: {patient_id}")
        
        # Create system prompt for the reasoner with qSOFA criteria
        system_prompt = (
            "Answer the qSOFA question based on the criteria provided below.\n"
            "You must conduct reasoning inside <think> and </think> first every time you get new information.\n" 
            "After reasoning, if you find you lack some knowledge, you can call a search engine by <search> query </search>, and it will return the top searched results between <information> and </information>.\n"
            "You can search as many times as you want. If you find no further external knowledge needed, you can directly provide the answer inside <answer> and </answer> without detailed illustrations. Example: <answer> SIRS present </answer>\n\n"
            "qSOFA criteria:\n"
            "- Respiratory Rate (RR) ≥ 22 breaths/min\n"
            "- Systolic Blood Pressure (SBP) ≤ 100 mmHg\n"
            "- Altered mentation (GCS verbal response is not \"Oriented\")\n"
            " => If ≥2 => qSOFA"
        )
        
        # Create fresh messages list with system prompt
        messages = [{"role": "system", "content": system_prompt}]
        
        if is_new_conversation:
            # For new conversations, just add the user's initial query
            messages.append({"role": "user", "content": user_input})
        else:
            # For continuations, add the conversation history (excluding system messages)
            for message in valid_history:
                if message.get("role") != "system":
                    messages.append(message)
            
            # Add the new user response with context
            messages.append({"role": "user", "content": f"I'm providing additional information: {user_input}. Please continue your assessment based on this new information."})
        
        # Generate response based on messages
        response_data = self.model_handler.generate(messages, max_tokens=1000, temperature=0.2)
        response_text = response_data["text"]
        
        # Extract thinking, search query, and answer
        extracted = self.model_handler.extract_sections(response_text)
        
        # Log what was extracted to help with debugging
        logger.info(f"Extracted thinking: {extracted['thinking'] is not None}")
        logger.info(f"Extracted search query: {extracted['search_query'] is not None}")
        logger.info(f"Extracted answer: {extracted['answer'] is not None}")
        
        # Prepare conversation history for the result
        if is_new_conversation:
            updated_history = [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": response_text}
            ]
        else:
            updated_history = valid_history.copy()
            updated_history.append({"role": "user", "content": user_input})
            updated_history.append({"role": "assistant", "content": response_text})
        
        # Prepare response
        result = {
            "full_response": response_text,
            "thinking": extracted["thinking"],
            "search_query": extracted["search_query"],
            "answer": extracted["answer"],
            "requires_information": bool(extracted["search_query"]),
            "conversation_history": updated_history
        }
        
        # Add extra fields for all responses to ensure consistency
        result["patient_id"] = patient_id
        if is_new_conversation:
            result["original_prompt"] = user_input
        
        # Log the conversation history for debugging
        logger.info(f"Returning result with conversation history of {len(updated_history)} messages")
        if len(updated_history) > 0:
            logger.info(f"First message: {updated_history[0].get('role')} - {updated_history[0].get('content')[:30]}...")
        
        return result

    def _extract_patient_id_from_history(self, conversation_history: List[Dict[str, str]]) -> str:
        """
        Extract patient ID from conversation history.
        This is used for continuation cases where we don't want to require the user to re-specify the patient ID.
        """
        # First, look for the original prompt which should contain the patient ID
        first_user_message = next((msg for msg in conversation_history if msg.get("role") == "user"), None)
        if first_user_message:
            try:
                return self.extract_patient_id(first_user_message.get("content", ""))
            except ValueError:
                pass
        
        # If that fails, search all messages for a patient ID
        for message in conversation_history:
            content = message.get("content", "")
            try:
                return self.extract_patient_id(content)
            except ValueError:
                continue
        
        # If no patient ID is found, return a default
        logger.warning("No patient ID found in conversation history, using default")
        return "unknown"

    # Keep these as wrapper methods for backward compatibility
    def start_reasoning(self, user_prompt: str) -> dict:
        """Start the reasoning process for a medical query."""
        return self.process_reasoning(user_prompt)
    
    def continue_reasoning(self, user_response: str, conversation_history: List[Dict[str, str]]) -> dict:
        """Continue the reasoning process with user's response to a previous query."""
        return self.process_reasoning(user_response, conversation_history)
