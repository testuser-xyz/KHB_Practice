"""
Restaurant Chatbot using Pipecat Flows (Dynamic Flows pattern).

This bot demonstrates:
- FlowManager for managing conversation flow
- NodeConfig with FlowsFunctionSchema for transitions
- State management in flow_manager.state
- Integration with Pipecat pipeline (STT, LLM, TTS)
"""

import os
from dotenv import load_dotenv

# Pipecat services
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.groq.stt import GroqSTTService

# Pipecat observers
from pipecat.observers.loggers.llm_log_observer import LLMLogObserver
from pipecat.observers.loggers.transcription_log_observer import TranscriptionLogObserver
from pipecat.observers.turn_tracking_observer import TurnTrackingObserver
from pipecat.observers.loggers.user_bot_latency_log_observer import UserBotLatencyLogObserver as LatencyObserver

# Pipecat pipeline components
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask

# Pipecat aggregators and context
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.aggregators.llm_context import LLMContext

# Voice Activity Detection
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3

# Transport
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.base_transport import TransportParams
from pipecat.runner.types import RunnerArguments

# Pipecat Flows
from pipecat_flows import FlowManager

# Import our nodes
from nodes import create_greet_node

import pytz
from datetime import datetime

load_dotenv()


def _require_env(key: str, fallback_key: str | None = None) -> str:
    """Fetch required API key with optional fallback and raise a clear error if missing."""
    value = os.getenv(key) or (os.getenv(fallback_key) if fallback_key else None)
    if not value:
        missing = f"Missing API key: set {key}" + (f" or {fallback_key}" if fallback_key else "")
        raise RuntimeError(missing)
    return value


async def bot(runner_args: RunnerArguments):
    """
    Main bot function that sets up the Pipecat pipeline with Flows.
    
    Args:
        runner_args: WebRTC connection details and configuration
    """
    
    # ========================================================================
    # TRANSPORT SETUP
    # ========================================================================
    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,      # Capture user microphone input
            audio_out_enabled=True,     # Send bot speech back to user
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),  # Natural turn completion
        )
    )
    
    # ========================================================================
    # SERVICES SETUP (STT, LLM, TTS)
    # ========================================================================
    stt = GroqSTTService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="whisper-large-v3",
        audio_passthrough=True
    )
    
    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.1-8b-instant"
    )
    
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22"
    )
    
    # ========================================================================
    # CONTEXT SETUP
    # ========================================================================
    # Initialize with empty messages - FlowManager will handle role/task messages
    messages = []
    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)
    
    # ========================================================================
    # PIPELINE SETUP
    # ========================================================================
    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),      # Add user message to context
        llm,
        tts,
        transport.output(),              # Send bot speech back to user
        context_aggregator.assistant()   # Add assistant message to context
    ])
    
    # ========================================================================
    # TASK SETUP
    # ========================================================================
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,  # Allow user to interrupt bot mid-speech
            observers=[
                LLMLogObserver(),              # Debug: LLM internals
                TranscriptionLogObserver(),    # Console: User speech-to-text
                TurnTrackingObserver(),        # Track: Turn management
                LatencyObserver(),             # Console: Response latency
            ]
        )
    )
    
    # ========================================================================
    # FLOW MANAGER SETUP
    # ========================================================================
    flow_manager = FlowManager(
        task=task,
        llm=llm,
        context_aggregator=context_aggregator,
        transport=transport,
    )
    
    # ========================================================================
    # TRANSPORT EVENT HANDLERS
    # ========================================================================
    @transport.event_handler('on_client_connected')
    async def handle_client_connected(transport: SmallWebRTCTransport, client):
        """
        Initialize the flow when client connects.
        """
        # Get current time in Asia/Karachi timezone
        tz = pytz.timezone('Asia/Karachi')
        current_time = datetime.now(tz)
        day = current_time.strftime("%A")
        date = current_time.strftime("%Y-%m-%d")
        time = current_time.strftime("%I:%M %p")
        
        print("\n" + "="*80)
        print(f"📡 CLIENT CONNECTED | Time: {time} | {day}, {date}")
        print("="*80)
        print("💬 Starting conversation with greeting...")
        print("🔄 Initializing Flow Manager with greet node\n")
        
        # Initialize the flow with the greet node
        await flow_manager.initialize(create_greet_node())
    
    @transport.event_handler('on_client_disconnected')
    async def handle_client_disconnected(transport: SmallWebRTCTransport, client):
        """
        Clean up when client disconnects.
        """
        print("\n" + "="*80)
        print("👋 CLIENT DISCONNECTED")
        print("="*80)
        
        # Cancel the task to clean up resources
        await task.cancel()
    
    # ========================================================================
    # RUN PIPELINE
    # ========================================================================
    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
