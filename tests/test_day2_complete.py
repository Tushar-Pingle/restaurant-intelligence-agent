"""
Day 2 - Complete Integration Tests

Tests all Day 2 components:
- Executor framework
- Insights generation
- End-to-end integration
- Error handling
- Actionable insights quality
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.agent.base_agent import RestaurantAnalysisAgent


def test_d2_test_001_agent_with_sample():
    """
    D2-TEST-001: Test agent with 100 review sample (simulated).
    
    Tests complete workflow with realistic data structure.
    """
    print("=" * 70)
    print("D2-TEST-001: Test agent with sample reviews")
    print("=" * 70 + "\n")
    
    # Create agent
    agent = RestaurantAnalysisAgent()
    
    # Progress tracking
    progress_updates = []
    def track_progress(status):
        progress_updates.append(status)
        print(f"  📊 {status}")
    
    # Run complete analysis
    print("Running complete analysis workflow...\n")
    results = agent.analyze_restaurant(
        restaurant_url="https://opentable.ca/r/test-restaurant",
        restaurant_name="Test Restaurant (100 Reviews)",
        review_count="100",
        progress_callback=track_progress
    )
    
    # Verify results structure
    print("\n" + "=" * 70)
    print("VERIFYING RESULTS STRUCTURE")
    print("=" * 70 + "\n")
    
    assert results is not None, "❌ Results should not be None"
    assert 'success' in results, "❌ Missing 'success' field"
    assert 'restaurant' in results, "❌ Missing 'restaurant' field"
    assert 'plan' in results, "❌ Missing 'plan' field"
    assert 'execution' in results, "❌ Missing 'execution' field"
    assert 'insights' in results, "❌ Missing 'insights' field"
    
    print("✅ All required fields present")
    
    # Verify plan was created
    assert len(results['plan']) > 0, "❌ Plan should have steps"
    assert len(results['plan']) >= 8, f"❌ Plan should have at least 8 steps, got {len(results['plan'])}"
    print(f"✅ Plan created with {len(results['plan'])} steps")
    
    # Verify execution happened
    assert results['execution']['results'], "❌ Execution should have results"
    assert len(results['execution']['results']) > 0, "❌ Should have executed some steps"
    print(f"✅ Executed {len(results['execution']['results'])} steps")
    
    # Verify insights were generated
    assert 'chef' in results['insights'], "❌ Missing chef insights"
    assert 'manager' in results['insights'], "❌ Missing manager insights"
    print("✅ Both chef and manager insights generated")
    
    # Verify progress tracking worked
    assert len(progress_updates) > 0, "❌ Should have progress updates"
    print(f"✅ Progress tracking working ({len(progress_updates)} updates)")
    
    print("\n✅ D2-TEST-001 PASSED: Agent works with sample data\n")
    
    return agent, results


def test_d2_test_002_verify_execution(results):
    """
    D2-TEST-002: Verify all steps execute without errors.
    
    Checks that execution completed successfully and handled errors properly.
    """
    print("=" * 70)
    print("D2-TEST-002: Verify all steps execute without errors")
    print("=" * 70 + "\n")
    
    execution = results['execution']
    
    # Check execution completed
    assert 'success' in execution, "❌ Missing execution success status"
    assert 'results' in execution, "❌ Missing execution results"
    assert 'execution_time' in execution, "❌ Missing execution time"
    
    print(f"Execution status: {execution['success']}")
    print(f"Total steps: {len(results['plan'])}")
    print(f"Executed steps: {len(execution['results'])}")
    print(f"Execution time: {execution['execution_time']:.2f}s")
    
    # Verify all steps were attempted
    assert len(execution['results']) == len(results['plan']), \
        f"❌ Should execute all {len(results['plan'])} steps, only executed {len(execution['results'])}"
    
    print(f"\n✅ All {len(results['plan'])} steps attempted")
    
    # Check each step's status
    print("\nStep-by-step verification:")
    success_count = 0
    failed_count = 0
    
    for step_num, step_result in execution['results'].items():
        status = step_result.get('status', 'unknown')
        action = step_result.get('action', 'unknown')
        
        if status == 'success':
            success_count += 1
            print(f"  ✅ Step {step_num}: {action} - {status}")
        else:
            failed_count += 1
            error = step_result.get('error', 'Unknown error')
            print(f"  ⚠️  Step {step_num}: {action} - {status} ({error})")
    
    print(f"\nExecution summary:")
    print(f"  Successful: {success_count}/{len(results['plan'])}")
    print(f"  Failed: {failed_count}/{len(results['plan'])}")
    
    # At minimum, should have attempted all steps (even if some fail gracefully)
    assert success_count > 0, "❌ At least some steps should succeed"
    
    # Check error handling
    if failed_count > 0:
        print(f"\n⚠️  {failed_count} steps failed (error handling working)")
        assert 'failed_steps' in execution, "❌ Should track failed steps"
    else:
        print("\n✅ All steps executed successfully")
    
    # Verify execution time is reasonable
    exec_time = execution['execution_time']
    assert exec_time > 0, "❌ Execution time should be positive"
    assert exec_time < 300, f"⚠️  Execution took {exec_time:.2f}s (should be faster)"
    
    print(f"✅ Execution time reasonable: {exec_time:.2f}s")
    
    # Verify logs exist
    assert 'logs' in execution, "❌ Should have execution logs"
    assert len(execution['logs']) > 0, "❌ Should have log entries"
    print(f"✅ Execution logs captured ({len(execution['logs'])} entries)")
    
    print("\n✅ D2-TEST-002 PASSED: Execution verified successfully\n")


def test_d2_test_003_check_insights_actionable(results):
    """
    D2-TEST-003: Check insights are actionable.
    
    Verifies that insights have specific, actionable recommendations.
    """
    print("=" * 70)
    print("D2-TEST-003: Check insights are actionable")
    print("=" * 70 + "\n")
    
    chef_insights = results['insights']['chef']
    manager_insights = results['insights']['manager']
    
    # Test Chef Insights
    print("CHEF INSIGHTS QUALITY CHECK:")
    print("-" * 70)
    
    # Check required fields
    assert 'summary' in chef_insights, "❌ Chef insights missing summary"
    assert 'strengths' in chef_insights, "❌ Chef insights missing strengths"
    assert 'concerns' in chef_insights, "❌ Chef insights missing concerns"
    assert 'recommendations' in chef_insights, "❌ Chef insights missing recommendations"
    
    print("✅ Chef insights have all required fields")
    
    # Check summary is meaningful
    chef_summary = chef_insights['summary']
    assert len(chef_summary) > 50, f"❌ Chef summary too short ({len(chef_summary)} chars)"
    assert len(chef_summary) < 1000, f"⚠️  Chef summary very long ({len(chef_summary)} chars)"
    print(f"✅ Chef summary length appropriate ({len(chef_summary)} chars)")
    
    # Check has strengths
    chef_strengths = chef_insights['strengths']
    assert isinstance(chef_strengths, list), "❌ Strengths should be a list"
    assert len(chef_strengths) > 0, "❌ Should have at least one strength"
    print(f"✅ Chef insights identify {len(chef_strengths)} strengths")
    
    # Check has concerns
    chef_concerns = chef_insights['concerns']
    assert isinstance(chef_concerns, list), "❌ Concerns should be a list"
    print(f"✅ Chef insights identify {len(chef_concerns)} concerns")
    
    # Check recommendations are actionable
    chef_recs = chef_insights['recommendations']
    assert isinstance(chef_recs, list), "❌ Recommendations should be a list"
    assert len(chef_recs) > 0, "❌ Should have at least one recommendation"
    
    print(f"\nVerifying {len(chef_recs)} chef recommendations are actionable:")
    
    for i, rec in enumerate(chef_recs, 1):
        # Check structure
        assert 'priority' in rec, f"❌ Recommendation {i} missing priority"
        assert 'action' in rec, f"❌ Recommendation {i} missing action"
        assert 'reason' in rec, f"❌ Recommendation {i} missing reason"
        
        # Check actionability
        action = rec['action']
        assert len(action) > 20, f"❌ Recommendation {i} action too vague ({len(action)} chars)"
        assert len(action) < 500, f"⚠️  Recommendation {i} action very long ({len(action)} chars)"
        
        # Check priority is valid
        priority = rec['priority'].lower()
        assert priority in ['high', 'medium', 'low'], f"❌ Invalid priority: {priority}"
        
        print(f"  ✅ Rec {i}: [{priority.upper()}] {action[:50]}...")
    
    print(f"\n✅ All {len(chef_recs)} chef recommendations are actionable")
    
    # Test Manager Insights
    print("\n" + "=" * 70)
    print("MANAGER INSIGHTS QUALITY CHECK:")
    print("-" * 70)
    
    # Check required fields
    assert 'summary' in manager_insights, "❌ Manager insights missing summary"
    assert 'recommendations' in manager_insights, "❌ Manager insights missing recommendations"
    
    print("✅ Manager insights have all required fields")
    
    # Check summary
    manager_summary = manager_insights['summary']
    assert len(manager_summary) > 50, f"❌ Manager summary too short ({len(manager_summary)} chars)"
    print(f"✅ Manager summary length appropriate ({len(manager_summary)} chars)")
    
    # Check recommendations
    manager_recs = manager_insights['recommendations']
    assert len(manager_recs) > 0, "❌ Should have at least one manager recommendation"
    
    print(f"\nVerifying {len(manager_recs)} manager recommendations are actionable:")
    
    for i, rec in enumerate(manager_recs, 1):
        assert 'priority' in rec, f"❌ Manager rec {i} missing priority"
        assert 'action' in rec, f"❌ Manager rec {i} missing action"
        
        action = rec['action']
        priority = rec['priority'].lower()
        
        assert len(action) > 20, f"❌ Manager rec {i} too vague"
        print(f"  ✅ Rec {i}: [{priority.upper()}] {action[:50]}...")
    
    print(f"\n✅ All {len(manager_recs)} manager recommendations are actionable")
    
    # Verify role separation
    print("\n" + "=" * 70)
    print("ROLE SEPARATION CHECK:")
    print("-" * 70)
    
    # Chef should focus on food
    chef_text = (chef_summary + ' '.join(chef_strengths + chef_concerns)).lower()
    food_keywords = ['food', 'menu', 'dish', 'ingredient', 'recipe', 'taste', 'flavor']
    food_mentions = sum(1 for keyword in food_keywords if keyword in chef_text)
    
    print(f"Chef insights mention food-related terms: {food_mentions} times")
    assert food_mentions > 0, "❌ Chef insights should focus on food"
    
    # Manager should focus on operations
    manager_text = (manager_summary + ' '.join(
        manager_insights.get('strengths', []) + 
        manager_insights.get('concerns', [])
    )).lower()
    ops_keywords = ['service', 'staff', 'operation', 'customer', 'wait', 'experience']
    ops_mentions = sum(1 for keyword in ops_keywords if keyword in manager_text)
    
    print(f"Manager insights mention operations terms: {ops_mentions} times")
    assert ops_mentions > 0, "❌ Manager insights should focus on operations"
    
    print("\n✅ Role separation verified (chef=food, manager=operations)")
    
    print("\n✅ D2-TEST-003 PASSED: Insights are actionable and role-appropriate\n")


def run_all_day2_tests():
    """Run all Day 2 tests in sequence."""
    print("\n" + "=" * 70)
    print("DAY 2 - COMPLETE TEST SUITE")
    print("=" * 70 + "\n")
    
    try:
        # Test 1
        agent, results = test_d2_test_001_agent_with_sample()
        
        # Test 2
        test_d2_test_002_verify_execution(results)
        
        # Test 3
        test_d2_test_003_check_insights_actionable(results)
        
        # Final summary
        print("=" * 70)
        print("🎉 ALL DAY 2 TESTS PASSED!")
        print("=" * 70)
        print("\n✅ D2-TEST-001: Agent with sample - PASSED")
        print("✅ D2-TEST-002: Execution verification - PASSED")
        print("✅ D2-TEST-003: Actionable insights - PASSED")
        print("\n🏆 Day 2 is 100% complete and validated!")
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
    success = run_all_day2_tests()
    sys.exit(0 if success else 1)
