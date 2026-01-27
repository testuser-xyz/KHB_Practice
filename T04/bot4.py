import os
from dotenv import load_dotenv
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.observers.loggers.llm_log_observer import LLMLogObserver
# from pipecat.observers.loggers.transcription_log_observer import TranscriptionLogObserver
from pipecat.observers.turn_tracking_observer import TurnTrackingObserver
from pipecat.observers.loggers.user_bot_latency_log_observer import UserBotLatencyLogObserver as LatencyObserver
# from pipecat.observers.loggers.debug_log_observer import DebugLogObserver
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.base_transport import TransportParams
from pipecat.runner.types import RunnerArguments
from pipecat.frames.frames import LLMRunFrame, StartInterruptionFrame, UserStoppedSpeakingFrame
import pytz
from datetime import datetime
import asyncio
from prompts import get_system_instruction
from audio_handlers import AudioBufferHandlers
from observers import JsonLatencyObserver, JsonTranscriptionObserver, UnifiedTurnLogger

load_dotenv()

async def bot(runner_args: RunnerArguments):
    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        )
    )

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
        voice_id=os.getenv("CARTESIA_VOICE"),
        params=CartesiaTTSService.InputParams(
            speed="normal",
            emotion=["positivity:high"]
        )
    )

    tz = pytz.timezone("Asia/Karachi")
    current_time = datetime.now(tz)
    day = current_time.strftime("%A")
    date = current_time.strftime("%Y-%m-%d")
    time = current_time.strftime("%I:%M %p")

    system_instruction = get_system_instruction(day, date, time)

    messages = [{"role": "system", "content": system_instruction}]
    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)

    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_dir = os.path.join(os.path.dirname(__file__), "audio_recordings", session_timestamp)
    os.makedirs(audio_dir, exist_ok=True)

    # Separate logs for latency and transcripts
    latency_log_path = os.path.join(audio_dir, "latency_logs.json")
    transcript_log_path = os.path.join(audio_dir, "transcription_logs.json")
    
    # Unified log for both latency and transcripts
    unified_log_path = os.path.join(audio_dir, "unified_turn_logs.json")

    audio_handlers = AudioBufferHandlers(audio_dir)

    # Initialize AudioBufferProcessor
    # - sample_rate: Uses transport's sample rate (auto-detected)
    # - num_channels: 1 for mono (user and bot audio mixed in proper sequence)
    # - buffer_size: 0 means events only trigger when recording stops
    # - enable_turn_audio: True to capture per-turn audio
    audiobuffer = AudioBufferProcessor(
        sample_rate=None,  # Auto-detect from transport
        num_channels=2,     # Stereo: user on one channel, bot on the other
        buffer_size=0,      # Trigger events only on stop
        enable_turn_audio=True  # Enable per-turn audio events
    )

    audio_handlers.setup_handlers(audiobuffer)

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        audiobuffer,
        context_aggregator.assistant()
    ])


    @transport.event_handler('on_client_connected')
    async def handle_client_connected(transport: SmallWebRTCTransport, client):
        print("Client connected. Listening for user input...")
        # Start recording immediately upon connection
        await audiobuffer.start_recording()

    @transport.event_handler('on_client_disconnected')
    async def handle_client_disconnected(transport: SmallWebRTCTransport, client):
        print("Client disconnected:")
        await audiobuffer.stop_recording()
        await task.cancel()

    task = PipelineTask(
        pipeline=pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            observers=[
                LLMLogObserver(),
                JsonTranscriptionObserver(output_filepath=transcript_log_path),
                JsonLatencyObserver(output_filepath=latency_log_path),
                UnifiedTurnLogger(output_filepath=unified_log_path),
                TurnTrackingObserver(),
                # LatencyObserver(),
                # DebugLogObserver()
            ]
        )
    )

    runner = PipelineRunner(handle_sigint=True)
    await runner.run(task)

if __name__ == "__main__":
    from pipecat.runner.run import main
    main()