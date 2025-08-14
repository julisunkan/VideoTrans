import os
import logging
import tempfile
import subprocess
import time
from datetime import datetime
try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    nr = None
    NOISEREDUCE_AVAILABLE = False
    logging.warning("noisereduce not available, audio cleaning will be skipped")
import soundfile as sf
import ffmpeg
from faster_whisper import WhisperModel
from googletrans import Translator
import threading

class TranscriptionService:
    def __init__(self):
        """Initialize the transcription service."""
        self.model = None
        self.translator = Translator()
        self.model_lock = threading.Lock()
        
        # Whisper supported languages
        self.supported_languages = {
            'auto': 'Auto-detect',
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'tr': 'Turkish',
            'pl': 'Polish',
            'nl': 'Dutch',
            'sv': 'Swedish',
            'da': 'Danish',
            'no': 'Norwegian',
            'fi': 'Finnish',
            'cs': 'Czech',
            'sk': 'Slovak',
            'hu': 'Hungarian',
            'ro': 'Romanian',
            'bg': 'Bulgarian',
            'hr': 'Croatian',
            'sl': 'Slovenian',
            'et': 'Estonian',
            'lv': 'Latvian',
            'lt': 'Lithuanian',
            'uk': 'Ukrainian',
            'be': 'Belarusian',
            'ca': 'Catalan',
            'eu': 'Basque',
            'gl': 'Galician',
            'is': 'Icelandic',
            'mt': 'Maltese',
            'cy': 'Welsh',
            'ga': 'Irish',
            'mk': 'Macedonian',
            'sq': 'Albanian',
            'az': 'Azerbaijani',
            'ka': 'Georgian',
            'hy': 'Armenian',
            'he': 'Hebrew',
            'ur': 'Urdu',
            'fa': 'Persian',
            'ps': 'Pashto',
            'sd': 'Sindhi',
            'bn': 'Bengali',
            'ne': 'Nepali',
            'si': 'Sinhala',
            'my': 'Myanmar',
            'km': 'Khmer',
            'lo': 'Lao',
            'vi': 'Vietnamese',
            'th': 'Thai',
            'ms': 'Malay',
            'id': 'Indonesian',
            'tl': 'Filipino',
            'sw': 'Swahili',
            'am': 'Amharic',
            'yo': 'Yoruba',
            'zu': 'Zulu',
            'af': 'Afrikaans',
            'mg': 'Malagasy',
            'so': 'Somali',
            'ha': 'Hausa',
            'ig': 'Igbo'
        }
    
    def get_whisper_model(self):
        """Get or initialize the Whisper model."""
        with self.model_lock:
            if self.model is None:
                try:
                    # Use tiny model for maximum speed - much faster processing
                    # Options: tiny, base, small, medium, large
                    # tiny = fastest, less accurate | large = slowest, most accurate
                    self.model = WhisperModel(
                        "tiny", 
                        device="cpu", 
                        compute_type="int8",
                        num_workers=2  # Use multiple threads for faster processing
                    )
                    logging.info("Fast Whisper model (tiny) loaded successfully")
                except Exception as e:
                    logging.error(f"Failed to load Whisper model: {str(e)}")
                    raise
            return self.model
    
    def extract_audio(self, video_path, session_id):
        """Extract audio from video file using FFmpeg."""
        try:
            output_path = os.path.join('outputs', f'audio_{session_id}.wav')
            
            # Use ffmpeg-python to extract audio with optimized settings
            stream = ffmpeg.input(video_path)
            audio = stream.audio
            # Extract at 16kHz mono for faster processing (Whisper's native format)
            out = ffmpeg.output(
                audio, output_path, 
                acodec='pcm_s16le', 
                ac=1,          # Mono audio
                ar='16000',    # 16kHz sample rate (Whisper optimized)
                t=None         # No duration limit
            )
            ffmpeg.run(out, overwrite_output=True, quiet=True)
            
            logging.info(f"Audio extracted successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logging.error(f"Audio extraction failed: {str(e)}")
            raise Exception(f"Failed to extract audio: {str(e)}")
    
    def clean_audio(self, audio_path, session_id):
        """Clean audio using noise reduction - disabled for speed optimization."""
        try:
            # Skip noise reduction for faster processing
            # This step can add significant time to processing
            logging.info("Skipping noise reduction for faster processing")
            return audio_path
            
            # The below code is commented out but available if quality is more important than speed
            # if not NOISEREDUCE_AVAILABLE:
            #     logging.info("Noise reduction not available, using original audio")
            #     return audio_path
            #     
            # # Read audio file
            # data, rate = sf.read(audio_path)
            # 
            # # Apply noise reduction
            # if nr is not None:
            #     reduced_noise = nr.reduce_noise(y=data, sr=rate)
            # else:
            #     reduced_noise = data
            # 
            # # Save cleaned audio
            # cleaned_path = os.path.join('outputs', f'cleaned_audio_{session_id}.wav')
            # sf.write(cleaned_path, reduced_noise, rate)
            # 
            # logging.info(f"Audio cleaned successfully: {cleaned_path}")
            # return cleaned_path
            
        except Exception as e:
            logging.error(f"Audio cleaning failed: {str(e)}")
            # If cleaning fails, return original audio
            logging.warning("Using original audio without cleaning")
            return audio_path
    
    def transcribe_audio(self, audio_path, language=None):
        """Transcribe audio using faster-whisper."""
        try:
            model = self.get_whisper_model()
            
            # Transcribe with optimized settings for speed
            segments, info = model.transcribe(
                audio_path,
                language=language,
                beam_size=1,  # Reduced from 5 for speed
                best_of=1,    # Reduced from 5 for speed 
                temperature=0.0,
                word_timestamps=False,  # Disabled for faster processing
                vad_filter=True,       # Voice activity detection for efficiency
                vad_parameters=dict(min_silence_duration_ms=1000)  # Skip long silences
            )
            
            # Convert segments to list for easier handling
            transcript_segments = []
            for segment in segments:
                transcript_segments.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text.strip()
                })
            
            result = {
                'language': info.language,
                'language_probability': info.language_probability,
                'duration': info.duration,
                'segments': transcript_segments
            }
            
            logging.info(f"Transcription completed. Detected language: {info.language}")
            return result
            
        except Exception as e:
            logging.error(f"Transcription failed: {str(e)}")
            raise Exception(f"Transcription failed: {str(e)}")
    
    def translate_transcript(self, segments, target_language):
        """Translate transcript segments to target language with batch optimization."""
        try:
            translated_segments = []
            
            # Process in batches for better performance
            batch_size = 10  # Process 10 segments at a time
            
            for i in range(0, len(segments), batch_size):
                batch = segments[i:i + batch_size]
                
                for segment in batch:
                    try:
                        # Translate the text with timeout for faster processing
                        translated = self.translator.translate(
                            segment['text'], 
                            dest=target_language
                        )
                        
                        translated_segments.append({
                            'start': segment['start'],
                            'end': segment['end'],
                            'text': translated.text
                        })
                        
                    except Exception as e:
                        logging.warning(f"Translation failed for segment: {str(e)}")
                        # Keep original text if translation fails
                        translated_segments.append(segment)
                
                # Small delay between batches to avoid rate limiting
                time.sleep(0.1)
            
            logging.info(f"Translation to {target_language} completed")
            return translated_segments
            
        except Exception as e:
            logging.error(f"Translation failed: {str(e)}")
            # Return original segments if translation fails
            return segments
    
    def get_supported_languages(self):
        """Get list of supported languages."""
        return self.supported_languages
    
    def transcribe_file(self, file_path, language=None):
        """Main method to transcribe a file (audio or video)."""
        try:
            session_id = os.path.basename(file_path).split('_')[0]
            
            # Determine if it's audio or video based on extension
            ext = os.path.splitext(file_path)[1].lower()
            video_extensions = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv'}
            
            if ext in video_extensions:
                # Extract audio from video
                audio_path = self.extract_audio(file_path, session_id)
            else:
                # Already audio, just clean it
                audio_path = self.clean_audio(file_path, session_id)
            
            # Transcribe the audio
            segments = self.transcribe_audio(audio_path, language)
            
            # Clean up temporary audio file if it was extracted
            if ext in video_extensions and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except:
                    pass
            
            return segments
            
        except Exception as e:
            logging.error(f"File transcription failed: {str(e)}")
            raise
    
    def translate_segments(self, segments, target_language):
        """Alias for translate_transcript for backward compatibility."""
        return self.translate_transcript(segments, target_language)
