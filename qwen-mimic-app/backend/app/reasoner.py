import re
import json
import logging
from typing import Dict, Any, List, Optional

from app.model_factory import ModelFactory
from app.criteria import get_active_criteria
from app.prompts import create_criteria_prompt, CONTINUATION_PROMPT
from app.query import get_qwen_generated_code, execute_sql_query

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
    
    def process_reasoning(self, user_input: str, conversation_history: List[Dict[str, str]] = None, use_sql: bool = False) -> dict:
        """
        Process reasoning for both initial queries and follow-up information.
        
        Args:
            user_input: The user's query or response
            conversation_history: Optional conversation history for continuing an existing session
            use_sql: Whether to use SQL retriever for database information
            
        Returns:
            Dictionary with reasoning results
        """
        # Log the SQL flag value for debugging
        logger.info(f"SQL retriever flag value: {use_sql} (type: {type(use_sql)})")
        
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
        logger.info(f"Processing as {'new conversation' if is_new_conversation else 'continuation'} (use_sql: {use_sql})")
        
        if is_new_conversation:
            logger.info(f"Starting new reasoning process for: {user_input}")
            # Extract patient ID for validation (only needed for new conversations)
            patient_id = self.extract_patient_id(user_input)
        else:
            logger.info(f"Continuing reasoning with additional information: {user_input}")
            # For continuations, try to extract a patient ID from the conversation history
            patient_id = self._extract_patient_id_from_history(valid_history)
            logger.info(f"Retrieved patient ID from history: {patient_id}")
        
        # Get the active criteria configuration
        active_criteria = get_active_criteria()
        
        # Create system prompt for the reasoner with dynamic criteria using central prompts
        system_prompt = create_criteria_prompt(
            criteria_name=active_criteria['name'],
            criteria_list=active_criteria['criteria'],
            threshold=active_criteria.get('threshold', '')
        )
        
        # Create fresh messages list with system prompt
        messages = [{"role": "system", "content": system_prompt}]
        
        database_info = None
        
        # If SQL mode is enabled, query the database
        if use_sql:
            try:
                # Generate SQL query based on the user's input and the patient ID
                sql_query_for_patient = f"Generate SQL query to get medical data for patient {patient_id} related to: {user_input}"
                logger.info(f"Generating SQL query: {sql_query_for_patient}")
                
                # Get SQL query from Qwen
                sql_query = get_qwen_generated_code(sql_query_for_patient)
                logger.info(f"Generated SQL query: {sql_query}")
                
                # Execute the query
                query_results = execute_sql_query(sql_query)
                
                # Format the results
                if isinstance(query_results, list):
                    result_str = "\n".join([str(row) for row in query_results[:10]])  # Limit to first 10 rows to avoid overwhelming the model
                    if len(query_results) > 10:
                        result_str += f"\n... and {len(query_results) - 10} more rows"
                else:
                    result_str = str(query_results)
                
                database_info = f"DATABASE INFORMATION:\nQuery: {sql_query}\nResults: {result_str}"
                logger.info(f"Database info retrieved successfully for patient {patient_id}")
                
                # Add database information to the conversation context for the model
                if is_new_conversation:
                    # For new conversations, include the database info in the prompt
                    messages.append({"role": "user", "content": f"{user_input}\n\n{database_info}"})
                else:
                    # For continuations, add the conversation history first
                    for message in valid_history:
                        if message.get("role") != "system":
                            messages.append(message)
                    
                    # Then add the new user response with database info
                    continuation_prompt = CONTINUATION_PROMPT.format(user_input=f"{user_input}\n\n{database_info}")
                    messages.append({"role": "user", "content": continuation_prompt})
            except Exception as e:
                logger.error(f"Error in SQL retrieval: {str(e)}")
                database_info = f"ERROR IN SQL RETRIEVAL: {str(e)}"
                
                # Fall back to regular behavior if SQL fails
                if is_new_conversation:
                    messages.append({"role": "user", "content": user_input})
                else:
                    for message in valid_history:
                        if message.get("role") != "system":
                            messages.append(message)
                    
                    continuation_prompt = CONTINUATION_PROMPT.format(user_input=user_input)
                    messages.append({"role": "user", "content": continuation_prompt})
        else:
            # Regular behavior without SQL
            if is_new_conversation:
                messages.append({"role": "user", "content": user_input})
            else:
                for message in valid_history:
                    if message.get("role") != "system":
                        messages.append(message)
                
                continuation_prompt = CONTINUATION_PROMPT.format(user_input=user_input)
                messages.append({"role": "user", "content": continuation_prompt})
        
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
        
        # For SQL mode, if there's a search query but we already have database info,
        # we can suppress the search query to avoid asking the user for more info
        requires_information = bool(extracted["search_query"])
        if use_sql and requires_information and database_info:
            requires_information = False
            logger.info("Suppressing search query since SQL mode is enabled and database info is available")
        
        # Prepare response
        result = {
            "full_response": response_text,
            "thinking": extracted["thinking"],
            "search_query": extracted["search_query"] if not use_sql else None,
            "answer": extracted["answer"],
            "requires_information": requires_information,
            "conversation_history": updated_history,
            "criteria_used": active_criteria["name"],
            "use_sql": use_sql
        }
        
        # Add database information if SQL retriever was used
        if use_sql and database_info:
            result["database_info"] = database_info
        
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
    def start_reasoning(self, user_prompt: str, use_sql: bool = False) -> dict:
        """Start the reasoning process for a medical query."""
        return self.process_reasoning(user_prompt, use_sql=use_sql)
    
    def continue_reasoning(self, user_response: str, conversation_history: List[Dict[str, str]], use_sql: bool = False) -> dict:
        """Continue the reasoning process with user's response to a previous query."""
        return self.process_reasoning(user_response, conversation_history, use_sql=use_sql)
