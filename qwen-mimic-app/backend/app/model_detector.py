import os
import sys
import platform
import logging
import subprocess
from typing import Dict, Any, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HardwareDetector:
    """Detect hardware capabilities to determine best model implementation"""
    
    @staticmethod
    def detect_system() -> Dict[str, Any]:
        """Detect system information and hardware capabilities"""
        system_info = {
            "os": platform.system(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "cuda_available": False,
            "mps_available": False,
            "cpu_only": True,
            "recommended_backend": "cpu"
        }
        
        # Try to detect CUDA for NVIDIA GPUs
        try:
            import torch
            system_info["torch_available"] = True
            system_info["torch_version"] = torch.__version__
            
            if torch.cuda.is_available():
                system_info["cuda_available"] = True
                system_info["cuda_version"] = torch.version.cuda
                system_info["gpu_name"] = torch.cuda.get_device_name(0)
                system_info["gpu_count"] = torch.cuda.device_count()
                system_info["recommended_backend"] = "vllm"
                system_info["cpu_only"] = False
                logger.info(f"CUDA is available: {system_info['gpu_name']}")
            
            # Check for Apple Silicon MPS (Metal Performance Shaders)
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                system_info["mps_available"] = True
                system_info["cpu_only"] = False
                system_info["recommended_backend"] = "transformers"
                logger.info("Apple MPS is available (M1/M2 Mac)")
            
            else:
                logger.info("No GPU acceleration found, using CPU")
                
        except ImportError:
            logger.warning("PyTorch not available, defaulting to CPU")
            system_info["torch_available"] = False
        
        # Check for M1/M2 Mac specifically
        if system_info["os"] == "Darwin" and system_info["architecture"] in ["arm64", "aarch64"]:
            system_info["is_apple_silicon"] = True
            # Even if torch.backends.mps is not available, we'll default to transformers for Apple Silicon
            if not system_info["mps_available"]:
                system_info["recommended_backend"] = "transformers"
            logger.info("Apple Silicon detected")
        else:
            system_info["is_apple_silicon"] = False
            
        return system_info

    @staticmethod
    def can_use_vllm() -> Tuple[bool, str]:
        """Check if vllm can be used on this system"""
        try:
            import vllm
            
            # Check if CUDA is available for vllm
            import torch
            if not torch.cuda.is_available():
                return False, "VLLM requires CUDA, but it's not available"
                
            return True, "VLLM is available and can be used"
        except ImportError:
            return False, "VLLM is not installed"
        except Exception as e:
            return False, f"Error checking VLLM: {str(e)}"
            
    @staticmethod
    def can_use_transformers() -> Tuple[bool, str]:
        """Check if transformers can be used on this system"""
        try:
            import transformers
            import torch
            
            return True, "Transformers is available and can be used"
        except ImportError:
            return False, "Transformers is not installed"
        except Exception as e:
            return False, f"Error checking Transformers: {str(e)}"

def get_optimal_backend() -> str:
    """Determine the optimal backend based on hardware detection"""
    system_info = HardwareDetector.detect_system()
    
    # Check for environment variable override
    force_backend = os.environ.get("FORCE_BACKEND", "").lower()
    if force_backend in ["vllm", "transformers", "cpu"]:
        logger.info(f"Backend forced to {force_backend} via environment variable")
        return force_backend
        
    # Otherwise use recommended backend
    logger.info(f"Using recommended backend: {system_info['recommended_backend']}")
    return system_info["recommended_backend"] 
