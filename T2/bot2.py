import os
#access env variables
from dotenv import load_dotenv
#loads env variables from .env
# from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.groq.stt import GroqSTTService
#pipecat services to support stt, llm, tts

#built-in Pipecat observers for monitoring
from pipecat.observers.loggers.llm_log_observer import LLMLogObserver
#tracks the entire lifecycle of LLM interactions, from initial prompts to final responses.
from pipecat.observers.loggers.transcription_log_observer import TranscriptionLogObserver
#logs speech-to-text transcriptions
from pipecat.observers.turn_tracking_observer import TurnTrackingObserver
#monitors conversation turns between user and bot
from pipecat.observers.loggers.user_bot_latency_log_observer import UserBotLatencyLogObserver as LatencyObserver
#measures latency between user and bot responses
# from pipecat.observers.loggers.debug_log_observer import DebugLogObserver
#comprehensive frame logging with configurable filtering for debugging pipeline activity
from pipecat.pipeline.pipeline import Pipeline
#connect services in a pipeline
from pipecat.pipeline.runner import PipelineRunner
# executes the pipeline asynchronously
from pipecat.pipeline.task import PipelineParams, PipelineTask
#wraps pipeline into a task with params
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
#aggregates both user and assistant messages
from pipecat.processors.aggregators.llm_context import LLMContext
#manages conversation history
from pipecat.audio.vad.silero import SileroVADAnalyzer
#voice activation detection, detects speech and silence
from pipecat.audio.vad.vad_analyzer import VADParams
#parameters for voice activity detection
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
#smart turn detection model for natural pauses
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
#captures and buffers audio frames from both user and bot
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
#handles real time audio streaming
from pipecat.transports.base_transport import TransportParams
#configurations 
from pipecat.runner.types import RunnerArguments
#contains webrtc connection details
from pipecat.frames.frames import LLMRunFrame
#frame to trigger LLM processing
import pytz
#timezone handling
from datetime import datetime

#import modular components
from prompts import get_system_instruction, get_greeting_prompt
#system prompts for the voice assistant
from audio_handlers import AudioBufferHandlers
#audio buffer event handlers for recording and analysis
# from observers_handlers import LatencyJSONObserver
from observers_handlers import SessionJSONObserver as LatencyJSONObserver
#custom observer for storing latency metrics in JSON

load_dotenv()

async def bot(runner_args: RunnerArguments):
    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,    #contains webrtc connection details
        params=TransportParams(
            audio_in_enabled=True,      #captures user microphone input
            audio_out_enabled=True,     #sends bot speech back to user
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)), # stop_secs lets Smart Turn decide if the user is truly done  
            turn_analyzer=LocalSmartTurnAnalyzerV3(), #analyzes audio for natural turn completion
        )
    )

    # stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"), audio_passthrough=True)
    stt = GroqSTTService(
        api_key=os.getenv("GROQ_API_KEY"), 
        model="whisper-large-v3",
        audio_passthrough=True  #enable audio passthrough for AudioBufferProcessor
    )
    llm = GroqLLMService(api_key=os.getenv("GROQ_API_KEY"), model="llama-3.1-8b-instant")
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22"
    )

    # Get current time in Asia/Karachi timezone
    tz = pytz.timezone('Asia/Karachi')
    current_time = datetime.now(tz)
    day = current_time.strftime("%A") # Full weekday name
    date = current_time.strftime("%Y-%m-%d") # YYYY-MM-DD format
    time = current_time.strftime("%I:%M %p") # HH:MM AM/PM format

    system_instruction = get_system_instruction(day, date, time)

    messages = [{"role": "system", "content": system_instruction}]
    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)
    
    # Create audio recordings directory with timestamp
    session_timestamp = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
    audio_dir = os.path.join(os.path.dirname(__file__), "audio_recordings", session_timestamp)
    os.makedirs(audio_dir, exist_ok=True)
    
    # Initialize audio buffer handlers
    audio_handlers = AudioBufferHandlers(audio_dir)

    
    # Initialize AudioBufferProcessor
    # - sample_rate: Uses transport's sample rate (auto-detected)
    # - num_channels: 1 for mono (user and bot audio mixed in proper sequence)
    # - buffer_size: 0 means events only trigger when recording stops
    # - enable_turn_audio: True to capture per-turn audio
    audiobuffer = AudioBufferProcessor(
        sample_rate=None,  # Auto-detect from transport
        num_channels=1,     # Mono: user and bot mixed together in temporal sequence
        buffer_size=0,      # Trigger events only on stop
        enable_turn_audio=True  # Enable per-turn audio events
    )

    # Setup all audio event handlers
    audio_handlers.setup_handlers(audiobuffer)
    
    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),  #add user message to context
        llm,
        tts,
        transport.output(),     #send bot speech back to user
        audiobuffer,           #capture audio AFTER output for both user and bot
        context_aggregator.assistant() #add assistant message to context
    ])

    @transport.event_handler('on_client_connected')
    async def handle_client_connected(transport: SmallWebRTCTransport, client):
        print("\n" + "="*80)
        print(f"📡 CLIENT CONNECTED | Time: {time} | {day}, {date}")
        print("="*80)
        print("💬 Starting conversation with greeting...")
        print("📼 Audio buffer recording started\n")
        
        # Start recording audio from both user and bot
        await audiobuffer.start_recording()
        
        # Context-aware greeting based on time of day
        if current_time.hour < 12:
            time_context = "It's breakfast time"
        elif current_time.hour < 17:
            time_context = "It's lunch time"
        else:
            time_context = "It's dinner time"
        
        greeting_prompt = get_greeting_prompt(time_context)
        messages.append({"role": "system", "content": greeting_prompt})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler('on_client_disconnected')
    async def handle_client_disconnected(transport: SmallWebRTCTransport, client):
        # Stop recording and flush any remaining buffered audio
        await audiobuffer.stop_recording()
        
        print("\n" + "="*80)
        print("👋 CLIENT DISCONNECTED")
        print("📼 Audio buffer recording stopped")
        print("="*80)
        
        # Cancel the task to clean up resources
        await task.cancel()
    
    # Built-in observers for monitoring:
    # LLMLogObserver - Logs all LLM requests/responses for debugging
    # TranscriptionLogObserver - Shows what user said (STT output)
    # TurnTrackingObserver - Tracks conversation turn-taking
    # LatencyObserver - Measures response time (user stop → bot start)
    # DebugLogObserver - Frame logging for pipeline debugging
    # LatencyJSONObserver - Custom observer to store latency metrics in JSON
    
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,  # Allow user to interrupt bot mid-speech
            observers=[
                LLMLogObserver(),              # Debug: LLM internals
                TranscriptionLogObserver(),    # Console: User speech-to-text
                TurnTrackingObserver(),        # Track: Turn management
                LatencyObserver(),             # Console: Response latency (logs to terminal)
                LatencyJSONObserver(audio_dir), # Custom: Save latency metrics to JSON
                # DebugLogObserver()             # Debug: Frame logging
            ]
        )
    )
    runner = PipelineRunner(handle_sigint=True)
    await runner.run(task)

if __name__ == "__main__":
    from pipecat.runner.run import main
    main()