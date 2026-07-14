/**
 * ECO COIN – Face Authentication Module
 * Uses face-api.js for browser-based face recognition (no server ML needed)
 */

const FACE_MODEL_URL   = '/static/models';
const MATCH_THRESHOLD  = 0.52; // Euclidean distance; <0.52 = same person

let _modelsLoaded  = false;
let _modelsLoading = false;

// ── Load face-api.js models ──────────────────────────────────
async function loadFaceModels(statusEl) {
    if (_modelsLoaded) return true;
    if (_modelsLoading) {
        while (_modelsLoading) await _sleep(200);
        return _modelsLoaded;
    }
    _modelsLoading = true;
    _setStatus(statusEl, 'Đang tải AI nhận diện khuôn mặt...', 'loading');
    try {
        await Promise.all([
            faceapi.nets.ssdMobilenetv1.loadFromUri(FACE_MODEL_URL),
            faceapi.nets.faceLandmark68Net.loadFromUri(FACE_MODEL_URL),
            faceapi.nets.faceRecognitionNet.loadFromUri(FACE_MODEL_URL),
        ]);
        _modelsLoaded  = true;
        _modelsLoading = false;
        return true;
    } catch(e) {
        _modelsLoading = false;
        console.error('[FaceAuth]', e);
        _setStatus(statusEl, 'Lỗi tải AI. Vui lòng dùng mật khẩu.', 'error');
        return false;
    }
}

// ── Camera helpers ────────────────────────────────────────────
async function _openCamera(videoEl) {
    const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: 480, height: 360 }
    });
    videoEl.srcObject = stream;
    await videoEl.play();
    return stream;
}
function _closeCamera(stream) {
    stream?.getTracks().forEach(t => t.stop());
}

// ── Get face descriptor from video frame ─────────────────────
async function _getDescriptor(videoEl) {
    const opts      = new faceapi.SsdMobilenetv1Options({ minConfidence: 0.5 });
    const detection = await faceapi
        .detectSingleFace(videoEl, opts)
        .withFaceLandmarks()
        .withFaceDescriptor();
    return detection ? Array.from(detection.descriptor) : null;
}

// ── Status helper ─────────────────────────────────────────────
function _setStatus(el, msg, type = '') {
    if (!el) return;
    el.textContent = msg;
    el.className   = 'face-status ' + type;
}

function _sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ════════════════════════════════════════════════════════════
// FACE LOGIN MODAL
// ════════════════════════════════════════════════════════════

let _loginStream   = null;
let _loginInterval = null;
let _loginScanning = false;

async function openFaceLogin(mode = 'app') {
    const modal   = document.getElementById('faceLoginModal');
    const status  = document.getElementById('faceLoginStatus');
    const video   = document.getElementById('faceLoginVideo');
    const overlay = document.getElementById('faceLoginOverlay');

    modal.classList.add('visible');
    _loginScanning = false;

    // Load models
    const ok = await loadFaceModels(status);
    if (!ok) return;

    // Open camera
    _setStatus(status, 'Đang mở camera...', 'loading');
    try {
        _loginStream = await _openCamera(video);
    } catch(e) {
        _setStatus(status, '❌ Không thể mở camera. Vui lòng cấp quyền.', 'error');
        return;
    }

    _setStatus(status, '👀 Nhìn thẳng vào camera – đang quét tự động...', 'scanning');
    _loginScanning = true;
    if (overlay) overlay.style.display = 'block';

    // Auto-scan every 2 seconds
    _loginInterval = setInterval(async () => {
        if (!_loginScanning) return;
        const desc = await _getDescriptor(video);
        if (!desc) {
            _setStatus(status, '🔍 Không thấy khuôn mặt. Nhìn thẳng vào camera...', 'scanning');
            return;
        }

        _setStatus(status, '⚡ Đang nhận diện...', 'loading');
        _loginScanning = false; // pause scanning during network call

        try {
            const res  = await fetch('/api/face_login', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ descriptor: desc, mode })
            });
            const data = await res.json();

            if (data.success) {
                clearInterval(_loginInterval);
                _setStatus(status, `✅ Xin chào, ${data.username}! Đang vào...`, 'success');
                _closeCamera(_loginStream);
                setTimeout(() => {
                    window.location.href = mode === 'machine' ? '/machine' : '/dashboard';
                }, 1000);
            } else {
                _setStatus(status, '❓ ' + data.error + '. Thử lại...', 'scanning');
                _loginScanning = true;
            }
        } catch(e) {
            _setStatus(status, '⚠️ Lỗi mạng. Thử lại...', 'error');
            _loginScanning = true;
        }
    }, 2200);
}

function closeFaceLogin() {
    _loginScanning = false;
    clearInterval(_loginInterval);
    _closeCamera(_loginStream);
    _loginStream = null;
    document.getElementById('faceLoginModal')?.classList.remove('visible');
}

// ════════════════════════════════════════════════════════════
// FACE ENROLLMENT MODAL (Dashboard)
// ════════════════════════════════════════════════════════════

let _enrollStream = null;

async function openFaceEnroll() {
    const modal  = document.getElementById('faceEnrollModal');
    const status = document.getElementById('faceEnrollStatus');
    const video  = document.getElementById('faceEnrollVideo');
    const btn    = document.getElementById('faceEnrollBtn');

    modal.classList.add('visible');
    if (btn) btn.disabled = true;

    const ok = await loadFaceModels(status);
    if (!ok) return;

    _setStatus(status, 'Đang mở camera...', 'loading');
    try {
        _enrollStream = await _openCamera(video);
    } catch(e) {
        _setStatus(status, '❌ Không thể mở camera.', 'error');
        return;
    }

    _setStatus(status, '😊 Nhìn thẳng vào camera, sau đó nhấn "Chụp khuôn mặt"', 'scanning');
    if (btn) btn.disabled = false;
}

async function captureEnrollFace() {
    const status = document.getElementById('faceEnrollStatus');
    const video  = document.getElementById('faceEnrollVideo');
    const btn    = document.getElementById('faceEnrollBtn');

    if (btn) btn.disabled = true;
    _setStatus(status, '⚡ Đang phân tích khuôn mặt...', 'loading');

    const desc = await _getDescriptor(video);
    if (!desc) {
        _setStatus(status, '❌ Không phát hiện khuôn mặt. Thử lại.', 'error');
        if (btn) btn.disabled = false;
        return;
    }

    try {
        const res  = await fetch('/api/enroll_face', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ descriptor: desc })
        });
        const data = await res.json();

        if (data.success) {
            _setStatus(status, '✅ Đăng ký khuôn mặt thành công!', 'success');
            _closeCamera(_enrollStream);
            setTimeout(closeFaceEnroll, 1500);
        } else {
            _setStatus(status, '❌ ' + data.error, 'error');
            if (btn) btn.disabled = false;
        }
    } catch(e) {
        _setStatus(status, '⚠️ Lỗi mạng.', 'error');
        if (btn) btn.disabled = false;
    }
}

function closeFaceEnroll() {
    _closeCamera(_enrollStream);
    _enrollStream = null;
    document.getElementById('faceEnrollModal')?.classList.remove('visible');
}
