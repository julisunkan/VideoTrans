# Overview

This is a Flask-based web application that generates and translates subtitles from audio and video files. Successfully migrated from Replit Agent to standard Replit environment on August 14, 2025. The application uses local Whisper models for speech-to-text transcription and free Google Translate API for subtitle translation. It supports multiple audio/video formats and provides subtitles in SRT, VTT, and ASS formats with real-time processing feedback via WebSockets.

# Recent Changes

**Migration Complete (August 14, 2025)**
- ✓ Consolidated app.py with proper Flask-SocketIO integration
- ✓ Enhanced security with session-based file access controls  
- ✓ Implemented proper client/server separation
- ✓ Fixed all route errors and security vulnerabilities
- ✓ Added ProxyFix middleware for HTTPS URL generation
- ✓ Graceful handling of missing noisereduce dependency

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework
- **Flask** with SocketIO for real-time communication
- **Eventlet** async mode for WebSocket handling
- **Bootstrap 5** with dark theme for responsive UI
- Session-based user state management

## File Processing Pipeline
- **FFmpeg** integration for audio extraction from video files
- **Noise reduction** using noisereduce library for audio enhancement
- **faster-whisper** for local speech-to-text transcription (no API costs)
- **Multiple format support**: Audio (mp3, wav, flac, m4a, aac) and Video (mp4, mkv, mov, avi, webm, flv)
- **File size limit**: 1GB maximum upload size

## Subtitle Generation
- **Multiple output formats**: SRT, VTT, and ASS subtitle formats
- **Language detection**: Automatic or manual selection from 60+ supported languages
- **Translation service**: googletrans for free subtitle translation
- **Batch processing**: Individual downloads or ZIP archives

## Real-time Features
- **WebSocket progress updates** during transcription and translation
- **Step-by-step progress tracking** with visual indicators
- **Video preview** with subtitle overlay in browser
- **Drag-and-drop** file upload interface

## File Management
- **Temporary storage** in uploads/ and outputs/ directories
- **Automatic cleanup** service removes files after 24 hours
- **Session-based file tracking** for user isolation
- **Secure filename handling** with werkzeug utilities

## Audio Processing
- **Audio extraction** from video files using FFmpeg
- **Audio enhancement** with noise reduction for better transcription accuracy
- **Format conversion** to optimize for Whisper model input

# External Dependencies

## Core Services
- **faster-whisper**: Local Whisper model for speech-to-text transcription
- **googletrans**: Free Google Translate API for subtitle translation
- **FFmpeg**: System dependency for audio/video processing

## Python Libraries
- **Flask + SocketIO**: Web framework with real-time communication
- **noisereduce + soundfile**: Audio processing and noise reduction
- **ffmpeg-python**: Python wrapper for FFmpeg operations

## Frontend Dependencies
- **Bootstrap 5**: UI framework with dark theme support
- **Font Awesome**: Icon library
- **Socket.IO client**: Real-time communication with backend

## System Requirements
- **Python 3.8+**: Runtime environment
- **FFmpeg**: Must be installed system-wide for audio/video processing
- **1GB storage**: For temporary file handling and processing