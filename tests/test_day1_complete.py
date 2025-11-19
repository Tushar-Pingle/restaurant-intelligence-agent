"""
Day 1 - Complete Integration Tests

Tests all Day 1 components:
- Agent initialization
- Planning module
- Reasoning logs
- Plan quality and structure
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.agent.base_agent import RestaurantAnalysisAgent


def test_d1_test_001_run_agent_with_miku():
    """
    D1-TEST-001: Run agent with Miku reviews sample
    
    Tests that agent can create a plan for a real restaurant (Miku).
    """
    print("=" * 70)
    print("D1-TEST-001: Run agent with Miku reviews sample")
    print("=" * 70 + "\n")
    
    # Create agent
    agent = RestaurantAnalysisAgent()
    
    # Create plan for Miku
    plan = agent.create_analysis_plan(
        restaurant_url="https://opentable.ca/r/miku-vancouver",
        restaurant_name="Miku Restaurant",
        review_count="500"
    )
    
    # Verify plan was created
    assert plan is not None, "❌ Plan should not be None"
    assert len(plan) > 0, "❌ Plan should have steps"
    assert len(plan) >= 10, f"❌ Plan should have at least 10 steps, got {len(plan)}"
    
    print(f"\n✅ TEST PASSED: Generated plan with {len(plan)} steps")
    print("\nPlan steps:")
    for step in plan:
        print(f"  {step['step']}. {step['action']} - {step['reason'][:50]}...")
    
    return agent, plan


def test_d1_test_002_verify_reasoning_logs(agent):
    """
    D1-TEST-002: Verify reasoning logs are coherent
    
    Tests that the agent's reasoning logs make sense and are properly formatted.
    """
    print("\n" + "=" * 70)
    print("D1-TEST-002: Verify reasoning logs are coherent")
    print("=" * 70 + "\n")
    
    # Get reasoning logs
    logs = agent.get_reasoning_log()
    
    # Check logs exist
    assert len(logs) > 0, "❌ Should have reasoning logs"
    
    print(f"Total log entries: {len(logs)}\n")
    
    # Verify log format
    for i, log in enumerate(logs):
        # Check log has timestamp
        assert "[" in log and "]" in log, f"❌ Log {i} missing timestamp: {log}"
        
        # Check log has content after timestamp
        parts = log.split("]", 1)
        assert len(parts) == 2, f"❌ Log {i} malformed: {log}"
        
        timestamp_part = parts[0]
        message_part = parts[1].strip()
        
        # Check timestamp format [YYYY-MM-DD HH:MM:SS]
        assert len(timestamp_part) > 10, f"❌ Log {i} has invalid timestamp: {timestamp_part}"
        
        # Check message is not empty
        assert len(message_part) > 0, f"❌ Log {i} has empty message"
    
    print("✅ All logs have proper format (timestamp + message)")
    
    # Verify logs are coherent (tell a story)
    log_messages = [log.split("]", 1)[1].strip() for log in logs]
    
    # Check for key milestones
    assert any("initialized" in msg.lower() for msg in log_messages), \
        "❌ Missing initialization log"
    
    assert any("creating analysis plan" in msg.lower() for msg in log_messages), \
        "❌ Missing plan creation log"
    
    assert any("generated plan" in msg.lower() for msg in log_messages), \
        "❌ Missing plan generation log"
    
    assert any("validation" in msg.lower() for msg in log_messages), \
        "❌ Missing validation log"
    
    print("✅ Logs are coherent and tell the agent's story")
    
    # Display sample logs
    print("\nSample reasoning log entries:")
    print("-" * 70)
    for log in logs[-5:]:
        print(f"  {log}")
    print("-" * 70)
    
    print("\n✅ TEST PASSED: Reasoning logs are coherent and well-formatted")


def test_d1_test_003_check_plan_structure(plan):
    """
    D1-TEST-003: Check plan includes all necessary steps
    
    Validates the plan has required actions and proper structure.
    """
    print("\n" + "=" * 70)
    print("D1-TEST-003: Check plan includes all necessary steps")
    print("=" * 70 + "\n")
    
    # Extract all actions from plan
    actions = [step['action'] for step in plan]
    
    print(f"Plan has {len(actions)} actions:")
    for action in actions:
        print(f"  ✓ {action}")
    print()
    
    # Check required actions are present
    required_actions = [
        'scrape_reviews',
        'discover_menu_items',
        'discover_aspects'
    ]
    
    missing = []
    for required in required_actions:
        if required not in actions:
            missing.append(required)
    
    assert len(missing) == 0, f"❌ Missing required actions: {missing}"
    print("✅ All required actions present (scrape, discover menu, discover aspects)")
    
    # Check each step has required fields
    required_fields = ['step', 'action', 'params', 'reason']
    
    for i, step in enumerate(plan, start=1):
        for field in required_fields:
            assert field in step, f"❌ Step {i} missing '{field}' field"
            
            # Check no null/empty values
            assert step[field] is not None, f"❌ Step {i} has null '{field}'"
            
            if field == 'reason':
                assert len(step[field]) > 0, f"❌ Step {i} has empty '{field}'"
    
    print("✅ All steps have required fields (step, action, params, reason)")
    
    # Check step numbering is sequential
    for i, step in enumerate(plan, start=1):
        assert step['step'] == i, f"❌ Step numbering error: expected {i}, got {step['step']}"
    
    print("✅ Step numbering is sequential (1, 2, 3...)")
    
    # Check data types
    for i, step in enumerate(plan, start=1):
        assert isinstance(step['step'], int), f"❌ Step {i}: 'step' should be int"
        assert isinstance(step['action'], str), f"❌ Step {i}: 'action' should be string"
        assert isinstance(step['params'], dict), f"❌ Step {i}: 'params' should be dict"
        assert isinstance(step['reason'], str), f"❌ Step {i}: 'reason' should be string"
    
    print("✅ All data types correct (int, str, dict, str)")
    
    # Check recommended actions are present
    recommended = ['analyze_sentiment', 'detect_anomalies', 'generate_insights_chef']
    present_recommended = [action for action in recommended if action in actions]
    
    print(f"\n✅ Recommended actions present: {len(present_recommended)}/{len(recommended)}")
    for action in present_recommended:
        print(f"  ✓ {action}")
    
    print("\n✅ TEST PASSED: Plan structure is valid and complete")


def run_all_day1_tests():
    """Run all Day 1 tests in sequence."""
    print("\n" + "=" * 70)
    print("DAY 1 - COMPLETE TEST SUITE")
    print("=" * 70 + "\n")
    
    try:
        # Test 1
        agent, plan = test_d1_test_001_run_agent_with_miku()
        
        # Test 2
        test_d1_test_002_verify_reasoning_logs(agent)
        
        # Test 3
        test_d1_test_003_check_plan_structure(plan)
        
        # Final summary
        print("\n" + "=" * 70)
        print("🎉 ALL DAY 1 TESTS PASSED!")
        print("=" * 70)
        print("\n✅ D1-TEST-001: Run agent with Miku - PASSED")
        print("✅ D1-TEST-002: Verify reasoning logs - PASSED")
        print("✅ D1-TEST-003: Check plan structure - PASSED")
        print("\n🏆 Day 1 is 100% complete and validated!")
        print("=" * 70 + "\n")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_day1_tests()
    sys.exit(0 if success else 1)
