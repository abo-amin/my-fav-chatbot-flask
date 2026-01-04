"""
Knowledge Base Chatbot - Main Flask Application
"""
from flask import Flask, redirect, url_for
from flask_cors import CORS
import config
from models import database


def create_app():
    """Application factory"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
    app.config['UPLOAD_FOLDER'] = str(config.UPLOAD_FOLDER)
    
    # Enable CORS for API
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize database
    database.init_db()
    config.init_directories()
    
    # Initialize knowledge base and ensure documents are indexed
    from services.knowledge_base import knowledge_base
    knowledge_base.ensure_indexed()
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    
    # Root redirect
    @app.route('/')
    def index():
        return redirect(url_for('admin.dashboard'))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def server_error(e):
        return {'error': 'Internal server error'}, 500
    
    return app


# Create app instance
app = create_app()


if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║          🤖 Knowledge Base Chatbot Started!               ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Dashboard: http://localhost:5000/admin                   ║
    ║  API Docs:  http://localhost:5000/api/v1/health           ║
    ║                                                           ║
    ║  Default Login:                                           ║
    ║    Username: admin                                        ║
    ║    Password: admin123                                     ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)
