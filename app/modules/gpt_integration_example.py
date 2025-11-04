from typing import Dict, Any
from nlp_input_processor import build_gpt_payload, format_for_gpt
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel


def call_gpt_with_preprocessing(user_query: str, user_profile: Dict[str, Any] = None):
    """
    Complete flow: Preprocess with NLP, then call GPT-4o using PydanticAI
    
    Args:
        user_query: Raw user input
        user_profile: User profile data (optional)
    
    Returns:
        GPT-4o response with enhanced context
    """
    # Step 1: Preprocess the query
    payload = build_gpt_payload(user_query, user_profile or {})
    
    # Step 2: Create enhanced system prompt
    system_prompt = create_enhanced_prompt(payload)
    
    # Step 3: Initialize PydanticAI agent with GPT-4o
    model = OpenAIModel('gpt-4o')
    agent = Agent(
        model=model,
        system_prompt=system_prompt
    )
    

    return {
        "payload": payload,
        "system_prompt": system_prompt,
        "query": payload['original_query'],
        "note": "Uncomment PydanticAI code to make actual API call"
    }
