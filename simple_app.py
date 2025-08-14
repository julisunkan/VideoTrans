import os
import logging
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, session
from werkzeug.utils import secure_filename
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

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB limit
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

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

def allowed_file(filename, file_type):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS[file_type]

def get_file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in ALLOWED_EXTENSIONS['audio']:
        return 'audio'
    elif ext in ALLOWED_EXTENSIONS['video']:
        return 'video'
    return None

@app.route('/')
def index():
    return render_template('index.html', languages=LANGUAGE_NAMES)

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        file_type = get_file_type(file.filename)
        if not file_type or not allowed_file(file.filename, file_type):
            return jsonify({'error': 'File type not supported'}), 400
        
        # Generate unique session ID and filename
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        filename = secure_filename(file.filename or '')
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
    if 'uploaded_file' not in session:
        return redirect(url_for('index'))
    return render_template('progress.html', 
                         filename=session['uploaded_file']['filename'],
                         languages=LANGUAGE_NAMES)

@app.route('/process', methods=['POST'])
def process_file():
    try:
        if 'uploaded_file' not in session:
            return jsonify({'error': 'No file uploaded'}), 400
        
        data = request.get_json()
        source_language = data.get('source_language', 'auto')
        target_languages = data.get('target_languages', [])
        subtitle_formats = data.get('formats', ['srt'])
        
        file_info = session['uploaded_file']
        
        # Start processing in background thread
        def process_background():
            try:
                # Step 1: Transcribe audio
                logging.info("Starting transcription...")
                segments = transcription_service.transcribe_file(
                    file_info['path'], 
                    source_language if source_language != 'auto' else None
                )
                
                # Step 2: Generate subtitle files
                logging.info("Generating subtitle files...")
                output_files = []
                
                for fmt in subtitle_formats:
                    # Original language subtitle
                    original_content = subtitle_formatter.to_format(segments, fmt)
                    original_filename = f"{session['session_id']}_original.{fmt}"
                    original_path = os.path.join(app.config['OUTPUT_FOLDER'], original_filename)
                    
                    with open(original_path, 'w', encoding='utf-8') as f:
                        f.write(original_content)
                    
                    output_files.append({
                        'filename': f"original.{fmt}",
                        'path': original_path,
                        'language': 'original',
                        'format': fmt
                    })
                    
                    # Translated subtitles
                    for lang_code in target_languages:
                        try:
                            translated_segments = transcription_service.translate_segments(segments, lang_code)
                            translated_content = subtitle_formatter.to_format(translated_segments, fmt)
                            
                            lang_filename = f"{session['session_id']}_{lang_code}.{fmt}"
                            lang_path = os.path.join(app.config['OUTPUT_FOLDER'], lang_filename)
                            
                            with open(lang_path, 'w', encoding='utf-8') as f:
                                f.write(translated_content)
                            
                            output_files.append({
                                'filename': f"{LANGUAGE_NAMES.get(lang_code, lang_code)}.{fmt}",
                                'path': lang_path,
                                'language': lang_code,
                                'format': fmt
                            })
                        except Exception as e:
                            logging.error(f"Translation error for {lang_code}: {e}")
                
                # Store results in session
                session['results'] = {
                    'files': output_files,
                    'original_filename': file_info['filename'],
                    'processing_complete': True
                }
                
                logging.info("Processing completed successfully")
                
            except Exception as e:
                logging.error(f"Processing error: {e}")
                session['results'] = {
                    'error': str(e),
                    'processing_complete': True
                }
        
        # Start background processing
        thread = threading.Thread(target=process_background)
        thread.start()
        
        return jsonify({'success': True, 'message': 'Processing started'})
        
    except Exception as e:
        logging.error(f"Process error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/status')
def get_status():
    if 'results' in session:
        if session['results'].get('processing_complete'):
            return jsonify({
                'complete': True,
                'success': 'error' not in session['results'],
                'error': session['results'].get('error'),
                'redirect': url_for('result') if 'error' not in session['results'] else None
            })
    
    return jsonify({'complete': False})

@app.route('/result')
def result():
    if 'results' not in session or 'error' in session['results']:
        return redirect(url_for('index'))
    
    results = session['results']
    return render_template('result.html', 
                         files=results['files'],
                         original_filename=results['original_filename'])

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # Security: Only allow downloads of files from current session
        if 'results' not in session:
            return "File not found", 404
        
        for file_info in session['results']['files']:
            if os.path.basename(file_info['path']) == filename:
                return send_file(file_info['path'], as_attachment=True, 
                               download_name=file_info['filename'])
        
        return "File not found", 404
        
    except Exception as e:
        logging.error(f"Download error: {e}")
        return "Download failed", 500

@app.route('/download_all')
def download_all():
    try:
        if 'results' not in session:
            return "No files to download", 404
        
        # Create ZIP file
        zip_filename = f"{session['session_id']}_subtitles.zip"
        zip_path = os.path.join(app.config['OUTPUT_FOLDER'], zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_info in session['results']['files']:
                zipf.write(file_info['path'], file_info['filename'])
        
        return send_file(zip_path, as_attachment=True, 
                        download_name=f"{session['results']['original_filename']}_subtitles.zip")
        
    except Exception as e:
        logging.error(f"Download all error: {e}")
        return "Download failed", 500

def start_cleanup_scheduler():
    """Start the cleanup service in a background thread"""
    def cleanup_worker():
        while True:
            try:
                cleanup_service.cleanup_old_files()
            except Exception as e:
                logging.error(f"Cleanup error: {e}")
            time.sleep(3600)  # Run every hour
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()

if __name__ == '__main__':
    start_cleanup_scheduler()
    app.run(host='0.0.0.0', port=5000, debug=True)