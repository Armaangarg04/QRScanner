import os
import re
from flask import Flask, send_from_directory, jsonify, request
import qrcode
import io
from urllib.parse import urlparse

app = Flask(__name__, static_folder='.', static_url_path='')

# Serve HTML files
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<page>.html')
def serve_page(page):
    return send_from_directory('.', f'{page}.html')

# API endpoint for QR generation (SVG ONLY - no Pillow)
@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    try:
        # Get JSON data
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
            
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"success": False, "error": "Text is required"}), 400
        
        print(f"🔳 Generating QR for: {text[:50]}...")
        
        # SIMPLE SVG QR GENERATION - NO PILLOW NEEDED
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        
        # Create SVG image using qrcode's built-in SVG factory
        factory = qrcode.image.svg.SvgPathImage
        img = qr.make_image(image_factory=factory, fill_color="black", back_color="white")
        
        # Save to string (SVG format)
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

# URL Security Analysis API
@app.route('/api/check-url', methods=['POST'])
def check_url():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({"error": "No URL provided"}), 400
        
        # Parse URL
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Security checks
        suspicious_keywords = ['free', 'download', 'claim', 'won', 'bank', 'password', 'login', 'verify', 'reward', 'prize']
        suspicious_patterns = [
            r'\d{16}',  # Credit card
            r'bit\.ly|goo\.gl|tinyurl|shorte\.st',  # URL shorteners
        ]
        
        is_suspicious = False
        reasons = []
        
        # Check domain
        if len(domain) < 5:
            is_suspicious = True
            reasons.append("Short domain name")
        
        # Check for suspicious TLDs
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top', '.club']
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
                reasons.append(f"Suspicious keyword: {keyword}")
                break
        
        # Check patterns
        for pattern in suspicious_patterns:
            if re.search(pattern, url_lower):
                is_suspicious = True
                reasons.append("Suspicious URL pattern")
                break
        
        # Check for IP address
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', domain):
            is_suspicious = True
            reasons.append("IP address instead of domain")
        
        # Risk score
        risk_score = min(0.9, 0.1 + len(reasons) * 0.2) if is_suspicious else 0.1
        
        return jsonify({
            "url": url,
            "domain": domain,
            "suspicious": is_suspicious,
            "warning": "⚠️ Suspicious URL detected: " + ", ".join(reasons) if is_suspicious else "✅ URL appears safe",
            "domain_prob": risk_score,
            "reasons": reasons if is_suspicious else []
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
