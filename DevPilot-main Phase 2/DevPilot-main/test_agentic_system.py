"""
Test script for the DevPilot Agentic System
"""

import asyncio
import sys

async def test_system():
    print("=" * 60)
    print("Testing DevPilot Agentic System")
    print("=" * 60)
    
    try:
        from src.dev_pilot.core.agentic_system import AgenticSystem
        print("[OK] AgenticSystem import successful")
    except Exception as e:
        print(f"[ERROR] Failed to import AgenticSystem: {e}")
        return
    
    # Create a mock LLM for testing
    class MockLLM:
        def invoke(self, prompt):
            return type('Response', (), {'content': 'Mock response for testing'})()
        def with_structured_output(self, schema):
            return self
    
    try:
        llm = MockLLM()
        system = AgenticSystem(llm=llm)
        print("[OK] AgenticSystem created successfully")
    except Exception as e:
        print(f"[ERROR] Failed to create AgenticSystem: {e}")
        return
    
    try:
        # Initialize the system
        success = await system.initialize()
        print(f"[OK] Initialization success: {success}")
    except Exception as e:
        print(f"[ERROR] Failed to initialize: {e}")
        return
    
    try:
        # Check system status
        status = system.get_system_status()
        print(f"[OK] System initialized: {status['initialized']}")
        print(f"[OK] Registered agents: {list(status['agents'].keys())}")
        print(f"[OK] Workflow engine status: {status['workflow_engine']}")
    except Exception as e:
        print(f"[ERROR] Failed to get status: {e}")
    
    try:
        # Create a test project
        project = await system.create_project('Test Project', ['Build a test app'])
        print(f"[OK] Created project: {project['project_id']}")
    except Exception as e:
        print(f"[ERROR] Failed to create project: {e}")
    
    try:
        # Shutdown
        await system.shutdown()
        print("[OK] System shutdown complete")
    except Exception as e:
        print(f"[ERROR] Failed to shutdown: {e}")
    
    print("=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_system())
