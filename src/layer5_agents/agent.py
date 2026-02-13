import logging
import re
from typing import List, Dict, Any, Optional
from .tools import BaseTool
from ..layer4_generation.llm import BaseLLM
from .prompts import REACT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class ReActAgent:
    """
    Agent implementing ReAct pattern (Reason + Act)
    """
    
    def __init__(self, llm: BaseLLM, tools: List[BaseTool], max_steps: int = 5):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.max_steps = max_steps
        self.history = [] # List of (query, answer) tuples
        
    def run(self, query: str) -> str:
        """Execute the ReAct loop"""
        logger.info(f"Agent starting for query: '{query}'")
        
        # 1. Prepare initial prompt
        tool_desc = "\n".join([f"{t.name}: {t.description}" for t in self.tools.values()])
        tool_names = ", ".join(self.tools.keys())
        
        # Build context from history
        history_str = ""
        if self.history:
            history_str = "PREVIOUS CONVERSATION:\n"
            for q, a in self.history[-3:]: # Keep last 3 turns
                history_str += f"Q: {q}\nA: {a}\n\n"
        
        base_prompt = REACT_SYSTEM_PROMPT.format(
            tool_descriptions=tool_desc,
            tool_names=tool_names,
            query=query
        )
        
        # Inject history before the main query if needed, or modify system prompt
        # For simplicity, we prepend history to the query in the prompt
        if history_str:
            base_prompt = base_prompt.replace(f"Question: {query}", f"{history_str}Question: {query}")
        
        current_prompt = base_prompt
        
        # 2. Main Loop

        for step in range(self.max_steps):
            logger.info(f"Step {step+1}/{self.max_steps}")
            
            # Generate LLM response
            response = self.llm.generate(current_prompt, temperature=0.0, max_tokens=500)
            logger.debug(f"LLM Response:\n{response}")
            
            # Use streaming/append approach
            current_prompt += f"\n{response}"
            
            # Parse Action
            action, action_input = self._parse_action(response)

            
            if action:
                logger.info(f"Action: {action}({action_input})")
                
                # Execute Tool
                tool = self.tools.get(action)
                if tool:
                    observation = tool.run(action_input)
                else:
                    observation = f"Error: Tool '{action}' not found."
                    
                logger.info(f"Observation: {observation[:100]}...")
                
                # Append Observation
                current_prompt += f"\nObservation: {observation}\nThought:"
                
            elif "Final Answer:" in response:
                final_answer = response.split("Final Answer:")[-1].strip()
                self.history.append((query, final_answer))
                return final_answer
            else:
                # If no action and no final answer, force final answer or stop
                # For now, let's assume LLM will eventually output something useful
                logger.warning("No action or final answer detected. Trying to continue...")
                current_prompt += "\nThought: I should provide a Final Answer or define an Action."

                
        return "I could not find an answer within the step limit."

    def _parse_action(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """Parse 'Action: Tool\nAction Input: Input' from text"""
        # Look for last occurrence of Action/Input
        action_match = re.search(r"Action:\s*(.*?)\nAction Input:\s*(.*)", text, re.DOTALL)
        
        if action_match:
            action = action_match.group(1).strip()
            action_input = action_match.group(2).strip().split('\n')[0] # Take only first line of input
            return action, action_input
            
        return None, None
