from flask import Flask, send_from_directory, jsonify, request
import qrcode
import io
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

# API endpoint for QR generation
@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    try:
        data = request.json
        text = data.get('text', 'Test QR')
        
        qr = qrcode.make(text)
        buffered = io.BytesIO()
        qr.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return jsonify({
            "success": True,
            "qr_code": f"data:image/png;base64,{img_str}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
