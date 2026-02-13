import unittest
from unittest.mock import MagicMock
from src.layer5_agents.agent import ReActAgent
from src.layer5_agents.tools import CalculatorTool

class TestReActParser(unittest.TestCase):
    def test_parse_action(self):
        agent = ReActAgent(MagicMock(), [])
        
        text = """
        Thought: I need to calculate
        Action: Calculator
        Action Input: 2 + 2
        """
        action, input_ = agent._parse_action(text)
        self.assertEqual(action, "Calculator")
        self.assertEqual(input_, "2 + 2")
        
    def test_parse_action_no_input(self):
        agent = ReActAgent(MagicMock(), [])
        text = "Thought: Nothing to do"
        action, _ = agent._parse_action(text)
        self.assertIsNone(action)

if __name__ == '__main__':
    unittest.main()
