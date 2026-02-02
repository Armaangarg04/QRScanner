from flask import Flask, render_template, jsonify, request
import qrcode
import io
import base64

app = Flask(__name__, template_folder='templates')  # ← IMPORTANT!

@app.route('/')
def home():
    return render_template('index.html')  # ← Uses templates/index.html

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
    app.run(debug=True)
