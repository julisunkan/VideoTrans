import logging
from datetime import timedelta

class SubtitleFormatter:
    def __init__(self):
        """Initialize subtitle formatter."""
        pass
    
    def format_timestamp_srt(self, seconds):
        """Format timestamp for SRT format (HH:MM:SS,mmm)."""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        seconds = td.total_seconds() % 60
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def format_timestamp_vtt(self, seconds):
        """Format timestamp for VTT format (HH:MM:SS.mmm)."""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        seconds = td.total_seconds() % 60
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    
    def format_timestamp_ass(self, seconds):
        """Format timestamp for ASS format (H:MM:SS.cc)."""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        seconds = td.total_seconds() % 60
        centiseconds = int((seconds % 1) * 100)
        seconds = int(seconds)
        
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
    
    def to_srt(self, segments):
        """Convert segments to SRT format."""
        try:
            srt_content = []
            
            for i, segment in enumerate(segments, 1):
                start_time = self.format_timestamp_srt(segment['start'])
                end_time = self.format_timestamp_srt(segment['end'])
                text = segment['text'].strip()
                
                srt_content.append(f"{i}")
                srt_content.append(f"{start_time} --> {end_time}")
                srt_content.append(text)
                srt_content.append("")  # Empty line between subtitles
            
            return '\n'.join(srt_content)
            
        except Exception as e:
            logging.error(f"SRT conversion failed: {str(e)}")
            raise
    
    def to_vtt(self, segments):
        """Convert segments to VTT format."""
        try:
            vtt_content = ["WEBVTT", ""]  # VTT header
            
            for segment in segments:
                start_time = self.format_timestamp_vtt(segment['start'])
                end_time = self.format_timestamp_vtt(segment['end'])
                text = segment['text'].strip()
                
                vtt_content.append(f"{start_time} --> {end_time}")
                vtt_content.append(text)
                vtt_content.append("")  # Empty line between subtitles
            
            return '\n'.join(vtt_content)
            
        except Exception as e:
            logging.error(f"VTT conversion failed: {str(e)}")
            raise
    
    def to_ass(self, segments):
        """Convert segments to ASS format."""
        try:
            # ASS header
            ass_header = """[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,16,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            
            ass_content = [ass_header.strip()]
            
            for segment in segments:
                start_time = self.format_timestamp_ass(segment['start'])
                end_time = self.format_timestamp_ass(segment['end'])
                text = segment['text'].strip()
                
                # Escape special characters in ASS
                text = text.replace('\n', '\\N')
                
                dialogue_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}"
                ass_content.append(dialogue_line)
            
            return '\n'.join(ass_content)
            
        except Exception as e:
            logging.error(f"ASS conversion failed: {str(e)}")
            raise
