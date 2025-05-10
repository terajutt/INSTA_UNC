from flask import Flask, jsonify

# Create Flask app
app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        "status": "running",
        "name": "IG Vault Bot",
        "description": "A Telegram bot for Instagram account distribution with referral system"
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)