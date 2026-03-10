import sys
import os

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.router_agent import RouterAgent
from orchestrator.executor import Executor
from config.logger import get_logger

logger = get_logger("SmokeTest")

def run_test():
    logger.info("Starting System Smoke Test...")
    
    try:
        logger.info("Instantiating RouterAgent...")
        router = RouterAgent()
        logger.info("RouterAgent initialized successfully.")
    except Exception as e:
        logger.error(f"RouterAgent failed to initialize: {e}")
        sys.exit(1)
        
    try:
        logger.info("Instantiating Executor...")
        executor = Executor()
        logger.info("Executor initialized successfully.")
    except Exception as e:
        logger.error(f"Executor failed to initialize: {e}")
        sys.exit(1)
        
    logger.info("Smoke Test Completed Successfully. System Core is stable.")

if __name__ == "__main__":
    run_test()
