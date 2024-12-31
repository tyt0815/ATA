from datetime import datetime

def log(content):
        now = datetime.now()
        now_str = now.strftime("[%Y-%m-%d %H:%M:%S]")
        print(now_str, content)