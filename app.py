import os
from flask import Flask, render_template, jsonify, request, send_from_directory
import qrcode
import io
import base64

# Get the absolute path to the templates directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

print(f"Base directory: {BASE_DIR}")
print(f"Templates directory: {TEMPLATES_DIR}")
print(f"Templates exist: {os.path.exists(TEMPLATES_DIR)}")
print(f"Templates files: {os.listdir(TEMPLATES_DIR) if os.path.exists(TEMPLATES_DIR) else 'NO TEMPLATES'}")

# Initialize Flask with absolute paths
app = Flask(__name__, 
            template_folder=TEMPLATES_DIR,
            static_folder=STATIC_DIR)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/scanner')
def scanner():
    return render_template('scanner.html')

@app.route('/generator')
def generator():
    return render_template('generator.html')

@app.route('/test')
def test():
    return f"""
    <h1>Debug Info</h1>
    <p>Base Dir: {BASE_DIR}</p>
    <p>Templates Dir: {TEMPLATES_DIR}</p>
    <p>Templates Exist: {os.path.exists(TEMPLATES_DIR)}</p>
    <p>Templates Files: {os.listdir(TEMPLATES_DIR) if os.path.exists(TEMPLATES_DIR) else 'None'}</p>
    <p><a href="/">Home</a></p>
    """

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

# Serve static files
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(STATIC_DIR, path)

if __name__ == '__main__':
    app.run(debug=True)
