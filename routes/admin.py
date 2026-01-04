"""
Admin Routes - Dashboard and management pages
"""
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from routes.auth import admin_required
from models import database
from services.document_processor import document_processor
from services.knowledge_base import knowledge_base
from services.ollama_service import ollama_service
from services.chat_service import chat_service
import config

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@admin_required
def dashboard():
    """Main admin dashboard"""
    stats = database.get_dashboard_stats()
    model_settings = database.get_model_settings()
    ollama_status = ollama_service.check_connection()
    
    return render_template('dashboard.html', 
                          stats=stats, 
                          model_settings=model_settings,
                          ollama_status=ollama_status)


@admin_bp.route('/documents')
@admin_required
def documents():
    """Document management page"""
    docs = database.get_all_documents()
    return render_template('documents.html', documents=docs)


@admin_bp.route('/documents/upload', methods=['POST'])
@admin_required
def upload_document():
    """Upload and process a document"""
    if 'file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('admin.documents'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('admin.documents'))
    
    # Check file extension
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in config.ALLOWED_EXTENSIONS:
        flash(f'File type not allowed. Allowed: {", ".join(config.ALLOWED_EXTENSIONS)}', 'danger')
        return redirect(url_for('admin.documents'))
    
    try:
        # Save file
        config.init_directories()
        filename = secure_filename(file.filename)
        # Add timestamp to prevent duplicates
        import time
        unique_filename = f"{int(time.time())}_{filename}"
        file_path = config.UPLOAD_FOLDER / unique_filename
        file.save(str(file_path))
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Add to database
        doc_id = database.add_document(
            filename=unique_filename,
            original_filename=filename,
            file_type=ext,
            file_size=file_size
        )
        
        # Process document
        result = document_processor.process_file(str(file_path))
        
        # Add chunks to database
        database.add_document_chunks(doc_id, result['chunks'])
        
        # Add to knowledge base (vector index)
        knowledge_base.add_documents(doc_id, result['chunks'])
        
        # Update document as indexed
        database.update_document_indexed(doc_id, result['chunk_count'])
        
        flash(f'Document uploaded successfully! {result["chunk_count"]} chunks indexed.', 'success')
        
    except Exception as e:
        flash(f'Error processing document: {str(e)}', 'danger')
    
    return redirect(url_for('admin.documents'))


@admin_bp.route('/documents/<doc_id>/delete', methods=['POST'])
@admin_required
def delete_document(doc_id):
    """Delete a document"""
    try:
        doc = database.get_document_by_id(doc_id)
        if doc:
            # Delete from file system
            file_path = config.UPLOAD_FOLDER / doc['filename']
            if file_path.exists():
                os.remove(file_path)
            
            # Delete from knowledge base
            knowledge_base.delete_document(doc_id)
            
            # Delete from database
            database.delete_document(doc_id)
            
            flash('Document deleted successfully.', 'success')
        else:
            flash('Document not found.', 'danger')
    except Exception as e:
        flash(f'Error deleting document: {str(e)}', 'danger')
    
    return redirect(url_for('admin.documents'))


@admin_bp.route('/api-keys')
@admin_required
def api_keys():
    """API key management page"""
    keys = database.get_all_api_keys()
    return render_template('api_keys.html', api_keys=keys)


@admin_bp.route('/api-keys/create', methods=['POST'])
@admin_required
def create_api_key():
    """Create a new API key"""
    name = request.form.get('name', '').strip()
    rate_limit = int(request.form.get('rate_limit', 60))
    
    if not name:
        flash('Please provide a name for the API key.', 'danger')
        return redirect(url_for('admin.api_keys'))
    
    try:
        result = database.create_api_key(name, rate_limit)
        # Store the key temporarily to show to user
        flash(f'API Key created! Key: {result["key"]} (Save this, it won\'t be shown again!)', 'success')
    except Exception as e:
        flash(f'Error creating API key: {str(e)}', 'danger')
    
    return redirect(url_for('admin.api_keys'))


@admin_bp.route('/api-keys/<key_id>/toggle', methods=['POST'])
@admin_required
def toggle_api_key(key_id):
    """Enable or disable an API key"""
    is_active = request.form.get('is_active') == 'true'
    database.toggle_api_key(key_id, is_active)
    flash('API key updated.', 'success')
    return redirect(url_for('admin.api_keys'))


@admin_bp.route('/api-keys/<key_id>/delete', methods=['POST'])
@admin_required
def delete_api_key(key_id):
    """Delete an API key"""
    database.delete_api_key(key_id)
    flash('API key deleted.', 'success')
    return redirect(url_for('admin.api_keys'))


@admin_bp.route('/models')
@admin_required
def models():
    """Model settings page"""
    ollama_status = ollama_service.check_connection()
    available_models = ollama_service.get_available_models() if ollama_status['connected'] else []
    model_settings = database.get_model_settings()
    
    return render_template('models.html',
                          ollama_status=ollama_status,
                          available_models=available_models,
                          model_settings=model_settings)


@admin_bp.route('/models/settings', methods=['POST'])
@admin_required
def update_model_settings():
    """Update model settings"""
    try:
        active_model = request.form.get('active_model')
        temperature = float(request.form.get('temperature', 0.7))
        context_length = int(request.form.get('context_length', 4096))
        top_p = float(request.form.get('top_p', 0.9))
        top_k = int(request.form.get('top_k', 40))
        fallback_model = request.form.get('fallback_model') or None
        system_prompt = request.form.get('system_prompt') or None
        
        database.update_model_settings(
            active_model=active_model,
            temperature=temperature,
            context_length=context_length,
            top_p=top_p,
            top_k=top_k,
            fallback_model=fallback_model,
            system_prompt=system_prompt
        )
        
        flash('Model settings updated successfully.', 'success')
    except Exception as e:
        flash(f'Error updating settings: {str(e)}', 'danger')
    
    return redirect(url_for('admin.models'))


@admin_bp.route('/chat')
@admin_required
def chat():
    """Chat testing page"""
    history = chat_service.get_chat_history(20)
    return render_template('chat.html', history=history)


@admin_bp.route('/chat/send', methods=['POST'])
@admin_required
def send_chat():
    """Send a chat message (admin testing)"""
    question = request.form.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'Please enter a question'}), 400
    
    try:
        result = chat_service.process_question(question)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
