import json
import time
import asyncio
import aiofiles
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Optional, List, Dict, Any

from loguru import logger

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    CancelFrame,
    EndFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
    TranscriptionFrame,
    TextFrame,
)
from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.processors.frame_processor import FrameDirection


class SessionJSONObserver(BaseObserver):
    def __init__(self, output_dir: Optional[str] = None):
        super().__init__()
        self._processed_frames = set()
        self._output_dir = Path(output_dir) if output_dir else Path.cwd()
        self._output_file = self._output_dir / "session_logs.json"
        
        self._output_dir.mkdir(parents=True, exist_ok=True)
        
        # Latency state
        self._user_stopped_time = 0
        
        # Session Data
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._transcripts: List[Dict[str, Any]] = []
        self._latency_metrics: List[Dict[str, Any]] = []
        self._statistics: Dict[str, Any] = {}
        
        # Content-based deduplication - track normalized text we've seen
        self._seen_text_chunks = set()
        self._last_text_reset_time = time.time()
        
        # Async write queue to prevent blocking
        self._write_lock = asyncio.Lock()
        self._pending_write_task = None
        
        logger.debug(f"SessionJSONObserver initialized. Output: {self._output_file}")

    async def on_push_frame(self, data: FramePushed):
        # Only capture downstream (output) frames
        if data.direction != FrameDirection.DOWNSTREAM:
            return

        # Prevent duplicate frame processing
        if data.frame.id in self._processed_frames:
            return
        self._processed_frames.add(data.frame.id)

        frame = data.frame
        should_save = False

        #transcript handling
        if isinstance(frame, TranscriptionFrame):
            # User Speech (STT)
            if frame.text and frame.text.strip():
                # Reset seen chunks on new user turn
                self._clear_old_text_chunks()
                self._smart_append("user", frame.text)
                should_save = True

        elif isinstance(frame, TextFrame):
            # Assistant Speech (LLM)
            if frame.text:
                # Normalize text for comparison (remove whitespace)
                normalized = ''.join(frame.text.split()).lower()
                
                # Skip if we've seen this exact content recently
                if normalized in self._seen_text_chunks:
                    logger.debug(f"🔁 Skipping duplicate TextFrame: '{frame.text[:50]}...'")
                    return
                
                # Add to seen chunks
                self._seen_text_chunks.add(normalized)
                
                self._smart_append("assistant", frame.text)
                should_save = True

        # latency tracking
        elif isinstance(frame, VADUserStartedSpeakingFrame):
            self._user_stopped_time = 0
            
        elif isinstance(frame, VADUserStoppedSpeakingFrame):
            self._user_stopped_time = time.time()
            
        elif isinstance(frame, BotStartedSpeakingFrame) and self._user_stopped_time:
            bot_start_time = time.time()
            latency = bot_start_time - self._user_stopped_time
            
            # Clear seen text chunks when bot starts a new response
            self._clear_old_text_chunks()
            
            self._add_latency(self._user_stopped_time, bot_start_time, latency)
            self._user_stopped_time = 0 # Reset
            
            logger.debug(f"⏱️ LATENCY: {latency:.3f}s")
            should_save = True

        # --- 3. END OF SESSION ---
        elif isinstance(frame, (EndFrame, CancelFrame)):
            self._calculate_final_stats()
            should_save = True

        if should_save:
            await self._save_to_json()

    def _clear_old_text_chunks(self):
        """Clear the seen text chunks cache periodically to prevent memory growth"""
        now = time.time()
        # Clear cache every 30 seconds or when switching turns
        if now - self._last_text_reset_time > 30:
            self._seen_text_chunks.clear()
            self._last_text_reset_time = now

    def _format_time(self, t: float) -> str:
        """Helper to get readable timestamp HH:MM:SS.mmm"""
        return datetime.fromtimestamp(t).strftime("%H:%M:%S.%f")[:-3]

    def _smart_append(self, role: str, text: str):
        """
        Intelligently merges text with temporal awareness.
        Deduplication is now handled at the frame level via content hashing.
        """
        now = time.time()
        text = text.strip()
        
        if not text:
            return
        
        # Check if we should append to the last entry
        if self._transcripts and self._transcripts[-1]["role"] == role:
            last_entry = self._transcripts[-1]
            last_update_time = last_entry.get("_last_update_ts", 0)
            
            #If > 3.0 seconds have passed, treat as new turn
            # This helps separate distinct responses
            if (now - last_update_time) > 3.0:
                self._create_new_entry(role, text, now)
                return
            
            # APPEND with smart spacing
            current_content = last_entry["content"]
            if not current_content.endswith(" ") and not text.startswith(" "):
                last_entry["content"] += " " + text
            else:
                last_entry["content"] += text
            last_entry["_last_update_ts"] = now
            
        else:
            self._create_new_entry(role, text, now)

    def _create_new_entry(self, role: str, text: str, timestamp: float):
        entry = {
            "role": role,
            "content": text,
            "timestamp": self._format_time(timestamp),
            "_last_update_ts": timestamp  # Internal use only
        }
        self._transcripts.append(entry)

    def _add_latency(self, start_ts, end_ts, latency):
        entry = {
            "timestamp": self._format_time(end_ts),
            "user_stopped_at": self._format_time(start_ts),
            "bot_started_at": self._format_time(end_ts),
            "latency_seconds": round(latency, 3)
        }
        self._latency_metrics.append(entry)
        self._calculate_final_stats()

    def _calculate_final_stats(self):
        latencies = [x["latency_seconds"] for x in self._latency_metrics]
        if latencies:
            self._statistics = {
                "total_turns": len(latencies),
                "avg_latency": round(mean(latencies), 3),
                "min_latency": round(min(latencies), 3),
                "max_latency": round(max(latencies), 3)
            }

    async def _save_to_json(self):
        """
        Non-blocking async JSON write using aiofiles.
        Prevents audio pops/clicks by avoiding blocking I/O.
        """
        # Create a clean copy of transcripts without the internal '_last_update_ts' key
        clean_transcripts = []
        for t in self._transcripts:
            clean_entry = t.copy()
            clean_entry.pop("_last_update_ts", None)
            clean_transcripts.append(clean_entry)

        output_data = {
            "session_id": self._session_id,
            "statistics": self._statistics,
            "latency_metrics": self._latency_metrics,
            "transcripts": clean_transcripts
        }
        
        try:
            # Use aiofiles for non-blocking async file writes
            # This prevents the event loop from blocking during disk I/O
            async with aiofiles.open(self._output_file, 'w', encoding='utf-8') as f:
                # json.dumps is CPU-bound but fast, here we write async
                json_str = json.dumps(output_data, indent=2, ensure_ascii=False)
                await f.write(json_str)
            
            logger.debug(f"✅ Session data saved async to {self._output_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save session JSON: {e}")
