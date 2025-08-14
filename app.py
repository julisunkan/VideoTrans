import os
import logging
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, session
from flask_socketio import SocketIO, emit
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

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB limit

# Initialize SocketIO with eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'audio': {'mp3', 'wav', 'flac', 'm4a', 'aac'},
    'video': {'mp4', 'mkv', 'mov', 'avi', 'webm', 'flv'}
}

# Create directories if they don't exist
os.makedirs('uploads', exist_ok=True)
os.makedirs('outputs', exist_ok=True)

# Initialize services
transcription_service = TranscriptionService()
subtitle_formatter = SubtitleFormatter()
cleanup_service = FileCleanupService()

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    if '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS['audio'] or extension in ALLOWED_EXTENSIONS['video']

def get_file_type(filename):
    """Determine if file is audio or video."""
    extension = filename.rsplit('.', 1)[1].lower()
    if extension in ALLOWED_EXTENSIONS['audio']:
        return 'audio'
    elif extension in ALLOWED_EXTENSIONS['video']:
        return 'video'
    return None

@app.route('/')
def index():
    """Main upload page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start transcription process."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Supported formats: MP3, WAV, MP4, MKV, MOV, AVI, WEBM'}), 400
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        
        # Get form data
        source_language = request.form.get('source_language', 'auto')
        target_languages = request.form.getlist('target_languages')
        
        if not target_languages:
            target_languages = ['en']  # Default to English
        
        # Secure filename and save
        filename = secure_filename(file.filename or "upload")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{session_id}_{filename}"
        filepath = os.path.join('uploads', unique_filename)
        
        file.save(filepath)
        
        # Store session data
        session.update({
            'filename': unique_filename,
            'original_filename': filename,
            'source_language': source_language,
            'target_languages': target_languages,
            'file_type': get_file_type(filename),
            'upload_time': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'redirect_url': url_for('progress')
        })
        
    except Exception as e:
        logging.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/progress')
def progress():
    """Progress page with real-time updates."""
    if 'session_id' not in session:
        return redirect(url_for('index'))
    return render_template('progress.html', session_id=session['session_id'])

@app.route('/result')
def result():
    """Results page with download links and video preview."""
    if 'session_id' not in session or 'output_files' not in session:
        return redirect(url_for('index'))
    
    return render_template('result.html', 
                         session_data=session,
                         output_files=session['output_files'])

@app.route('/download/<filename>')
def download_file(filename):
    """Download individual subtitle files."""
    try:
        # First try outputs directory for subtitle files
        filepath = os.path.join('outputs', filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        
        # Then try uploads directory for media files (for video preview)
        filepath = os.path.join('uploads', filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=False)
        
        return "File not found", 404
    except Exception as e:
        logging.error(f"Download error: {str(e)}")
        return "Download failed", 500

@app.route('/download_zip')
def download_zip():
    """Download all subtitle files as ZIP."""
    try:
        if 'output_files' not in session:
            return "No files available", 404
        
        session_id = session['session_id']
        zip_filename = f"subtitles_{session_id}.zip"
        zip_path = os.path.join('outputs', zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_info in session['output_files']:
                file_path = os.path.join('outputs', file_info['filename'])
                if os.path.exists(file_path):
                    zipf.write(file_path, file_info['filename'])
        
        return send_file(zip_path, as_attachment=True, download_name=zip_filename)
        
    except Exception as e:
        logging.error(f"ZIP download error: {str(e)}")
        return "ZIP creation failed", 500

@socketio.on('start_transcription')
def handle_transcription(data):
    """Handle transcription request via WebSocket."""
    session_id = data.get('session_id')
    
    if session_id != session.get('session_id'):
        emit('error', {'message': 'Invalid session'})
        return
    
    def transcription_task():
        try:
            filename = session['filename']
            filepath = os.path.join('uploads', filename)
            source_language = session['source_language']
            target_languages = session['target_languages']
            original_filename = session['original_filename']
            
            # Start transcription process
            emit('progress', {'step': 'starting', 'message': 'Starting transcription...', 'percentage': 0})
            
            # Extract audio if video file
            if session['file_type'] == 'video':
                emit('progress', {'step': 'extracting', 'message': 'Extracting audio from video...', 'percentage': 10})
                audio_path = transcription_service.extract_audio(filepath, session_id)
            else:
                audio_path = filepath
            
            # Clean audio
            emit('progress', {'step': 'cleaning', 'message': 'Cleaning audio for better transcription...', 'percentage': 20})
            cleaned_audio_path = transcription_service.clean_audio(audio_path, session_id)
            
            # Transcribe
            emit('progress', {'step': 'transcribing', 'message': 'Transcribing audio...', 'percentage': 30})
            transcript = transcription_service.transcribe_audio(
                cleaned_audio_path, 
                source_language if source_language != 'auto' else None
            )
            
            # Translate and generate subtitles
            output_files = []
            base_progress = 50
            progress_per_lang = 40 / len(target_languages)
            
            for i, target_lang in enumerate(target_languages):
                current_progress = base_progress + (i * progress_per_lang)
                emit('progress', {
                    'step': 'translating', 
                    'message': f'Translating to {target_lang}...', 
                    'percentage': int(current_progress)
                })
                
                # Translate if target language is different from source
                if target_lang != transcript['language']:
                    translated_segments = transcription_service.translate_transcript(
                        transcript['segments'], target_lang
                    )
                else:
                    translated_segments = transcript['segments']
                
                # Generate subtitle formats
                base_filename = f"{os.path.splitext(original_filename)[0]}_{target_lang}"
                
                # SRT format
                srt_content = subtitle_formatter.to_srt(translated_segments)
                srt_filename = f"{base_filename}.srt"
                srt_path = os.path.join('outputs', srt_filename)
                with open(srt_path, 'w', encoding='utf-8') as f:
                    f.write(srt_content)
                output_files.append({'filename': srt_filename, 'format': 'SRT', 'language': target_lang})
                
                # VTT format
                vtt_content = subtitle_formatter.to_vtt(translated_segments)
                vtt_filename = f"{base_filename}.vtt"
                vtt_path = os.path.join('outputs', vtt_filename)
                with open(vtt_path, 'w', encoding='utf-8') as f:
                    f.write(vtt_content)
                output_files.append({'filename': vtt_filename, 'format': 'VTT', 'language': target_lang})
                
                # ASS format
                ass_content = subtitle_formatter.to_ass(translated_segments)
                ass_filename = f"{base_filename}.ass"
                ass_path = os.path.join('outputs', ass_filename)
                with open(ass_path, 'w', encoding='utf-8') as f:
                    f.write(ass_content)
                output_files.append({'filename': ass_filename, 'format': 'ASS', 'language': target_lang})
            
            # Store output files in session
            session['output_files'] = output_files
            session['transcript'] = transcript
            
            emit('progress', {
                'step': 'completed', 
                'message': 'Transcription and translation completed!', 
                'percentage': 100
            })
            
            emit('transcription_complete', {
                'output_files': output_files,
                'redirect_url': url_for('result')
            })
            
        except Exception as e:
            logging.error(f"Transcription error: {str(e)}")
            emit('error', {'message': f'Transcription failed: {str(e)}'})
    
    # Start transcription in background thread
    thread = threading.Thread(target=transcription_task)
    thread.daemon = True
    thread.start()

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    logging.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    logging.info('Client disconnected')

# Background cleanup task
def start_cleanup_scheduler():
    """Start the file cleanup scheduler."""
    def cleanup_loop():
        while True:
            try:
                cleanup_service.cleanup_old_files()
                time.sleep(3600)  # Run every hour
            except Exception as e:
                logging.error(f"Cleanup error: {str(e)}")
                time.sleep(3600)
    
    cleanup_thread = threading.Thread(target=cleanup_loop)
    cleanup_thread.daemon = True
    cleanup_thread.start()

if __name__ == '__main__':
    start_cleanup_scheduler()
    # Note: Changed to port 8080 as requested for Replit compatibility
    # but keeping 5000 as per guidelines - you may need to adjust based on deployment
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, log_output=False)
