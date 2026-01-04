"""
Public API Routes - External API for users
"""
from flask import Blueprint, request, jsonify
from functools import wraps
from models import database
from services.chat_service import chat_service
from services.ollama_service import ollama_service

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


def require_api_key(f):
    """Decorator to require valid API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({
                'error': 'API key required',
                'message': 'Please provide your API key in the X-API-Key header or as api_key parameter'
            }), 401
        
        key_info = database.verify_api_key(api_key)
        
        if not key_info:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is invalid or has been revoked'
            }), 401
        
        # Store key info in request context
        request.api_key_info = key_info
        
        return f(*args, **kwargs)
    return decorated_function


@api_bp.route('/health')
def health():
    """Health check endpoint (no auth required)"""
    ollama_status = ollama_service.check_connection()
    return jsonify({
        'status': 'healthy',
        'ollama': ollama_status
    })


@api_bp.route('/chat', methods=['POST'])
@require_api_key
def chat():
    """
    Send a message and get a response
    
    Request Body:
    {
        "question": "Your question here"
    }
    
    Response:
    {
        "answer": "The AI response",
        "source_type": "documents" or "ai_model",
        "from_documents": true/false,
        "sources": [...] (if from documents)
    }
    """
    data = request.get_json()
    
    if not data or not data.get('question'):
        return jsonify({
            'error': 'Missing question',
            'message': 'Please provide a "question" field in the request body'
        }), 400
    
    question = data['question'].strip()
    
    if not question:
        return jsonify({
            'error': 'Empty question',
            'message': 'Question cannot be empty'
        }), 400
    
    try:
        result = chat_service.process_question(
            question=question,
            api_key_id=request.api_key_info['id']
        )
        
        return jsonify({
            'answer': result['answer'],
            'source_type': result['source_type'],
            'from_documents': result['from_documents'],
            'sources': result.get('sources', []),
            'model_used': result.get('model_used', ''),
            'note': result.get('note', '')
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Processing error',
            'message': str(e)
        }), 500


@api_bp.route('/documents', methods=['GET'])
@require_api_key
def list_documents():
    """
    List all available documents
    
    Response:
    {
        "documents": [
            {
                "id": "...",
                "filename": "...",
                "file_type": "...",
                "chunk_count": 10,
                "is_indexed": true
            }
        ]
    }
    """
    docs = database.get_all_documents()
    
    return jsonify({
        'documents': [{
            'id': doc['id'],
            'filename': doc['original_filename'],
            'file_type': doc['file_type'],
            'chunk_count': doc['chunk_count'],
            'is_indexed': bool(doc['is_indexed']),
            'created_at': doc['created_at']
        } for doc in docs]
    })


@api_bp.route('/stats', methods=['GET'])
@require_api_key
def get_stats():
    """
    Get chatbot statistics
    
    Response:
    {
        "total_documents": 5,
        "total_chunks": 100,
        "total_chats": 50
    }
    """
    stats = chat_service.get_stats()
    return jsonify(stats)


# ----- Ollama API for internal use -----

@api_bp.route('/ollama/status')
def ollama_status():
    """Check Ollama connection status"""
    status = ollama_service.check_connection()
    return jsonify(status)


@api_bp.route('/ollama/models')
def ollama_models():
    """Get available Ollama models"""
    models = ollama_service.get_available_models()
    return jsonify({'models': models})


@api_bp.route('/ollama/models/<model_name>')
def ollama_model_info(model_name):
    """Get info about a specific model"""
    info = ollama_service.get_model_info(model_name)
    if info:
        return jsonify(info)
    return jsonify({'error': 'Model not found'}), 404
