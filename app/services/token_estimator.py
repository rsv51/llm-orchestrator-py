"""
Token estimation service for providers that don't return usage info.
"""
import re
from typing import List, Dict, Any


class TokenEstimator:
    """Estimate token usage when provider doesn't return it."""
    
    @staticmethod
    def estimate_messages_tokens(messages: List[Dict[str, Any]]) -> int:
        """
        Estimate tokens for input messages.
        
        Rough estimation:
        - English: ~4 chars = 1 token
        - Chinese: ~1.5 chars = 1 token
        - Add overhead for message structure
        """
        total_chars = 0
        
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            
            # Add overhead for role and structure (~10 tokens per message)
            total_chars += 40  # ~10 tokens
        
        # Mixed estimation
        english_chars = len(re.findall(r'[a-zA-Z0-9\s\p{P}]', str(total_chars)))
        chinese_chars = total_chars - english_chars
        
        estimated_tokens = int(
            (english_chars / 4.0) + (chinese_chars / 1.5)
        )
        
        return max(estimated_tokens, 10)  # Minimum 10 tokens
    
    @staticmethod
    def estimate_completion_tokens(content: str) -> int:
        """
        Estimate tokens for completion content.
        
        Args:
            content: Response content string
            
        Returns:
            Estimated token count
        """
        if not content:
            return 0
        
        # Count different character types
        english_chars = len(re.findall(r'[a-zA-Z0-9\s]', content))
        chinese_chars = len(content) - english_chars
        
        # Estimation formula
        estimated_tokens = int(
            (english_chars / 4.0) + (chinese_chars / 1.5)
        )
        
        return max(estimated_tokens, 1)