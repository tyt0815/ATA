from datetime import datetime
import os

def log(content, end = '\n'):
    print(log_prefix(), content, end=end)
        
def save_log(content, file_path):
    now_str = log_prefix()
    print(now_str, f'log saved at {file_path}')
    with open(os.path.join(file_path, now_str+'.log'), 'w') as f:
        f.write(content)
    
def log_prefix():
    return datetime.now().strftime("[%Y-%m-%d %Hh%Mm%Ss]")