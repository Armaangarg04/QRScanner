from flask import Flask, render_template, request, jsonify
import os
import traceback

app = Flask(__name__)

# Try to import QR code with fallback
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("Note: qrcode module not installed")

try:
    from io import BytesIO
    import base64
    IO_AVAILABLE = True
except ImportError:
    IO_AVAILABLE = False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/scanner')
def scanner():
    return render_template('scanner.html')

@app.route('/qr-generator')
def qr_generator():
    return render_template('generator.html')

@app.route('/api/check-url', methods=['POST'])
def check_url():
    try:
        data = request.get_json()
        url = data.get('url', '')
        
        return jsonify({
            'suspicious': False,
            'warning': None,
            'domain': url.split('/')[2] if '//' in url else url,
            'domain_prob': 0.1
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'success': False, 'error': 'No text provided'}), 400
        
        # Check if we can generate image QR
        can_generate_image = QR_AVAILABLE and IO_AVAILABLE
        
        response = {
            'success': True,
            'text': text,
            'message': 'QR code generated successfully' if can_generate_image else 'Text received',
        }
        
        if can_generate_image:
            try:
                # Generate actual QR image
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(text)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Convert to base64
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                buffer.seek(0)
                img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
                
                response['qr_image_url'] = f'data:image/png;base64,{img_base64}'
                response['message'] = 'QR code image generated successfully'
                
            except Exception as img_error:
                print(f"Image generation failed: {img_error}")
                can_generate_image = False
        
        # Always include ASCII preview
        response['ascii_qr'] = generate_ascii_preview(text)
        
        if not can_generate_image:
            response['note'] = 'Install qrcode and pillow for image generation'
            
        return jsonify(response)
            
    except Exception as e:
        print(f"Error in generate_qr: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to process request'
        }), 500

def generate_ascii_preview(text, width=40):
    """Generate simple ASCII art"""
    border_top = "╔" + "═" * (width - 2) + "╗"
    border_bottom = "╚" + "═" * (width - 2) + "╝"
    
    result = [border_top]
    
    # Add text in middle
    middle_line = f"║ {text[:width-4].center(width-4)} ║"
    result.append(middle_line)
    
    result.append(border_bottom)
    return "\n".join(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
