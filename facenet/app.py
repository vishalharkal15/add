import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from mtcnn import MTCNN
from keras_facenet import FaceNet

# Initialize Flask with static folder for production
app = Flask(__name__, static_folder='static', static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# CORS configuration based on environment
if os.environ.get('FLASK_ENV') == 'production':
    # In production, restrict CORS to your domain
    CORS(app, resources={r"/api/*": {"origins": "*"}})  # Update with your domain
else:
    CORS(app)  # Allow all origins in development

# Initialize DB
from database import init_db
db, Attendance, Student = init_db(app)

# Initialize FaceNet & MTCNN
detector = MTCNN()
embedder = FaceNet()

# Health check endpoint for monitoring (MUST be before catch-all route)
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'service': 'attendance-system'}, 200

# Register API routes
from routes import register_routes
register_routes(app, db, Attendance, detector, embedder)

# Serve React App (for production) - MUST be last
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve React app with fallback routing for SPA"""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        # Fallback to index.html for client-side routing
        if os.path.exists(os.path.join(app.static_folder, 'index.html')):
            return send_from_directory(app.static_folder, 'index.html')
        else:
            return {"message": "Frontend not built. Run 'npm run build' first."}, 404

# Security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    if debug and os.path.exists("./{Yout IP}.pem"):
        # Development server with SSL
        app.run(
            host="0.0.0.0", 
            port=port, 
            debug=True,
            ssl_context=("./{Yout IP}.pem", "./{Yout IP}-key.pem")
        )
    else:
        # Production or development without SSL
        app.run(host="0.0.0.0", port=port, debug=debug)
