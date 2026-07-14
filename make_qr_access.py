"""
Tạo QR code cho các đường link truy cập Eco Coin trên mạng LAN.
Chạy: python make_qr_access.py
"""
import qrcode
import socket

def get_local_ip():
    """Lấy IP mạng LAN của máy tính."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "192.168.0.114"

import os

IP = get_local_ip()
PORT = 5000

public_url = None
if os.path.exists("public_url.txt"):
    with open("public_url.txt", "r") as f:
        public_url = f.read().strip()
        
if public_url:
    base_url = public_url
    print(f"[*] Da tim thay Public URL: {public_url}")
else:
    base_url = f"http://{IP}:{PORT}"

links = {
    "app_home":    f"{base_url}",
    "app_machine": f"{base_url}/machine",
}

for name, url in links.items():
    qr = qrcode.make(url)
    filename = f"qr_{name}.png"
    qr.save(filename)
    print(f"[OK] Da luu: {filename}  ->  {url}")

print("\n=== HUONG DAN ===")
if public_url:
    print(f"  Da dung Public Tunnel. Ban co the quet QR bang mang 4G!")
else:
    print(f"  Dien thoai phai cung mang WiFi voi may tinh!")
    
print(f"  App nguoi dung : {base_url}")
print(f"  Man hinh may   : {base_url}/machine")
print(f"Hoac quet QR file qr_app_home.png / qr_app_machine.png")
