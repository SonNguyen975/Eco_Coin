import os
import urllib.request
import subprocess
import re
import sys
import threading

CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
EXE_NAME = "cloudflared.exe"

def download_cloudflared():
    if not os.path.exists(EXE_NAME):
        print("[*] Dang tai cong cu Cloudflare Tunnel...")
        urllib.request.urlretrieve(CLOUDFLARED_URL, EXE_NAME)
        print("[*] Da tai xong!")

def start_tunnel():
    print("[*] Khoi dong Tunnel, vui long cho trong giay lat...")
    # cloudflared prints logs to stderr
    process = subprocess.Popen(
        [f".\\{EXE_NAME}", "tunnel", "--url", "http://localhost:5000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    public_url = None
    url_pattern = re.compile(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)')

    while True:
        line = process.stderr.readline()
        if not line:
            break
        
        # In ra log cho dễ debug nếu cần
        # print(line, end="")

        match = url_pattern.search(line)
        if match and not public_url:
            public_url = match.group(1)
            print("\n" + "="*50)
            print(f"🚀 PUBLIC URL DA SAN SANG: {public_url}")
            print("="*50)
            print("[*] URL nay da duoc luu vao public_url.txt")
            print("[*] Ma QR tao ra tu gio se dung link nay, ban co the quet bang 4G!")
            print("[*] Cu de cua so terminal nay chay ngam...\n")
            
            with open("public_url.txt", "w") as f:
                f.write(public_url)

if __name__ == "__main__":
    try:
        download_cloudflared()
        start_tunnel()
    except KeyboardInterrupt:
        print("\n[*] Dang dong Tunnel...")
        if os.path.exists("public_url.txt"):
            os.remove("public_url.txt")
        sys.exit(0)
