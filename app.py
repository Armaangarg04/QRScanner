from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import re
import json
from pathlib import Path
import numpy as np
from urllib.parse import urlparse
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import joblib
import qrcode
import io
import base64
import time

# Initialize Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)

# Global settings
DOMAIN_PROB_THRESHOLD = 0.50
CONTENT_PROB_THRESHOLD = 0.85
HEURISTIC_HITS_THRESHOLD = 3
REQUIRE_BOTH_STRONG = True

# Popular domains list
POPULAR_DOMAINS = [
    "google.com", "youtube.com", "facebook.com", "amazon.com", "apple.com",
    "microsoft.com", "gmail.com", "twitter.com", "instagram.com", "wikipedia.org",
    "linkedin.com", "paypal.com", "bing.com", "reddit.com"
]

# Edit distance function
def edit_distance(a, b):
    la, lb = len(a), len(b)
    dp = [[0]*(lb+1) for _ in range(la+1)]
    for i in range(la+1):
        dp[i][0] = i
    for j in range(lb+1):
        dp[0][j] = j
    for i in range(1, la+1):
        for j in range(1, lb+1):
            cost = 0 if a[i-1]==b[j-1] else 1
            dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)
    return dp[la][lb]

# Domain features
def make_domain_features(domain, candidate_list=POPULAR_DOMAINS):
    d = domain.lower()
    labels = d.split('.')
    if len(labels) >= 2:
        base = '.'.join(labels[-2:])
    else:
        base = d
    features = []
    distances = [edit_distance(base, p) for p in candidate_list]
    min_dist = min(distances)
    mean_dist = float(sum(distances))/len(distances)
    features.append(min_dist)
    features.append(mean_dist)
    features.append(min_dist / max(1, len(base)))
    features.append(len(base))
    features.append(sum(c.isdigit() for c in base))
    features.append(base.count('-'))
    max_run = 1
    run = 1
    for i in range(1, len(base)):
        if base[i] == base[i-1]:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    features.append(max_run)
    vowels = sum(1 for c in base if c in 'aeiou')
    features.append(vowels / max(1, len(base)))
    return np.array(features, dtype=float)

def synthesize_domain_examples():
    X = []
    y = []
    for d in POPULAR_DOMAINS:
        base = d
        X.append(make_domain_features(base))
        y.append(0)
        def add_variant(s, variant):
            X.append(make_domain_features(variant))
            y.append(1)
        add_variant(d, d.replace('o','0') if 'o' in d else d + '0')
        if '.' in d:
            s2 = d.replace('.', '')
            add_variant(d, s2)
        add_variant(d, d.replace('g','gg',1) if 'g' in d else 'x'+d)
        s = list(d)
        s[0] = chr(((ord(s[0]) - 97 + 1) % 26) + 97) if s[0].isalpha() else s[0]
        add_variant(d, ''.join(s))
    extras = ["mybank.com", "example.org", "safesite.net", "my-office.com"]
    for e in extras:
        X.append(make_domain_features(e))
        y.append(0)
    return np.vstack(X), np.array(y)

def train_domain_model():
    X, y = synthesize_domain_examples()
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    clf = LogisticRegression(solver='liblinear')
    clf.fit(Xs, y)
    return {"scaler": scaler, "clf": clf}

def build_sample_content_dataset():
    benign = [
        "<html><body><h1>Welcome to Example</h1><p>This is a safe site about gardening and recipes.</p></body></html>",
        "<html><body><p>Contact us at info@example.org for more information about our services.</p></body></html>",
        "This blog explains how to cook pasta. Ingredients: pasta, tomato, salt, olive oil."
    ]
    scandal = [
        "<html><body><h1>Free movies download</h1><p>Click here to download the full movie. No registration</p></body></html>",
        "You won $1,000,000! Claim now with your bank details. Urgent.",
        "<html><body><p>Adult content images and sexual material for adults only.</p></body></html>"
    ]
    X = benign + scandal
    y = [0]*len(benign) + [1]*len(scandal)
    return X, y

def train_content_model():
    X, y = build_sample_content_dataset()
    pipeline = make_pipeline(
        TfidfVectorizer(ngram_range=(1,2), max_features=2000),
        LogisticRegression(solver='liblinear')
    )
    pipeline.fit(X, y)
    return pipeline

# Initialize models
MODEL_DIR = Path("ml_models")
MODEL_DIR.mkdir(exist_ok=True)
DOMAIN_MODEL_FPATH = MODEL_DIR / "domain_model.pkl"
CONTENT_MODEL_FPATH = MODEL_DIR / "content_model.pkl"

def ensure_models():
    if DOMAIN_MODEL_FPATH.exists():
        domain_model = joblib.load(DOMAIN_MODEL_FPATH)
    else:
        print("[*] Training domain typo model...")
        domain_model = train_domain_model()
        joblib.dump(domain_model, DOMAIN_MODEL_FPATH)
    
    if CONTENT_MODEL_FPATH.exists():
        content_model = joblib.load(CONTENT_MODEL_FPATH)
    else:
        print("[*] Training content-safety model...")
        content_model = train_content_model()
        joblib.dump(content_model, CONTENT_MODEL_FPATH)
    
    return domain_model, content_model

domain_model, content_model = ensure_models()

def predict_domain_typo(domain, model):
    d = domain.lower()
    labels = d.split('.')
    if len(labels) >= 2:
        base = '.'.join(labels[-2:])
    else:
        base = d

    if base in POPULAR_DOMAINS:
        return {"is_typosquat": False, "score": 0.0}

    feat = make_domain_features(domain).reshape(1, -1)
    Xs = model["scaler"].transform(feat)
    prob = model["clf"].predict_proba(Xs)[0, 1]
    pred = model["clf"].predict(Xs)[0]
    return {"is_typosquat": bool(pred), "score": float(prob)}

def predict_content_suspicious(content, model):
    prob = model.predict_proba([content])[0,1]
    pred = model.predict([content])[0]
    return {"is_suspicious": bool(pred), "score": float(prob)}

def fetch_url_content(url, timeout=8, max_bytes=50000):
    headers = {"User-Agent": "QR-Security-Tool/1.0"}
    try:
        with requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True) as r:
            if r.status_code != 200:
                return {"ok": False, "status_code": r.status_code, "content": ""}
            
            ctype = r.headers.get('content-type','').lower()
            if not any(ct in ctype for ct in ('text','html','xml', 'application/json')):
                return {"ok": False, "status_code": r.status_code, "content": ""}
            
            chunks = []
            total = 0
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= max_bytes:
                        break
            raw = b''.join(chunks)
            text = raw.decode('utf-8', errors='replace')
            return {"ok": True, "status_code": r.status_code, "content": text}
    except Exception as e:
        return {"ok": False, "status_code": None, "content": str(e)}

def extract_domain_from_url(url):
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if ':' in host:
            host = host.split(':')[0]
        return host
    except:
        return ""

# ========== ROUTES ==========

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scanner')
def scanner():
    return render_template('scanner.html')

@app.route('/generator')
def generator():
    return render_template('generator.html')

@app.route('/api/check-url', methods=['POST'])
def check_url():
    data = request.json
    url = data.get('url', '')
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    domain = extract_domain_from_url(url)
    dom_result = predict_domain_typo(domain, domain_model)
    domain_prob = float(dom_result.get("score", 0.0))
    domain_flag = bool(dom_result.get("is_typosquat", False))
    
    response = {
        "url": url,
        "domain": domain,
        "domain_result": dom_result,
        "domain_prob": domain_prob,
        "domain_flag": domain_flag,
        "content_result": None,
        "suspicious": False
    }
    
    if domain_flag and (domain_prob >= DOMAIN_PROB_THRESHOLD):
        response["suspicious"] = True
        response["warning"] = "⚠️ Suspicious domain detected"
        return jsonify(response)
    
    fetch = fetch_url_content(url)
    if not fetch.get("ok"):
        return jsonify(response)
    
    content_text = fetch.get("content", "")
    content_res = predict_content_suspicious(content_text, content_model)
    content_prob = float(content_res.get("score", 0.0))
    content_flag = bool(content_res.get("is_suspicious", False))
    
    suspicious_keywords = ['bank', 'password', 'claim', 'won', 'free', 'download', 'adult', 'credit card']
    hits = sum(1 for kw in suspicious_keywords if kw in content_text.lower())
    
    response["content_result"] = content_res
    response["content_prob"] = content_prob
    response["content_flag"] = content_flag
    response["heuristic_hits"] = hits
    
    domain_strong = domain_flag and (domain_prob >= DOMAIN_PROB_THRESHOLD)
    content_strong = content_prob >= CONTENT_PROB_THRESHOLD
    heuristic_strong = hits >= HEURISTIC_HITS_THRESHOLD
    
    if REQUIRE_BOTH_STRONG:
        suspicious = (domain_strong and content_strong) or heuristic_strong
    else:
        suspicious = content_strong or domain_strong or heuristic_strong
    
    response["suspicious"] = suspicious
    response["warning"] = "⚠️ This URL appears suspicious" if suspicious else "✅ URL appears safe"
    
    return jsonify(response)

@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return jsonify({
        "success": True,
        "qr_code": f"data:image/png;base64,{img_str}",
        "text": text
    })

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)