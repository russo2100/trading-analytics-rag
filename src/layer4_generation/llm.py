import os
import requests
import json
import logging
from typing import Optional, Dict, Any
from .interfaces import BaseLLM
from ..config import settings

logger = logging.getLogger(__name__)

class OpenRouterClient(BaseLLM):
    """Client for OpenRouter API (Access to Claude, GPT-4, etc.)"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.openrouter_api_key
        self.model = model or settings.openrouter_model
        self.base_url = settings.openrouter_base_url
        
        if not self.api_key:
            logger.warning("OpenRouter API Key is missing! Generation will fail.")
            
    def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Generate completion using OpenRouter API
        """
        if not self.api_key:
            return "Error: OpenRouter API Key not configured."
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/russo2100/trading-rag", # Optional
            "X-Title": "Trading Analytics RAG" # Optional
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            logger.info(f"Sending request to OpenRouter ({self.model})...")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=60
            )
            
            if response.status_code != 200:
                error_msg = f"API Error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return f"Error generation: {error_msg}"
                
            data = response.json()
            # Handle potential different response structures
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                
                # Log usage if available
                usage = data.get("usage", {})
                logger.info(f"Generated {usage.get('completion_tokens', '?')} tokens (Total: {usage.get('total_tokens', '?')})")
                
                return content
            else:
                 return f"Error: Unexpected response format: {data}"
            
        except Exception as e:
            logger.error(f"Failed to call OpenRouter: {e}")
            return f"Error: {str(e)}"

    def name(self) -> str:
        return self.model
