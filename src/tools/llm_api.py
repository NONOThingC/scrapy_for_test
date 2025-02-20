"""
LLM API module for interacting with language models.
"""

import asyncio
import subprocess
from typing import Optional
from loguru import logger

async def query_llm(prompt: str, provider: str = "openai") -> str:
    """Query the language model.
    
    Args:
        prompt (str): The prompt to send to the model
        provider (str, optional): The LLM provider to use. Defaults to "openai".
        
    Returns:
        str: The model's response
    """
    try:
        # Run the LLM API command
        cmd = ["python", "./tools/llm_api.py", "--prompt", prompt]
        if provider:
            cmd.extend(["--provider", provider])
            
        # Execute command and get output
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"LLM API error: {stderr.decode()}")
            return f"Error: Failed to get response from {provider}"
            
        response = stdout.decode().strip()
        return response
        
    except Exception as e:
        logger.error(f"Error querying LLM: {str(e)}")
        return "Error: Failed to query language model" 