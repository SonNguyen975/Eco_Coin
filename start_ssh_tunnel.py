import subprocess
import re
import sys
import time

print("[*] Khoi tao SSH Tunnel...")

cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:5000", "nokey@localhost.run"]

process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

public_url = None
url_pattern = re.compile(r'(https://[a-zA-Z0-9.-]+\.lhr\.life)')

while True:
    line = process.stdout.readline()
    if not line:
        break
    
    # print(line, end="") # Debug if needed
    
    match = url_pattern.search(line)
    if match and not public_url:
        public_url = match.group(1)
        print("\n" + "="*50)
        print(f"[*] PUBLIC URL DA SAN SANG: {public_url}")
        print("="*50)
        print("[*] URL nay da duoc luu vao public_url.txt")
        
        with open("public_url.txt", "w") as f:
            f.write(public_url)
            
        print("[*] Tunnel dang hoat dong... (Khong tat cua so nay)")
