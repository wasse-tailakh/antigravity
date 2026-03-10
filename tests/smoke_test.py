"""
Smoke tests to verify Phase 1 stabilization.

These tests check that:
1. All imports work correctly
2. Logging system is functional  
3. Error handling works as expected
4. Basic agent initialization works
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.logger import LoggerSetup, get_logger

# Setup logging
LoggerSetup.setup(name="smoke_test", level=10)
logger = get_logger(__name__)


def test_imports():
    """Test that all imports work correctly."""
    print("\n" + "="*60)
    print("TEST 1: Testing Imports")
    print("="*60)
    
    try:
        logger.info("Testing config imports...")
        from config import settings, get_logger
        logger.info("Config imports successful")
        
        logger.info("Testing agent imports...")
        from agents import BaseAgent, ClaudeAgent, OpenAIAgent, GeminiAgent, RouterAgent
        logger.info("Agent imports successful")
        
        logger.info("Testing skills imports...")
        from skills import FileSkill, ShellSkill, GitSkill
        logger.info("Skills imports successful")
        
        logger.info("Testing orchestrator imports...")
        from orchestrator import Planner, Executor
        logger.info("Orchestrator imports successful")
        
        print("PASS: All imports successful!")
        return True
    except Exception as e:
        logger.error(f"Import test failed: {e}", exc_info=True)
        print(f"FAIL: Import test failed: {e}")
        return False


def test_logging():
    """Test that logging system works."""
    print("\n" + "="*60)
    print("TEST 2: Testing Logging System")
    print("="*60)
    
    try:
        test_logger = get_logger("test_module")
        test_logger.debug("Debug message")
        test_logger.info("Info message")
        test_logger.warning("Warning message")
        test_logger.error("Error message")
        
        print("PASS: Logging system working!")
        return True
    except Exception as e:
        print(f"FAIL: Logging test failed: {e}")
        return False


def test_skills():
    """Test that skills can be instantiated."""
    print("\n" + "="*60)
    print("TEST 3: Testing Skills Initialization")
    print("="*60)
    
    try:
        from skills import FileSkill, ShellSkill, GitSkill
        
        logger.info("Initializing FileSkill...")
        file_skill = FileSkill(project_root=str(project_root))
        logger.info(f"FileSkill initialized: {file_skill.name}")
        
        logger.info("Initializing ShellSkill...")
        shell_skill = ShellSkill()
        logger.info(f"ShellSkill initialized: {shell_skill.name}")
        
        logger.info("Initializing GitSkill...")
        git_skill = GitSkill()
        logger.info(f"GitSkill initialized: {git_skill.name}")
        
        print("PASS: All skills initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"Skills test failed: {e}", exc_info=True)
        print(f"FAIL: Skills test failed: {e}")
        return False


def test_agents():
    """Test that agents can be instantiated."""
    print("\n" + "="*60)
    print("TEST 4: Testing Agent Initialization")
    print("="*60)
    
    try:
        from agents import ClaudeAgent, OpenAIAgent, GeminiAgent
        
        logger.info("Initializing ClaudeAgent...")
        claude = ClaudeAgent()
        logger.info(f"ClaudeAgent initialized: {claude.name}")
        
        logger.info("Initializing OpenAIAgent...")
        openai_agent = OpenAIAgent()
        logger.info(f"OpenAIAgent initialized: {openai_agent.name}")
        
        logger.info("Initializing GeminiAgent...")
        gemini = GeminiAgent()
        logger.info(f"GeminiAgent initialized: {gemini.name}")
        
        print("PASS: All agents initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"Agent test failed: {e}", exc_info=True)
        print(f"FAIL: Agent test failed: {e}")
        return False


def test_router():
    """Test RouterAgent initialization."""
    print("\n" + "="*60)
    print("TEST 5: Testing RouterAgent")
    print("="*60)
    
    try:
        from agents import RouterAgent
        
        logger.info("Initializing RouterAgent...")
        router = RouterAgent()
        logger.info(f"RouterAgent initialized: {router.name}")
        logger.info(f"Available agents: {list(router.agents.keys())}")
        
        print("PASS: RouterAgent initialized successfully!")
        print(f"   Available agents: {list(router.agents.keys())}")
        return True
    except Exception as e:
        logger.error(f"Router test failed: {e}", exc_info=True)
        print(f"FAIL: Router test failed: {e}")
        return False


def test_orchestrator():
    """Test Orchestrator components."""
    print("\n" + "="*60)
    print("TEST 6: Testing Orchestrator Components")
    print("="*60)
    
    try:
        from orchestrator import Planner, Executor
        
        logger.info("Initializing Planner...")
        planner = Planner()
        logger.info("Planner initialized")
        
        logger.info("Initializing Executor...")
        executor = Executor()
        logger.info("Executor initialized")
        
        print("PASS: Orchestrator components initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"Orchestrator test failed: {e}", exc_info=True)
        print(f"FAIL: Orchestrator test failed: {e}")
        return False


def main():
    """Run all smoke tests."""
    print("\n" + "#"*60)
    print("#" + " "*18 + "PHASE 1 SMOKE TESTS" + " "*19 + "#")
    print("#"*60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Logging", test_logging()))
    results.append(("Skills", test_skills()))
    results.append(("Agents", test_agents()))
    results.append(("Router", test_router()))
    results.append(("Orchestrator", test_orchestrator()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name:20} {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED - Phase 1 is stable!")
    else:
        print("SOME TESTS FAILED - Please review errors above")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
