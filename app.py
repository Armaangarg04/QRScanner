import re
from urllib.parse import urlparse

# Add this route to your existing app.py
@app.route('/api/check-url', methods=['POST'])
def check_url():
    try:
        data = request.json
        url = data.get('url', '')
        
        if not url:
            return jsonify({"error": "No URL provided"}), 400
        
        # Parse the URL
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Basic security checks
        suspicious_keywords = ['free', 'download', 'claim', 'won', 'bank', 'password', 'login', 'verify']
        suspicious_patterns = [
            r'\d{16}',  # Credit card numbers
            r'bit\.ly|goo\.gl|tinyurl',  # URL shorteners
        ]
        
        # Check for suspicious content
        is_suspicious = False
        reasons = []
        
        # Check domain length (very short domains can be suspicious)
        if len(domain) < 5:
            is_suspicious = True
            reasons.append("Very short domain name")
        
        # Check for keywords
        url_lower = url.lower()
        for keyword in suspicious_keywords:
            if keyword in url_lower:
                is_suspicious = True
                reasons.append(f"Contains suspicious keyword: '{keyword}'")
                break
        
        # Check for patterns
        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                is_suspicious = True
                reasons.append("Matches suspicious pattern")
                break
        
        # Calculate risk score (simple example)
        risk_score = 0.7 if is_suspicious else 0.1
        
        return jsonify({
            "url": url,
            "domain": domain,
            "suspicious": is_suspicious,
            "warning": "⚠️ This URL appears suspicious. Reasons: " + ", ".join(reasons) if is_suspicious else "✅ This URL appears safe",
            "domain_prob": risk_score,
            "reasons": reasons if is_suspicious else []
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
