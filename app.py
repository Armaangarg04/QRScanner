import os
import re
from flask import Flask, send_from_directory, jsonify, request
import qrcode
import io
from urllib.parse import urlparse
from qrcode.image.svg import SvgPathImage
import base64

app = Flask(__name__, static_folder='.', static_url_path='')

# Serve HTML files
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<page>.html')
def serve_page(page):
    return send_from_directory('.', f'{page}.html')

# API endpoint for QR generation
@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"success": False, "error": "Text is required"}), 400
        
        print(f"🔳 Generating QR for: {text[:50]}...")
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        
        img = qr.make_image(image_factory=SvgPathImage, fill_color="black", back_color="white")
        
        stream = io.BytesIO()
        img.save(stream)
        svg_string = stream.getvalue().decode('utf-8')
        
        return jsonify({
            "success": True,
            "qr_code": svg_string,
            "format": "svg",
            "text": text
        })
        
    except Exception as e:
        print(f"❌ QR Generation Error: {str(e)}")
        return jsonify({"success": False, "error": f"QR generation failed: {str(e)}"}), 500

# ✅ NEW: Simple QR scan API (for uploaded images)
@app.route('/api/scan-qr', methods=['POST'])
def scan_qr():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"error": "No image data provided"}), 400
        
        # Extract base64 image data
        image_data = data['image']
        if 'base64,' in image_data:
            image_data = image_data.split('base64,')[1]
        
        # Decode base64
        image_bytes = base64.b64decode(image_data)
        
        # Save to temp file (for debugging)
        with open('temp_qr.png', 'wb') as f:
            f.write(image_bytes)
        
        # For now, return a simple test response
        # In production, you'd use a QR decoding library like pyzbar or cv2
        return jsonify({
            "success": True,
            "text": "https://www.example.com",
            "note": "QR scanning via API coming soon. Currently using test data."
        })
        
    except Exception as e:
        print(f"❌ QR Scan Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ✅ FIXED: URL Security Analysis API
@app.route('/api/check-url', methods=['POST', 'GET'])
def check_url():
    try:
        if request.method == 'GET':
            url = request.args.get('url', '')
        else:
            data = request.get_json()
            url = data.get('url', '').strip()
        
        if not url:
            return jsonify({"error": "No URL provided"}), 400
        
        print(f"🔍 Checking URL: {url}")
        
        # Parse URL
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Security checks
        suspicious_keywords = ['free', 'download', 'claim', 'won', 'bank', 'password', 'login', 'verify', 'reward', 'prize', 'hack', 'crack']
        suspicious_patterns = [
            r'\d{16}',  # Credit card
            r'bit\.ly|goo\.gl|tinyurl|shorte\.st|ow\.ly',  # URL shorteners
        ]
        
        is_suspicious = False
        reasons = []
        
        # Check domain
        if len(domain) < 5:
            is_suspicious = True
            reasons.append("Short domain name")
        
        # Check for suspicious TLDs
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top', '.club', '.info', '.biz']
        for tld in suspicious_tlds:
            if domain.endswith(tld):
                is_suspicious = True
                reasons.append(f"Suspicious TLD: {tld}")
                break
        
        # Check keywords
        url_lower = url.lower()
        for keyword in suspicious_keywords:
            if keyword in url_lower:
                is_suspicious = True
                reasons.append(f"Suspicious keyword: '{keyword}'")
                break
        
        # Check patterns
        for pattern in suspicious_patterns:
            if re.search(pattern, url_lower):
                is_suspicious = True
                reasons.append("Suspicious URL pattern detected")
                break
        
        # Check for IP address
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', domain):
            is_suspicious = True
            reasons.append("IP address instead of domain name")
        
        # Risk score
        risk_score = min(0.95, 0.1 + len(reasons) * 0.2) if is_suspicious else 0.05
        
        return jsonify({
            "url": url,
            "domain": domain,
            "suspicious": is_suspicious,
            "warning": "⚠️ Suspicious URL detected: " + ", ".join(reasons) if is_suspicious else "✅ URL appears safe",
            "domain_prob": round(risk_score, 2),
            "reasons": reasons if is_suspicious else [],
            "secure": parsed.scheme == 'https'
        })
        
    except Exception as e:
        print(f"❌ URL Check Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Health check endpoint
@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "QR Scanner API"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
