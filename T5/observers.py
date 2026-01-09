import json
from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.processors.frame_processor import FrameDirection
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    StartInterruptionFrame
)

class SpeechEventObserver(BaseObserver):
    """
    Observer that tracks conversation turns and calculates latency.
    
    A "Turn" is defined as: 
    User Starts -> User Stops -> Bot Starts -> Bot Stops (or is Interrupted).
    """
    
    def __init__(self):
        super().__init__()
        self.turn_count = 1
        
        # PERSISTENT STATE: Tracks when the bot finished in the PREVIOUS turn
        self.last_bot_stop_time = None 
        
        # CURRENT STATE: Holds data for the active turn
        self.current_turn = self._create_empty_turn(self.turn_count)

    def _create_empty_turn(self, turn_id):
        return {
            "turn_id": turn_id,
            "latency_from_bot_user": None, # Time between Prev Bot Stop -> Curr User Start
            "user_start": None,
            "user_stop": None,
            "bot_start": None,
            "bot_stop": None,
            "interrupted": False,
            "interruption_time": None
        }

    async def on_push_frame(self, data: FramePushed):
        # Convert nanoseconds to seconds
        time_sec = data.timestamp / 1_000_000_000
        frame = data.frame

        # ---------------------------------------------------------
        # 1. USER STARTS SPEAKING (Marks the start of a new turn)
        # ---------------------------------------------------------
        if isinstance(frame, UserStartedSpeakingFrame):
            # If the previous turn was considered "done" (bot stopped or was interrupted),
            # we reset for this new turn.
            if self.current_turn["bot_stop"] is not None or self.current_turn["interrupted"]:
                self.turn_count += 1
                self.current_turn = self._create_empty_turn(self.turn_count)

            # Record Start Time
            if self.current_turn["user_start"] is None:
                self.current_turn["user_start"] = time_sec
                
                # --- CALCULATE LATENCY ---
                # Check when the bot stopped previously
                if self.last_bot_stop_time is not None:
                    latency = time_sec - self.last_bot_stop_time
                    self.current_turn["latency_from_bot_user"] = round(latency, 4)
                else:
                    self.current_turn["latency_from_bot_user"] = 0.0 # First turn

                print(f"\n🟢 [TURN {self.turn_count} OPENED]")

        # ---------------------------------------------------------
        # 2. USER STOPS SPEAKING
        # ---------------------------------------------------------
        elif isinstance(frame, UserStoppedSpeakingFrame):
            self.current_turn["user_stop"] = time_sec

        # ---------------------------------------------------------
        # 3. BOT STARTS SPEAKING
        # ---------------------------------------------------------
        elif isinstance(frame, BotStartedSpeakingFrame):
            self.current_turn["bot_start"] = time_sec

        # ---------------------------------------------------------
        # 4. BOT STOPS SPEAKING (Normal Turn End)
        # ---------------------------------------------------------
        elif isinstance(frame, BotStoppedSpeakingFrame):
            # Only record if we haven't already marked this turn as finished/interrupted
            if not self.current_turn["interrupted"] and self.current_turn["bot_stop"] is None:
                self.current_turn["bot_stop"] = time_sec
                
                # UPDATE PERSISTENT STATE for the next turn
                self.last_bot_stop_time = time_sec
                
                self._print_turn_summary(reason="Normal Completion")

        # ---------------------------------------------------------
        # 5. INTERRUPTION (Abrupt Turn End)
        # ---------------------------------------------------------
        elif isinstance(frame, StartInterruptionFrame):
            # Only process if we haven't already processed an interruption for this turn
            if not self.current_turn["interrupted"]:
                self.current_turn["interruption_time"] = time_sec
                self.current_turn["interrupted"] = True
                
                # UPDATE PERSISTENT STATE: 
                # In an interruption, the bot "stopped" at the moment of interruption.
                self.last_bot_stop_time = time_sec
                
                self._print_turn_summary(reason="Interrupted by User")

    def _print_turn_summary(self, reason):
        """Helper to print the JSON summary cleanly."""
        print(80 * "-")
        print(f"🏁 TURN {self.turn_count} SUMMARY | Status: {reason}")
        print(f"⏱️  Latency (User wait time): {self.current_turn['latency_from_bot_user']}s")
        print(json.dumps(self.current_turn, indent=2))
        print(80 * "-")