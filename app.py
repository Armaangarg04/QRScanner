from flask import Flask, render_template, request, jsonify, send_from_directory
import qrcode
import base64
import io

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scanner')
def scanner():
    return render_template('scanner.html')

@app.route('/generator')
def generator():
    return render_template('generator.html')

@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    try:
        data = request.json
        text = data.get('text', '')
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return jsonify({
            "success": True,
            "qr_code": f"data:image/png;base64,{img_str}",
            "text": text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/check-url', methods=['POST'])
def check_url():
    # Simple URL check without ML
    import re
    url = request.json.get('url', '')
    
    # Basic checks
    suspicious_keywords = ['free', 'download', 'claim', 'won', 'bank', 'password']
    is_suspicious = any(keyword in url.lower() for keyword in suspicious_keywords)
    
    return jsonify({
        "url": url,
        "domain": url.split('//')[-1].split('/')[0] if '//' in url else url.split('/')[0],
        "suspicious": is_suspicious,
        "warning": "⚠️ Suspicious URL detected" if is_suspicious else "✅ URL appears safe",
        "domain_prob": 0.8 if is_suspicious else 0.1,
        "content_prob": 0.7 if is_suspicious else 0.1
    })

if __name__ == '__main__':
    app.run(debug=True)
