from flask import Flask, render_template, request, jsonify, send_file
import qrcode
from io import BytesIO
import base64
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')  # Your main page

@app.route('/qr-generator')
def qr_generator_page():
    return render_template('qr_generator.html')  # The HTML above

@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is empty'}), 400
        
        print(f"Generating QR code for: {text[:50]}...")
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save image to bytes
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Convert to base64 for embedding in HTML
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
        
        # Generate ASCII QR (simplified version)
        ascii_qr = generate_ascii_qr(text)
        
        return jsonify({
            'success': True,
            'text': text,
            'qr_image_url': f'data:image/png;base64,{img_base64}',
            'ascii_qr': ascii_qr,
            'message': 'QR code generated successfully'
        })
        
    except Exception as e:
        print(f"Error generating QR: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate QR code'
        }), 500

def generate_ascii_qr(text, width=40):
    """Generate a simple ASCII representation of QR code"""
    try:
        # For simplicity, create a basic ASCII representation
        # In reality, you'd use a proper ASCII QR generator
        lines = []
        lines.append("┌" + "─" * width + "┐")
        
        # Add text in the middle
        padding = (width - len(text)) // 2
        if padding > 0:
            lines.append("│" + " " * padding + text + " " * (width - padding - len(text)) + "│")
        else:
            # Text too long, wrap it
            for i in range(0, len(text), width):
                chunk = text[i:i+width]
                lines.append("│" + chunk.ljust(width) + "│")
        
        lines.append("└" + "─" * width + "┘")
        return "\n".join(lines)
    except:
        return "QR Code (ASCII preview not available)"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
