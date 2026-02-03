from flask import Flask, send_from_directory, jsonify, request
import qrcode
import base64
import os

app = Flask(__name__, static_folder='.', static_url_path='')

# Serve HTML files
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<page>.html')
def serve_page(page):
    return send_from_directory('.', f'{page}.html')

# API endpoint for QR generation (without Pillow)
@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    try:
        data = request.json
        text = data.get('text', 'Test QR')
        
        # Generate QR code using pure qrcode (no Pillow)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        
        # Create image matrix (no Pillow)
        matrix = qr.get_matrix()
        
        # Create simple ASCII QR for now
        # We'll return text instead of image temporarily
        ascii_qr = ''
        for row in matrix:
            ascii_qr += ''.join(['██' if cell else '  ' for cell in row]) + '\n'
        
        return jsonify({
            "success": True,
            "text": text,
            "ascii_qr": ascii_qr,
            "message": "QR generated successfully! Upgrade to image version soon."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
