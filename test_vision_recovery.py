
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to sys.path so we can import vision_agent
sys.path.append('/Users/oscar/moltbot')

from vision_agent import VisionAgent

class TestVisionAgentRecovery(unittest.TestCase):

    def setUp(self):
        self.agent = VisionAgent()
        # Mock external dependencies to avoid real API/System calls
        self.agent.capture_screen = MagicMock(return_value="/tmp/mock_screenshot.png")
        self.agent.capture_screen_fast = MagicMock(return_value="/tmp/mock_screenshot_fast.png")
        self.agent.start_realtime_capture = MagicMock(return_value=(MagicMock(), "/tmp/mock_capture"))
        self.agent.extract_key_frames = MagicMock(return_value=["/tmp/mock_frame.png"])
        self.agent.locate_element = MagicMock(return_value={"found": True, "coordinates": {"x": 100, "y": 200}, "description": "Mock Target"})

    @patch('vision_agent.VisionAgent.vision_analyze')
    @patch('vision_agent.VisionAgent.perform_action')
    def test_auto_recovery_execution(self, mock_perform, mock_analyze):
        # Setup the scenario:
        # 1. Step is "Click Button"
        # 2. First attempt fails (implicitly, we simulate the feedback saying so)
        # 3. Feedback says "Failed, but try clicking 'Recovery Button'"
        # 4. Agent should execute "Click Recovery Button"
        # 5. Agent should verify again

        # Mock perform_action to return True (action successful)
        mock_perform.return_value = True

        # Mock analyze_realtime_feedback (which uses vision_analyze internally)
        # We need to mock what vision_analyze returns when called for feedback
        # The agent calls vision_analyze multiple times:
        # 1. perceive_state (before action) -> returns state json
        # 2. locate_element (optional)
        # 3. analyze_realtime_feedback -> returns feedback json WITH next_action
        # 4. perceive_state (after recovery) -> returns state json
        # 5. verify_result (after recovery) -> returns success json

        # We'll use a side_effect to return different responses based on the prompt/order
        
        def vision_side_effect(screenshot, prompt):
            # 1. Feedback analysis (looking for "current_state", "next_action")
            if "next_action" in prompt: 
                return {
                    "success": True, 
                    "analysis": '''{
                        "success": false,
                        "current_state": "Popup blocking button",
                        "stuck": true,
                        "stuck_reason": "Popup detected",
                        "next_action": {
                            "action": "click",
                            "target": "Close Popup Button",
                            "description": "Click the X to close the popup"
                        }
                    }'''
                }
            # 2. Verification (looking for "success")
            elif "expected_result" in prompt or "预期结果" in prompt:
                return {
                    "success": True,
                    "analysis": '{"success": true, "reason": "Popup gone, button clicked"}'
                }
            # 3. State perception (default)
            else:
                 return {
                    "success": True,
                    "analysis": '{"active_app": "MockApp", "ui_elements": ["Button"], "state_description": "Ready"}'
                }

        mock_analyze.side_effect = vision_side_effect

        # Define the step
        step = {
            "step_number": 1,
            "action": "click",
            "target": "Submit Button",
            "expected_result": "Form Submitted"
        }

        # Run execute_step
        print("\n--- Starting Test ---")
        result = self.agent.execute_step(step)
        print("--- Test Finished ---\n")

        # Assertions
        
        # 1. Verify perform_action was called TWICE
        #    Once for the original action ("Submit Button")
        #    Once for the recovery action ("Close Popup Button")
        self.assertEqual(mock_perform.call_count, 2, "perform_action should be called twice (original + recovery)")
        
        # Check arguments of the calls
        args_list = mock_perform.call_args_list
        
        # First call: Original action
        original_call_args = args_list[0]
        self.assertEqual(original_call_args[0][0], "click")
        # Note: the target passed to perform_action might be the resolved element dict or the mock one
        
        # Second call: Recovery action
        recovery_call_args = args_list[1]
        self.assertEqual(recovery_call_args[0][0], "click")
        # The second call uses the 'found_target' dict which has coordinates but not necessarily the 'target' string key
        # verify coordinates match the mock
        self.assertEqual(recovery_call_args[0][1]['coordinates']['x'], 100)
        self.assertEqual(recovery_call_args[0][1]['description'], "Mock Target")

        # 2. Verify result is successful (recovered)
        self.assertTrue(result['success'])
        self.assertTrue(result.get('recovered', False), "Result should be marked as recovered")

if __name__ == '__main__':
    unittest.main()
