from dotenv import load_dotenv
import os

load_dotenv()

env = os.environ

SESSDATA = env.get('SESSDATA', '')
BILI_JCT = env.get('BILI_JCT', '')
BUVID3 = env.get('BUVID3', '')
DEDE_USER_ID = env.get('DEDE_USER_ID', '')
AT_TIME_VALUE = env.get('AT_TIME_VALUE', '')