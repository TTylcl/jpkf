
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core import llm_client


get_llm_client = llm_client.LLMClient()