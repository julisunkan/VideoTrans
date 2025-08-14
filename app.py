import os
import logging
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import threading
import time
from utils.transcribe import TranscriptionService
from utils.subtitle_formats import SubtitleFormatter
from utils.cleanup import FileCleanupService
import zipfile
import tempfile

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB limit
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Initialize SocketIO with eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'audio': {'mp3', 'wav', 'flac', 'm4a', 'aac'},
    'video': {'mp4', 'mkv', 'mov', 'avi', 'webm', 'flv'}
}

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Initialize services
transcription_service = TranscriptionService()
subtitle_formatter = SubtitleFormatter()
cleanup_service = FileCleanupService()

# Language mapping for display
LANGUAGE_NAMES = {
    'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German', 'it': 'Italian',
    'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese', 'ko': 'Korean', 'zh': 'Chinese',
    'ar': 'Arabic', 'hi': 'Hindi', 'tr': 'Turkish', 'pl': 'Polish', 'nl': 'Dutch',
    'sv': 'Swedish', 'da': 'Danish', 'no': 'Norwegian', 'fi': 'Finnish', 'cs': 'Czech',
    'hu': 'Hungarian', 'ro': 'Romanian', 'bg': 'Bulgarian', 'hr': 'Croatian', 'sk': 'Slovak',
    'sl': 'Slovenian', 'et': 'Estonian', 'lv': 'Latvian', 'lt': 'Lithuanian', 'uk': 'Ukrainian',
    'be': 'Belarusian', 'mk': 'Macedonian', 'sq': 'Albanian', 'sr': 'Serbian', 'bs': 'Bosnian',
    'mt': 'Maltese', 'cy': 'Welsh', 'ga': 'Irish', 'is': 'Icelandic', 'eu': 'Basque',
    'ca': 'Catalan', 'gl': 'Galician', 'af': 'Afrikaans', 'sw': 'Swahili', 'ms': 'Malay',
    'id': 'Indonesian', 'tl': 'Filipino', 'vi': 'Vietnamese', 'th': 'Thai', 'my': 'Myanmar',
    'km': 'Khmer', 'lo': 'Lao', 'ka': 'Georgian', 'am': 'Amharic', 'ne': 'Nepali',
    'si': 'Sinhala', 'bn': 'Bengali', 'ur': 'Urdu', 'fa': 'Persian', 'he': 'Hebrew',
    'yi': 'Yiddish', 'ml': 'Malayalam', 'ta': 'Tamil', 'te': 'Telugu', 'kn': 'Kannada',
    'gu': 'Gujarati', 'pa': 'Punjabi', 'or': 'Odia', 'as': 'Assamese', 'sa': 'Sanskrit'
}

def allowed_file(filename, file_type=None):
    """Check if the uploaded file has an allowed extension."""
    if '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    
    if file_type:
        return extension in ALLOWED_EXTENSIONS.get(file_type, set())
    
    return extension in ALLOWED_EXTENSIONS['audio'] or extension in ALLOWED_EXTENSIONS['video']

def get_file_type(filename):
    """Determine if file is audio or video."""
    if '.' not in filename:
        return None
    extension = filename.rsplit('.', 1)[1].lower()
    if extension in ALLOWED_EXTENSIONS['audio']:
        return 'audio'
    elif extension in ALLOWED_EXTENSIONS['video']:
        return 'video'
    return None

@app.route('/')
def index():
    """Main upload page."""
    return render_template('index.html', languages=LANGUAGE_NAMES)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start transcription process."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Determine file type
        file_type = get_file_type(file.filename)
        if not file_type or not allowed_file(file.filename, file_type):
            return jsonify({'error': 'File type not supported. Please upload audio (MP3, WAV, FLAC, M4A, AAC) or video (MP4, MKV, MOV, AVI, WEBM, FLV) files.'}), 400
        
        # Generate unique session ID and filename
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        filename = secure_filename(file.filename or 'upload')
        unique_filename = f"{session['session_id']}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save uploaded file
        file.save(file_path)
        
        # Store file info in session
        session['uploaded_file'] = {
            'filename': filename,
            'path': file_path,
            'type': file_type,
            'unique_filename': unique_filename
        }
        
        return jsonify({
            'success': True,
            'filename': filename,
            'file_type': file_type,
            'redirect': url_for('progress')
        })
        
    except Exception as e:
        logging.error(f"Upload error: {e}")
        return jsonify({'error': 'Upload failed'}), 500

@app.route('/progress')
def progress():
    """Progress page with real-time updates."""
    if 'uploaded_file' not in session:
        return redirect(url_for('index'))
    return render_template('progress.html', 
                         filename=session['uploaded_file']['filename'],
                         languages=LANGUAGE_NAMES,
                         session_id=session['session_id'])

@app.route('/process', methods=['POST'])
def process_file():
    """Process the uploaded file with transcription and translation."""
    try:
        if 'uploaded_file' not in session:
            return jsonify({'error': 'No file uploaded'}), 400
        
        data = request.get_json()
        source_language = data.get('source_language', 'auto')
        target_languages = data.get('target_languages', [])
        subtitle_formats = data.get('formats', ['srt'])
        
        file_info_session = session['uploaded_file']
        session_id = session['session_id']
        
        # Start processing in background thread
        def process_background():
            try:
                # Emit progress updates via SocketIO
                socketio.emit('progress_update', {
                    'stage': 'transcription',
                    'progress': 0,
                    'message': 'Starting transcription...'
                }, to=session_id)
                
                # Step 1: Transcribe audio
                logging.info("Starting transcription...")
                segments = transcription_service.transcribe_file(
                    file_info_session['path'], 
                    source_language if source_language != 'auto' else None
                )
                
                socketio.emit('progress_update', {
                    'stage': 'transcription',
                    'progress': 100,
                    'message': 'Transcription completed!'
                }, to=session_id)
                
                # Step 2: Generate subtitle files
                socketio.emit('progress_update', {
                    'stage': 'subtitle_generation',
                    'progress': 0,
                    'message': 'Generating subtitle files...'
                }, to=session_id)
                
                output_files = []
                total_tasks = len(subtitle_formats) * (1 + len(target_languages))
                current_task = 0
                
                for fmt in subtitle_formats:
                    # Original language subtitle
                    original_content = subtitle_formatter.to_format(segments, fmt)
                    original_filename = f"{session_id}_original.{fmt}"
                    original_path = os.path.join(app.config['OUTPUT_FOLDER'], original_filename)
                    
                    with open(original_path, 'w', encoding='utf-8') as f:
                        f.write(original_content)
                    
                    output_files.append({
                        'filename': f"original.{fmt}",
                        'path': original_path,
                        'language': 'original',
                        'format': fmt
                    })
                    
                    current_task += 1
                    progress = int((current_task / total_tasks) * 100)
                    socketio.emit('progress_update', {
                        'stage': 'subtitle_generation',
                        'progress': progress,
                        'message': f'Generated original {fmt.upper()} subtitle'
                    }, to=session_id)
                    
                    # Translated subtitles
                    for lang_code in target_languages:
                        try:
                            socketio.emit('progress_update', {
                                'stage': 'translation',
                                'progress': progress,
                                'message': f'Translating to {LANGUAGE_NAMES.get(lang_code, lang_code)}...'
                            }, to=session_id)
                            
                            translated_segments = transcription_service.translate_segments(segments, lang_code)
                            translated_content = subtitle_formatter.to_format(translated_segments, fmt)
                            translated_filename = f"{session_id}_{lang_code}.{fmt}"
                            translated_path = os.path.join(app.config['OUTPUT_FOLDER'], translated_filename)
                            
                            with open(translated_path, 'w', encoding='utf-8') as f:
                                f.write(translated_content)
                            
                            output_files.append({
                                'filename': f"{LANGUAGE_NAMES.get(lang_code, lang_code)}.{fmt}",
                                'path': translated_path,
                                'language': lang_code,
                                'format': fmt
                            })
                            
                        except Exception as e:
                            logging.error(f"Translation error for {lang_code}: {e}")
                        
                        current_task += 1
                        progress = int((current_task / total_tasks) * 100)
                        socketio.emit('progress_update', {
                            'stage': 'translation',
                            'progress': progress,
                            'message': f'Translated to {LANGUAGE_NAMES.get(lang_code, lang_code)}'
                        }, to=session_id)
                
                # Store results in session
                session['output_files'] = output_files
                session['processed'] = True
                
                # Final completion signal
                socketio.emit('processing_complete', {
                    'success': True,
                    'files': output_files,
                    'redirect_url': url_for('result')
                }, to=session_id)
                
                # Note: Cleanup will happen automatically via the cleanup service
                
            except Exception as e:
                logging.error(f"Processing error: {e}")
                socketio.emit('processing_error', {
                    'error': f'Processing failed: {str(e)}'
                }, to=session_id)
        
        # Start background processing
        thread = threading.Thread(target=process_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'Processing started'})
        
    except Exception as e:
        logging.error(f"Process error: {e}")
        return jsonify({'error': 'Processing failed'}), 500

@app.route('/result')
def result():
    """Results page with download links."""
    if 'session_id' not in session or 'output_files' not in session:
        return redirect(url_for('index'))
    
    return render_template('result.html', 
                         session_data=session,
                         output_files=session['output_files'],
                         uploaded_file=session['uploaded_file'])

@app.route('/download/<filename>')
def download_file(filename):
    """Download individual subtitle files."""
    try:
        # Security check: ensure filename belongs to current session
        if 'session_id' not in session:
            return "Unauthorized", 403
        
        session_id = session['session_id']
        
        # Try outputs directory for subtitle files
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f"{session_id}_{filename}")
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)
        
        # Try uploads directory for media files (for video preview)
        if 'uploaded_file' in session:
            upload_path = session['uploaded_file']['path']
            if os.path.exists(upload_path) and filename == session['uploaded_file']['filename']:
                return send_file(upload_path, as_attachment=False)
        
        return "File not found", 404
    except Exception as e:
        logging.error(f"Download error: {str(e)}")
        return "Download failed", 500

@app.route('/download_zip')
def download_zip():
    """Download all subtitle files as ZIP."""
    try:
        if 'output_files' not in session or 'session_id' not in session:
            return "No files available", 404
        
        session_id = session['session_id']
        zip_filename = f"subtitles_{session_id}.zip"
        zip_path = os.path.join(app.config['OUTPUT_FOLDER'], zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_info in session['output_files']:
                if os.path.exists(file_info['path']):
                    zipf.write(file_info['path'], file_info['filename'])
        
        return send_file(zip_path, as_attachment=True, download_name=zip_filename)
        
    except Exception as e:
        logging.error(f"ZIP download error: {str(e)}")
        return "ZIP creation failed", 500

# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    if 'session_id' in session:
        join_room(session['session_id'])
        logging.info(f"Client connected to session: {session['session_id']}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    if 'session_id' in session:
        leave_room(session['session_id'])
        logging.info(f"Client disconnected from session: {session['session_id']}")

@socketio.on('join_session')
def handle_join_session(data):
    """Handle joining a specific session room."""
    session_id = data.get('session_id')
    if session_id:
        join_room(session_id)
        session['session_id'] = session_id
        logging.info(f"Client joined session: {session_id}")

# Error handlers
@app.errorhandler(413)
def file_too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 1GB.'}), 413

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True, log_output=True)