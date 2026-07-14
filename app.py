from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import hashlib
import uuid
import json
import datetime
import socket
import qrcode
import io
import base64
import os
import threading
import subprocess
import re
import atexit
from database import get_db, init_db

app = Flask(__name__)
# Đọc secret key từ biến môi trường (bảo mật hơn)
# Trên Railway: đặt biến SECRET_KEY trong Settings > Variables
app.secret_key = os.environ.get('SECRET_KEY', 'eco_coin_super_secret_key_local_only')

# Khởi tạo database ngay khi app load
# Dùng app_context() để hoạt động với cả gunicorn (Railway) và python app.py (local)
with app.app_context():
    init_db()

# ==============================================================
# BẢNG GIÁ VẬT LIỆU
# ==============================================================
ITEM_PRICES = {
    'plastic_small': {
        'name': 'Chai nhựa nhỏ',
        'detail': 'dưới 500ml',
        'price': 250,
        'icon': '🧴',
        'color': '#4fc3f7',
        'bg': 'rgba(79, 195, 247, 0.15)'
    },
    'plastic_large': {
        'name': 'Chai nhựa lớn',
        'detail': 'từ 500ml trở lên',
        'price': 300,
        'icon': '🍶',
        'color': '#29b6f6',
        'bg': 'rgba(41, 182, 246, 0.15)'
    },
    'can_small': {
        'name': 'Lon nhôm 330ml',
        'detail': 'lon nước ngọt',
        'price': 500,
        'icon': '🥫',
        'color': '#ffb74d',
        'bg': 'rgba(255, 183, 77, 0.15)'
    },
    'can_large': {
        'name': 'Lon nhôm 500ml',
        'detail': 'lon bia, nước tăng lực',
        'price': 700,
        'icon': '🍺',
        'color': '#ffa726',
        'bg': 'rgba(255, 167, 38, 0.15)'
    },
}

# ==============================================================
# HELPER FUNCTIONS
# ==============================================================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_lan_ip() -> str:
    """Lấy địa chỉ IP mạng LAN thực của máy tính (không phải localhost)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LAN_IP = get_lan_ip()  # Cache IP khi khoi dong

# ==============================================================
# PUBLIC URL – đọc từ biến môi trường (Railway tự cung cấp)
# Khi chạy local với tunnel, vẫn đọc từ public_url.txt
# ==============================================================

def get_public_base_url():
    """Lấy base URL công khai: Railway URL hoặc tunnel URL hoặc None."""
    # Railway tự cung cấp biến RAILWAY_PUBLIC_DOMAIN
    railway_domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    if railway_domain:
        return f"https://{railway_domain}"
    # Khi chạy local với tunnel
    if os.path.exists("public_url.txt"):
        with open("public_url.txt", "r") as f:
            url = f.read().strip()
        if url:
            return url
    return None

def generate_qr_base64(data: str) -> str:
    """Tạo QR code từ data, trả về chuỗi base64 để nhúng vào HTML."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=9,
        border=3,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0d2818", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def get_machine_user():
    """Lấy thông tin người dùng đang đăng nhập trên máy."""
    if 'machine_user_id' not in session:
        return None
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['machine_user_id'],)).fetchone()
    db.close()
    return user

# ==============================================================
# TEMPLATE FILTERS
# ==============================================================

@app.template_filter('currency')
def currency_filter(amount):
    """Định dạng tiền VNĐ: 1000 → 1.000đ"""
    return f"{int(amount):,}đ".replace(",", ".")

@app.template_filter('fmt_date')
def fmt_date_filter(dt_str):
    """Định dạng ngày giờ."""
    if not dt_str:
        return ''
    try:
        dt = datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%H:%M - %d/%m/%Y')
    except Exception:
        return str(dt_str)

# ==============================================================
# ROUTE DEBUG – chỉ dùng để kiểm tra, xóa sau khi ổn định
# ==============================================================

@app.route('/debug')
def debug_info():
    """Kiểm tra cấu hình server - xóa route này sau khi deploy ổn."""
    import os
    db_url = os.environ.get('DATABASE_URL', 'KHÔNG CÓ - đang dùng SQLite')
    # Ẩn password trong URL
    if '@' in db_url:
        parts = db_url.split('@')
        db_url = '***:***@' + parts[-1]
    try:
        db = get_db()
        db.execute('SELECT 1')
        db.close()
        db_status = '✅ Kết nối OK'
    except Exception as e:
        db_status = f'❌ Lỗi: {str(e)}'
    return f"""
    <h2>Debug Info</h2>
    <p><b>DATABASE_URL:</b> {db_url}</p>
    <p><b>DB Status:</b> {db_status}</p>
    <p><b>PORT:</b> {os.environ.get('PORT', '5000')}</p>
    <p><b>RAILWAY_DOMAIN:</b> {os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'không có')}</p>
    """

# ==============================================================
# ROUTES – QUẢN TRỊ VIÊN (ADMIN DASHBOARD)
# ==============================================================

def is_admin():
    return session.get('is_admin') == True

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if is_admin():
        return redirect(url_for('admin_dashboard'))
    
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        admin_pass = os.environ.get('ADMIN_PASSWORD', 'chamiucuason')
        if password == admin_pass:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Sai mật khẩu mất rồi bé ơi!'
            
    return render_template('admin.html', view='login', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_dashboard():
    if not is_admin():
        return redirect(url_for('admin_login'))
        
    db = get_db()
    
    # Lấy thống kê tổng quan
    total_users_query = db.execute("SELECT COUNT(id) as count FROM users").fetchone()
    total_users = total_users_query['count'] if total_users_query else 0
    
    total_items_query = db.execute("SELECT SUM(total_items) as count FROM users").fetchone()
    total_items = total_items_query['count'] if total_items_query and total_items_query['count'] else 0
    
    total_balance_query = db.execute("SELECT SUM(balance) as sum FROM users").fetchone()
    total_balance = total_balance_query['sum'] if total_balance_query and total_balance_query['sum'] else 0
    
    # Lấy danh sách người dùng
    users = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    db.close()
    
    return render_template('admin.html', 
                           view='dashboard',
                           total_users=total_users,
                           total_items=total_items,
                           total_balance=total_balance,
                           users=users)

# ==============================================================
# ROUTES – ỨNG DỤNG NGƯỜI DÙNG (MOBILE APP)
# ==============================================================

@app.route('/')
def index():
    """Trang chủ – chuyển đến đăng nhập hoặc dashboard."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    """Đăng ký tài khoản mới."""
    username = request.form.get('username', '').strip()
    phone    = request.form.get('phone', '').strip()
    password = request.form.get('password', '')
    next_url = request.form.get('next_url', '')

    if not username or not password:
        return render_template('index.html',
            error='Vui lòng điền đầy đủ thông tin!', tab='register')

    if len(password) < 6:
        return render_template('index.html',
            error='Mật khẩu phải có ít nhất 6 ký tự!', tab='register')

    db = get_db()
    try:
        db.execute(
            'INSERT INTO users (username, phone, password_hash) VALUES (?, ?, ?)',
            (username, phone or None, hash_password(password))
        )
        db.commit()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        session['user_id']  = user['id']
        session['username'] = user['username']
        return redirect(next_url if next_url else url_for('dashboard'))
    except sqlite3.IntegrityError:
        return render_template('index.html',
            error='Tên đăng nhập hoặc số điện thoại đã tồn tại!', tab='register', next_url=next_url)
    finally:
        db.close()

@app.route('/login', methods=['POST'])
def login():
    """Đăng nhập tài khoản."""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    next_url = request.form.get('next_url', '')

    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE (username = ? OR phone = ?) AND password_hash = ?',
        (username, username, hash_password(password))
    ).fetchone()
    db.close()

    if user:
        session['user_id']  = user['id']
        session['username'] = user['username']
        return redirect(next_url if next_url else url_for('dashboard'))

    return render_template('index.html',
        error='Điền cho đúng đi mấy má ơi!',
        tab='login',
        next_url=next_url)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

# ==============================================================
# ROUTES – DASHBOARD VÍ TIỀN
# ==============================================================

@app.route('/dashboard')
def dashboard():
    """Trang ví điện tử của người dùng."""
    if 'user_id' not in session:
        return redirect(url_for('index'))

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    raw_txs = db.execute(
        'SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 30',
        (session['user_id'],)
    ).fetchall()
    db.close()

    txs = []
    for tx in raw_txs:
        items = json.loads(tx['items_data'])
        txs.append({
            'id':          tx['id'],
            'token':       tx['token'],
            'amount':      tx['amount'],
            'items':       items,
            'total_items': sum(items.values()),
            'status':      tx['status'],
            'created_at':  tx['created_at'],
            'claimed_at':  tx['claimed_at'],
        })

    return render_template('dashboard.html',
        user=user,
        transactions=txs,
        item_prices=ITEM_PRICES)

# ==============================================================
# ROUTES – NHẬN THƯỞNG QUA QR
# ==============================================================

@app.route('/claim/<token>')
def claim_qr(token):
    """
    Người dùng quét QR trên điện thoại → mở URL này.
    Nếu chưa đăng nhập: chuyển đến trang login rồi quay lại.
    Nếu đã đăng nhập: cộng tiền vào ví ngay.
    """
    if 'user_id' not in session:
        return render_template('index.html',
            error='🎁 Đăng nhập để nhận tiền thưởng từ mã QR!',
            tab='login',
            next_url=url_for('claim_qr', token=token))

    db = get_db()
    tx = db.execute('SELECT * FROM transactions WHERE token = ?', (token,)).fetchone()

    if not tx:
        db.close()
        return render_template('claim.html', result='invalid')

    if tx['status'] in ('claimed', 'direct'):
        db.close()
        return render_template('claim.html', result='used')

    # Cộng tiền vào ví người dùng
    items       = json.loads(tx['items_data'])
    total_items = sum(items.values())
    now         = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db.execute(
        "UPDATE transactions SET status = 'claimed', user_id = ?, claimed_at = ? WHERE token = ?",
        (session['user_id'], now, token)
    )
    db.execute(
        'UPDATE users SET balance = balance + ?, total_items = total_items + ? WHERE id = ?',
        (tx['amount'], total_items, session['user_id'])
    )
    db.commit()
    db.close()

    return render_template('claim.html',
        result='success',
        amount=tx['amount'],
        items=items,
        item_prices=ITEM_PRICES)

# ==============================================================
# ROUTES – XAC THUC KHUON MAT (FACE API)
# ==============================================================

@app.route('/api/face_login', methods=['POST'])
def face_login():
    """
    Nhan face descriptor tu frontend (128 float), tim user co khuon mat giong nhat.
    mode: 'app' (dang nhap app) hoac 'machine' (dang nhap tren may)
    """
    data       = request.get_json()
    descriptor = data.get('descriptor')  # list 128 float
    mode       = data.get('mode', 'app')

    if not descriptor or len(descriptor) != 128:
        return jsonify({'success': False, 'error': 'Du lieu khuon mat khong hop le'})

    db    = get_db()
    users = db.execute(
        'SELECT id, username, face_descriptor FROM users WHERE face_descriptor IS NOT NULL'
    ).fetchall()
    db.close()

    if not users:
        return jsonify({'success': False, 'error': 'Chua co tai khoan nao dang ky khuon mat'})

    THRESHOLD  = 0.52  # Nguong: < 0.52 la cung nguoi, cang thap cang chat che
    best_user  = None
    best_dist  = float('inf')

    for user in users:
        stored = json.loads(user['face_descriptor'])
        # Euclidean distance giua 2 vector 128 chieu
        dist = sum((a - b) ** 2 for a, b in zip(descriptor, stored)) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best_user = user

    if best_user and best_dist < THRESHOLD:
        if mode == 'machine':
            session['machine_user_id']  = best_user['id']
            session['machine_username'] = best_user['username']
        else:
            session['user_id']  = best_user['id']
            session['username'] = best_user['username']
        return jsonify({'success': True, 'username': best_user['username']})

    return jsonify({'success': False, 'error': 'Khong nhan ra khuon mat. Thu lai hoac dung mat khau.'})


@app.route('/api/enroll_face', methods=['POST'])
def enroll_face():
    """Luu face descriptor cho user dang dang nhap tren app."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Chua dang nhap'})

    data       = request.get_json()
    descriptor = data.get('descriptor')

    if not descriptor or len(descriptor) != 128:
        return jsonify({'success': False, 'error': 'Du lieu khuon mat khong hop le'})

    db = get_db()
    db.execute('UPDATE users SET face_descriptor = ? WHERE id = ?',
               (json.dumps(descriptor), session['user_id']))
    db.commit()
    db.close()

    return jsonify({'success': True})


# ==============================================================
# ROUTES – MAN HINH MAY (KIOSK)
# ==============================================================

@app.route('/machine')
def machine():
    """Giao diện màn hình máy Eco Coin (kiosk mode)."""
    machine_user = get_machine_user()
    return render_template('machine.html',
        item_prices=ITEM_PRICES,
        machine_user=machine_user,
        open_form=None)

@app.route('/machine/login', methods=['POST'])
def machine_login():
    """Đăng nhập trực tiếp trên màn hình máy."""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE (username = ? OR phone = ?) AND password_hash = ?',
        (username, username, hash_password(password))
    ).fetchone()
    db.close()

    if user:
        session['machine_user_id']  = user['id']
        session['machine_username'] = user['username']
        return redirect(url_for('machine'))

    return render_template('machine.html',
        error='Sai tài khoản hoặc mật khẩu!',
        item_prices=ITEM_PRICES,
        machine_user=None,
        open_form='login')

@app.route('/machine/logout')
def machine_logout():
    """Đăng xuất khỏi màn hình máy."""
    session.pop('machine_user_id', None)
    session.pop('machine_username', None)
    return redirect(url_for('machine'))

@app.route('/machine/register', methods=['POST'])
def machine_register():
    """Đăng ký tài khoản mới trực tiếp trên màn hình máy."""
    username = request.form.get('username', '').strip()
    phone    = request.form.get('phone', '').strip()
    password = request.form.get('password', '')

    if not username or not password:
        return render_template('machine.html',
            error='Vui lòng điền đầy đủ thông tin đăng ký!',
            item_prices=ITEM_PRICES,
            machine_user=None,
            open_form='register')

    if len(password) < 6:
        return render_template('machine.html',
            error='Mật khẩu phải có ít nhất 6 ký tự!',
            item_prices=ITEM_PRICES,
            machine_user=None,
            open_form='register')

    db = get_db()
    try:
        db.execute(
            'INSERT INTO users (username, phone, password_hash) VALUES (?, ?, ?)',
            (username, phone or None, hash_password(password))
        )
        db.commit()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        session['machine_user_id']  = user['id']
        session['machine_username'] = user['username']
        return redirect(url_for('machine'))
    except sqlite3.IntegrityError:
        return render_template('machine.html',
            error='Tên đăng nhập hoặc số điện thoại đã tồn tại!',
            item_prices=ITEM_PRICES,
            machine_user=None,
            open_form='register')
    finally:
        db.close()

@app.route('/machine/submit', methods=['POST'])
def machine_submit():
    """
    Xử lý khi người dùng bỏ chai/lon vào và bấm xác nhận.

    - Nếu đã đăng nhập trên máy → tiền vào thẳng tài khoản (status='direct')
    - Nếu chưa đăng nhập (guest) → tạo QR code để quét bằng app (status='pending')
    """
    items        = {}
    total_amount = 0

    for key, info in ITEM_PRICES.items():
        qty = request.form.get(key, '0')
        try:
            qty = max(0, int(qty))
        except ValueError:
            qty = 0
        if qty > 0:
            items[key]    = qty
            total_amount += qty * info['price']

    machine_user = get_machine_user()

    if total_amount == 0:
        return render_template('machine.html',
            error='Vui long chon it nhat 1 chai hoac lon!',
            item_prices=ITEM_PRICES,
            machine_user=machine_user,
            open_form=None)

    try:
        token = str(uuid.uuid4())
        db    = get_db()

        if machine_user:
            # ── CHẾ ĐỘ ĐÃ ĐĂNG NHẬP: tiền vào thẳng tài khoản ──
            total_items = sum(items.values())
            db.execute(
                "INSERT INTO transactions (token, user_id, amount, items_data, status) "
                "VALUES (?, ?, ?, ?, 'direct')",
                (token, machine_user['id'], total_amount, json.dumps(items))
            )
            db.execute(
                'UPDATE users SET balance = balance + ?, total_items = total_items + ? WHERE id = ?',
                (total_amount, total_items, machine_user['id'])
            )
            db.commit()
            # Lấy lại user sau khi cập nhật balance
            updated_user = db.execute('SELECT * FROM users WHERE id = ?', (machine_user['id'],)).fetchone()
            db.close()

            return render_template('machine.html',
                item_prices=ITEM_PRICES,
                machine_user=updated_user,
                open_form=None,
                result={
                    'mode':     'direct',
                    'amount':   total_amount,
                    'items':    items,
                    'new_balance': updated_user['balance'],
                })

        else:
            # ── CHẾ ĐỘ KHÁCH: tạo QR để quét bằng app ──
            db.execute(
                "INSERT INTO transactions (token, amount, items_data, status) "
                "VALUES (?, ?, ?, 'pending')",
                (token, total_amount, json.dumps(items))
            )
            db.commit()
            db.close()

            # Luôn dùng Public URL (Railway) hoặc LAN IP
            base_url = get_public_base_url()
            if base_url:
                claim_url = base_url + url_for('claim_qr', token=token)
            else:
                port = request.host.split(':')[-1] if ':' in request.host else '5000'
                claim_url = f"http://{LAN_IP}:{port}" + url_for('claim_qr', token=token)
                
            qr_b64 = generate_qr_base64(claim_url)

            return render_template('machine.html',
                item_prices=ITEM_PRICES,
                machine_user=None,
                open_form=None,
                result={
                    'mode':      'qr',
                    'amount':    total_amount,
                    'items':     items,
                    'qr_image':  qr_b64,
                    'claim_url': claim_url,
                    'token':     token,
                })

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] machine_submit: {error_detail}")
        # Hiển thị lỗi thật để debug (xóa sau khi ổn định)
        return f"""
        <h2 style='color:red'>Lỗi Debug (tạm thời)</h2>
        <pre style='background:#111;color:#0f0;padding:20px;font-size:12px'>{error_detail}</pre>
        <a href='/machine'>← Quay lại</a>
        """, 500

# ==============================================================
# KHOI DONG SERVER
# ==============================================================

if __name__ == '__main__':
    init_db()
    print("=" * 55)
    print("  [*]  ECO COIN SERVER")
    print("=" * 55)
    print(f"  [APP]     http://localhost:5000")
    print(f"  [MACHINE] http://localhost:5000/machine")
    print(f"  [LAN]     http://{LAN_IP}:5000")
    print("=" * 55)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)