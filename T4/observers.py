import json
import os
from datetime import datetime
from pipecat.observers.base_observer import BaseObserver, FramePushed
# We import TranscriptionFrame to ensure we capture the EXACT text
from pipecat.frames.frames import (
    TranscriptionFrame,
    TextFrame,
    Frame,
    LLMFullResponseStartFrame,
    LLMFullResponseEndFrame, 
    UserStoppedSpeakingFrame, 
    BotStartedSpeakingFrame)
from pipecat.observers.loggers.transcription_log_observer import TranscriptionLogObserver
from pipecat.observers.loggers.user_bot_latency_log_observer import UserBotLatencyLogObserver
from pipecat.observers.base_observer import BaseObserver, FramePushed
# Import the specific frames we need to detect Start/End of turns

class JsonLatencyObserver(UserBotLatencyLogObserver):
    def __init__(self, output_filepath: str):
        super().__init__()
        self.output_filepath = output_filepath
        self.captured_latencies = [] 
        
        self.log_data = {
            "session_start": datetime.now().isoformat(),
            "latency_events": [],
            "summary": None
        }
        self._save_json()

    def _save_json(self):
        try:
            with open(self.output_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.log_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving latency JSON: {e}")

    def _log_latency(self, latency: float):
        super()._log_latency(latency)
        self.captured_latencies.append(latency)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "latency_seconds": round(latency, 4),
            "message": f"LATENCY FROM USER STOPPED SPEAKING TO BOT STARTED SPEAKING: {latency:.3f}s"
        }
        
        self.log_data["latency_events"].append(entry)
        self._save_json()

    def _log_summary(self):
        super()._log_summary()
        if not self.captured_latencies:
            return

        avg_lat = sum(self.captured_latencies) / len(self.captured_latencies)
        min_lat = min(self.captured_latencies)
        max_lat = max(self.captured_latencies)

        self.log_data["summary"] = {
            "timestamp": datetime.now().isoformat(),
            "count": len(self.captured_latencies),
            "average_seconds": round(avg_lat, 4),
            "min_seconds": round(min_lat, 4),
            "max_seconds": round(max_lat, 4)
        }
        self._save_json()


class JsonTranscriptionObserver(BaseObserver):
    def __init__(self, output_filepath: str):
        super().__init__()
        self.output_filepath = output_filepath
        self.bot_text_buffer = []
        self.pending_bot_text = ""
        self.last_user_stop_time = None
        
        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
        
        self.log_data = {
            "session_start": datetime.now().isoformat(),
            "conversation": []
        }
        self._save_json()

    def _save_json(self):
        try:
            with open(self.output_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.log_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _append_log(self, role, text, timestamp=None):
        if not text or not text.strip():
            return
        
        ts = timestamp if timestamp else datetime.now().isoformat()
        
        entry = {
            "timestamp": ts,
            "role": role, 
            "text": text.strip()
        }
        self.log_data["conversation"].append(entry)
        self._save_json()

    async def on_push_frame(self, *args, **kwargs):
        source = None
        frame = None

        if len(args) > 0:
            if isinstance(args[0], FramePushed):
                frame = args[0].frame
                source = args[0].source
            else:
                source = args[0] 
                for arg in args:
                    if isinstance(arg, Frame):
                        frame = arg
                        break
        
        if not frame:
            return

        src_name = str(source) if source else ""

        if isinstance(frame, UserStoppedSpeakingFrame):
            self.last_user_stop_time = datetime.now().isoformat()

        elif isinstance(frame, TranscriptionFrame):
            if "STT" in src_name:
                use_time = self.last_user_stop_time
                self._append_log("user", frame.text, timestamp=use_time)
                self.last_user_stop_time = None

        elif "LLM" in src_name and "Aggregator" not in src_name:
            if isinstance(frame, LLMFullResponseStartFrame):
                self.bot_text_buffer = []

            elif isinstance(frame, TextFrame):
                self.bot_text_buffer.append(frame.text)

            elif isinstance(frame, LLMFullResponseEndFrame):
                self.pending_bot_text = "".join(self.bot_text_buffer)
                self.bot_text_buffer = []

        elif isinstance(frame, BotStartedSpeakingFrame):
            if self.pending_bot_text:
                self._append_log("assistant", self.pending_bot_text, timestamp=datetime.now().isoformat())
                self.pending_bot_text = ""

        return

class UnifiedTurnLogger(UserBotLatencyLogObserver):
    
    def __init__(self, output_filepath: str):
        super().__init__()
        self.output_filepath = output_filepath
        
        # Transcription tracking
        self.bot_text_buffer = []
        self.pending_bot_text = ""
        self.pending_user_text = ""
        self.last_user_stop_time = None
        
        # Latency tracking
        self.captured_latencies = []
        
        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
        
        self.log_data = {
            "session_start": datetime.now().isoformat(),
            "turns": [],
            "summary": None
        }
        self._save_json()

    def _save_json(self):
        try:
            with open(self.output_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.log_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving unified log JSON: {e}")

    def _log_latency(self, latency: float):
        super()._log_latency(latency)
        self.captured_latencies.append(latency)
        
        # At this point we have: user text, bot text, and latency
        if self.pending_user_text and self.pending_bot_text:
            turn = {
                "turn_number": len(self.log_data["turns"]) + 1,
                "timestamp": self.last_user_stop_time or datetime.now().isoformat(),
                "user": {
                    "text": self.pending_user_text.strip(),
                    "stopped_speaking_at": self.last_user_stop_time
                },
                "assistant": {
                    "text": self.pending_bot_text.strip(),
                    "started_speaking_at": datetime.now().isoformat()
                },
                "latency": {
                    "seconds": round(latency, 4),
                    "milliseconds": round(latency * 1000, 2)
                }
            }
            
            self.log_data["turns"].append(turn)
            self._save_json()
            
            print(f"[UNIFIED] Turn #{turn['turn_number']} | Latency: {turn['latency']['milliseconds']}ms | User: '{self.pending_user_text[:50]}...'")
            
            # Reset for next turn
            self.pending_user_text = ""
            self.pending_bot_text = ""
            self.last_user_stop_time = None

    def _log_summary(self):
        super()._log_summary()
        
        if not self.captured_latencies:
            return
        
        avg_lat = sum(self.captured_latencies) / len(self.captured_latencies)
        min_lat = min(self.captured_latencies)
        max_lat = max(self.captured_latencies)
        
        self.log_data["summary"] = {
            "session_end": datetime.now().isoformat(),
            "total_turns": len(self.log_data["turns"]),
            "latency_stats": {
                "count": len(self.captured_latencies),
                "average_seconds": round(avg_lat, 4),
                "min_seconds": round(min_lat, 4),
                "max_seconds": round(max_lat, 4),
                "average_milliseconds": round(avg_lat * 1000, 2),
                "min_milliseconds": round(min_lat * 1000, 2),
                "max_milliseconds": round(max_lat * 1000, 2)
            }
        }
        self._save_json()

    async def on_push_frame(self, frame_pushed: FramePushed):
        # First, let parent handle latency tracking
        await super().on_push_frame(frame_pushed)
        
        frame = frame_pushed.frame
        source = frame_pushed.source
        src_name = str(source) if source else ""

        # Capture user stopped speaking timestamp
        if isinstance(frame, UserStoppedSpeakingFrame):
            self.last_user_stop_time = datetime.now().isoformat()

        # Capture user transcript from STT (same as JsonTranscriptionObserver)
        elif isinstance(frame, TranscriptionFrame):
            if "STT" in src_name and frame.text and frame.text.strip():
                self.pending_user_text = frame.text

        # Capture bot text from LLM (same as JsonTranscriptionObserver)
        elif "LLM" in src_name and "Aggregator" not in src_name:
            if isinstance(frame, LLMFullResponseStartFrame):
                self.bot_text_buffer = []
            elif isinstance(frame, TextFrame):
                self.bot_text_buffer.append(frame.text)
            elif isinstance(frame, LLMFullResponseEndFrame):
                self.pending_bot_text = "".join(self.bot_text_buffer)
                self.bot_text_buffer = []