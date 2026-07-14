import qrcode

# Địa chỉ IP mạng LAN máy tính của bạn
IP_ADDRESS = "192.168.0.114" 
web_link = f"http://{IP_ADDRESS}:5000"

print(f"[*] Đang tạo QR Code cho đường link: {web_link}")

# Tạo và hiển thị mã QR
qr = qrcode.make(web_link)
qr.show()