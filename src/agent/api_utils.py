"""
API utility functions with retry logic
"""
import time
from typing import Any, Callable
from anthropic import Anthropic

def call_claude_with_retry(
    client: Anthropic,
    model: str,
    max_tokens: int,
    temperature: float,
    messages: list,
    max_retries: int = 3,
    initial_delay: float = 2.0
) -> Any:
    """
    Call Claude API with exponential backoff retry logic.
    
    Args:
        client: Anthropic client
        model: Model name
        max_tokens: Max tokens
        temperature: Temperature
        messages: Messages list
        max_retries: Max retry attempts
        initial_delay: Initial delay in seconds
    
    Returns:
        API response
    """
    delay = initial_delay
    
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages
            )
            return response
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if it's a retryable error
            if 'overloaded' in error_str or '529' in error_str or 'rate' in error_str:
                if attempt < max_retries - 1:
                    print(f"⚠️  API overloaded, retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
                else:
                    print(f"❌ API still overloaded after {max_retries} attempts")
                    raise
            else:
                # Non-retryable error
                raise
    
    raise Exception("Max retries exceeded")
