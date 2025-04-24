import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.query import get_qwen_generated_code, execute_sql_query
from app.model_detector import HardwareDetector
from app.diagnose import router as diagnose_router
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.criteria import (
    get_criteria_list, 
    get_active_criteria, 
    set_active_criteria, 
    add_custom_criteria, 
    delete_custom_criteria
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define data models for criteria endpoints
class CustomCriteriaCreate(BaseModel):
    key: str
    name: str
    description: str
    criteria: List[str]
    threshold: str

class CriteriaSelection(BaseModel):
    key: str

# Startup event
@app.on_event("startup")
async def startup_event():
    """Run at app startup - detect hardware and log info"""
    logger.info("🚀 Starting MedInsight backend server")
    
    # Detect system capabilities
    system_info = HardwareDetector.detect_system()
    
    # Log detailed system information
    logger.info("=" * 50)
    logger.info("SYSTEM INFORMATION")
    logger.info("=" * 50)
    logger.info(f"OS: {system_info['os']}")
    logger.info(f"Architecture: {system_info['architecture']}")
    logger.info(f"Python version: {system_info['python_version']}")
    
    if system_info.get('torch_available', False):
        logger.info(f"PyTorch version: {system_info.get('torch_version', 'Unknown')}")
        if system_info.get('cuda_available', False):
            logger.info(f"CUDA available: Yes (version {system_info.get('cuda_version', 'Unknown')})")
            logger.info(f"GPU: {system_info.get('gpu_name', 'Unknown')}")
        elif system_info.get('mps_available', False):
            logger.info("Apple MPS available: Yes (M1/M2 Mac acceleration)")
        else:
            logger.info("GPU acceleration: Not available, using CPU")
    else:
        logger.info("PyTorch: Not available")
    
    logger.info(f"Recommended backend: {system_info.get('recommended_backend', 'unknown')}")
    logger.info("=" * 50)
    
    # Test if VLLM is available
    can_use_vllm, vllm_reason = HardwareDetector.can_use_vllm()
    logger.info(f"VLLM available: {'Yes' if can_use_vllm else 'No'}")
    if not can_use_vllm:
        logger.info(f"VLLM status: {vllm_reason}")
    
    # Test if transformers is available
    can_use_transformers, transformers_reason = HardwareDetector.can_use_transformers()
    logger.info(f"Transformers available: {'Yes' if can_use_transformers else 'No'}")
    if not can_use_transformers:
        logger.info(f"Transformers status: {transformers_reason}")
    
    logger.info("=" * 50)
    logger.info("Server started successfully")

@app.get("/")
def read_root():
    return {"message": "FastAPI Backend Running"}

@app.get("/system-info")
def get_system_info():
    """Endpoint to get system information for the frontend"""
    system_info = HardwareDetector.detect_system()
    
    # Add additional backend information
    can_use_vllm, vllm_reason = HardwareDetector.can_use_vllm()
    can_use_transformers, transformers_reason = HardwareDetector.can_use_transformers()
    
    return {
        "os": system_info["os"],
        "architecture": system_info["architecture"],
        "python_version": system_info["python_version"],
        "torch_available": system_info.get("torch_available", False),
        "cuda_available": system_info.get("cuda_available", False),
        "mps_available": system_info.get("mps_available", False),
        "is_apple_silicon": system_info.get("is_apple_silicon", False),
        "gpu_name": system_info.get("gpu_name", "N/A"),
        "recommended_backend": system_info.get("recommended_backend", "cpu"),
        "vllm_available": can_use_vllm,
        "transformers_available": can_use_transformers,
        "vllm_status": vllm_reason,
        "transformers_status": transformers_reason
    }

# Criteria endpoints
@app.get("/criteria")
def list_criteria():
    """Get a list of all available criteria"""
    try:
        criteria_list = get_criteria_list()
        return {
            "criteria": criteria_list,
            "active": get_active_criteria()["name"]
        }
    except Exception as e:
        logger.error(f"Error listing criteria: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/criteria/active")
def get_active():
    """Get the currently active criteria configuration"""
    try:
        return get_active_criteria()
    except Exception as e:
        logger.error(f"Error getting active criteria: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/criteria/active")
def set_active(criteria: CriteriaSelection):
    """Set the active criteria by key"""
    try:
        if set_active_criteria(criteria.key):
            return {"success": True, "active": get_active_criteria()}
        else:
            raise HTTPException(status_code=404, detail=f"Criteria with key '{criteria.key}' not found")
    except Exception as e:
        logger.error(f"Error setting active criteria: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/criteria/custom")
def create_custom_criteria(criteria: CustomCriteriaCreate):
    """Add a new custom criteria configuration"""
    try:
        if add_custom_criteria(
            criteria.key,
            criteria.name,
            criteria.description,
            criteria.criteria,
            criteria.threshold
        ):
            return {"success": True, "message": f"Custom criteria '{criteria.name}' created"}
        else:
            raise HTTPException(status_code=400, detail=f"Could not create criteria '{criteria.key}'. Key may already be in use.")
    except Exception as e:
        logger.error(f"Error creating custom criteria: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/criteria/custom/{key}")
def remove_custom_criteria(key: str):
    """Delete a custom criteria configuration"""
    try:
        if delete_custom_criteria(key):
            return {"success": True, "message": f"Custom criteria '{key}' deleted"}
        else:
            raise HTTPException(status_code=404, detail=f"Custom criteria '{key}' not found")
    except Exception as e:
        logger.error(f"Error deleting custom criteria: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
def process_query(user_query: dict):
    try:
        query_text = user_query.get("user_query")
        if not query_text:
            raise ValueError("User query is empty or missing")
            
        generated_sql = get_qwen_generated_code(query_text)
        result = execute_sql_query(generated_sql)
        return {"generated_code": generated_sql, "result": result}
    except ValueError as e:
        logger.error(f"Value error in query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Runtime error in query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

app.include_router(diagnose_router)
