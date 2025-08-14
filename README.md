# Video and Audio Subtitle Generator

A powerful Flask web application that generates and translates subtitles from audio and video files using local Whisper transcription and free translation APIs.

## Features

### Core Functionality
- **File Upload**: Support for audio (.mp3, .wav, .flac, .m4a, .aac) and video (.mp4, .mkv, .mov, .avi, .webm, .flv) files
- **Audio Extraction**: Automatically extract audio from video files using FFmpeg
- **Audio Cleaning**: Enhance audio quality using noise reduction for better transcription
- **Local Transcription**: Use faster-whisper for accurate speech-to-text conversion (no API costs)
- **Language Detection**: Automatic language detection or manual selection from 60+ supported languages
- **Translation**: Free subtitle translation using googletrans
- **Multiple Formats**: Generate subtitles in SRT, VTT, and ASS formats
- **Batch Download**: Download individual files or all formats in a ZIP archive

### User Experience
- **Real-time Progress**: WebSocket-powered progress updates during processing
- **Video Preview**: In-browser video player with subtitle overlay
- **Drag & Drop**: Intuitive file upload interface
- **Mobile Friendly**: Responsive Bootstrap 5 design
- **Auto Cleanup**: Files automatically deleted after 24 hours for privacy

## Installation

### Prerequisites
- Python 3.8+
- FFmpeg (for audio/video processing)

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# macOS (with Homebrew)
brew install ffmpeg

# Windows
# Download FFmpeg from https://ffmpeg.org/download.html
