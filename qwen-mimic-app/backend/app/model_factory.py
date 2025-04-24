import logging
import importlib
from typing import Any, Dict, List, Optional, Union

from app.model_detector import get_optimal_backend, HardwareDetector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelFactory:
    """Factory class to create the appropriate model handler based on hardware detection"""
    
    @staticmethod
    def create_model(model_name: str, model_type: str = "reasoning") -> Any:
        """
        Create a model handler for the specified model
        
        Args:
            model_name: Name/path of the model to load
            model_type: Type of model ('reasoning' or 'sql')
            
        Returns:
            Model handler instance
        
        Raises:
            RuntimeError: If no suitable backend is available or model loading fails
        """
        # Determine the optimal backend
        backend = get_optimal_backend()
        logger.info(f"Creating {model_type} model with backend: {backend}")
        
        try:
            if backend == "vllm":
                # Check if vllm can be used
                can_use_vllm, reason = HardwareDetector.can_use_vllm()
                if not can_use_vllm:
                    logger.warning(f"Cannot use VLLM: {reason}")
                    logger.info("Falling back to transformers backend")
                    backend = "transformers"
                else:
                    # Try to import and create VLLM handler
                    from app.model_vllm import VLLMModelHandler
                    handler = VLLMModelHandler(model_name)
                    logger.info(f"Successfully created VLLMModelHandler for {model_name}")
                    return handler
            
            if backend == "transformers":
                # Check if transformers can be used
                can_use_transformers, reason = HardwareDetector.can_use_transformers()
                if not can_use_transformers:
                    logger.error(f"Cannot use Transformers: {reason}")
                    raise RuntimeError(f"No suitable backend available: {reason}")
                else:
                    # Try to import and create Transformers handler
                    from app.model_transformers import TransformersModelHandler
                    handler = TransformersModelHandler(model_name)
                    logger.info(f"Successfully created TransformersModelHandler for {model_name}")
                    return handler
            
            # If we reach here with no backend, raise an error
            raise RuntimeError("No suitable model backend available")
                
        except Exception as e:
            logger.error(f"Error creating model handler: {str(e)}")
            raise RuntimeError(f"Failed to create model handler: {str(e)}")
