import qrcode
import uuid
import datetime

def calculate_reward(small_bottles, large_bottles):
    """
    Tính tổng tiền thưởng dựa trên số lượng vỏ chai
    Chai nhỏ (small): 250đ
    Chai to (large): 300đ
    """
    total_amount = (small_bottles * 250) + (large_bottles * 300)
    return total_amount

def generate_reward_qr(amount):
    """
    Tạo mã QR chứa thông tin giao dịch để người dùng quét
    """
    # Tạo một mã giao dịch duy nhất (Transaction ID) để tránh quét lại nhiều lần
    transaction_id = str(uuid.uuid4())[:8] 
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Dữ liệu sẽ được nhúng vào QR Code. 
    # Trong thực tế, đây thường là 1 đường link API web, ví dụ:
    # qr_data = f"https://your-domain.com/claim_reward?id={transaction_id}&amount={amount}"
    
    # Ở đây ta dùng định dạng JSON cơ bản để demo
    qr_data = f'{{"transaction_id": "{transaction_id}", "amount_vnd": {amount}, "time": "{timestamp}"}}'
    
    print(f"[*] Đang tạo QR Code cho số tiền: {amount}đ...")
    print(f"[*] Dữ liệu ẩn trong QR: {qr_data}")

    # Cấu hình hình dáng mã QR
    qr = qrcode.QRCode(
        version=1, # Kích thước QR (1 đến 40)
        error_correction=qrcode.constants.ERROR_CORRECT_L, # Mức độ sửa lỗi
        box_size=10, # Kích thước mỗi ô pixel
        border=4, # Độ dày viền trắng
    )
    
    qr.add_data(qr_data)
    qr.make(fit=True)

    # Tạo hình ảnh QR và hiển thị
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Lưu file ảnh (tùy chọn)
    filename = f"reward_qr_{transaction_id}.png"
    img.save(filename)
    
    # Hiển thị ảnh lên màn hình
    img.show()
    print(f"[*] Đã hiển thị QR Code! Người dùng có thể quét để nhận {amount}đ.")

# ==========================================
# CHẠY THỬ NGHIỆM HỆ THỐNG
# ==========================================
if __name__ == "__main__":
    print("--- HỆ THỐNG THU GOM CHAI NHỰA ---")
    
    # Giả lập việc cảm biến máy đã đếm xong số chai người dùng bỏ vào
    so_chai_nho = int(input("Nhập số lượng chai nhỏ (250đ/chai): "))
    so_chai_to = int(input("Nhập số lượng chai to (300đ/chai): "))
    
    # Tính tiền
    tong_tien = calculate_reward(so_chai_nho, so_chai_to)
    
    if tong_tien > 0:
        print(f"\n=> Tổng tiền thưởng của bạn là: {tong_tien}đ")
        # Gọi hàm sinh QR hiển thị lên màn hình
        generate_reward_qr(tong_tien)
    else:
        print("Vui lòng cho chai vào máy để nhận thưởng!")