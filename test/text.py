
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils import logger


logger.add_log(level="info",message="sadsadfsafasdfsdfsdfasdf测试消息",module='机器人')
