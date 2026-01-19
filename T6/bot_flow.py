"""
Restaurant Calling Bot using Pipecat Flows (Dynamic Flows pattern).
"""

import os
import wave
from datetime import datetime
from dotenv import load_dotenv

# Pipecat services
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.groq.stt import GroqSTTService

# Pipecat pipeline components
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask

# Pipecat aggregators and context
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.aggregators.llm_context import LLMContext

# --- TEXT PROCESSOR FOR FILTERING SYNTAX ---
from pipecat.processors.aggregators.llm_text_processor import LLMTextProcessor
from pipecat.utils.text.pattern_pair_aggregator import PatternPairAggregator, MatchAction
# -------------------------------------------

# Audio processing
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor

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

# Import observer
from observer import SessionObserver

import pytz

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
    
    # SERVICES
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
    )
    
    messages = []
    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)
    
    # --- TEXT PROCESSOR SETUP ---
    text_filter = PatternPairAggregator()
    
    # Filter 1: Catch Markdown code blocks
    text_filter.add_pattern(
        type="code_block",
        start_pattern="```",
        end_pattern="```",
        action=MatchAction.AGGREGATE
    )
    
    # Filter 2: Catch standalone JSON objects
    text_filter.add_pattern(
        type="json_object",
        start_pattern="{",
        end_pattern="}",
        action=MatchAction.AGGREGATE
    )

    # Filter 3: Catch XML-style function hallucinations (The specific fix for your error)
    text_filter.add_pattern(
        type="xml_function",
        start_pattern="<function",
        end_pattern="</function>",
        action=MatchAction.AGGREGATE
    )

    llm_text_processor = LLMTextProcessor(text_aggregator=text_filter)
    # ----------------------------
    
    # RECORDING SETUP
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_dir = os.path.join(os.path.dirname(__file__), "Recordings", session_timestamp)
    os.makedirs(audio_dir, exist_ok=True)

    audiobuffer = AudioBufferProcessor(
        num_channels=1,
        buffer_size=0,
    )
    
    observer = SessionObserver(filename=os.path.join(audio_dir, "conversation_metrics.json"))
    
    # PIPELINE
    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        llm_text_processor, # Filters text before it hits TTS
        tts,
        transport.output(),
        context_aggregator.assistant(),
        audiobuffer,
    ])
    
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            observers=[observer],
        )
    )
    
    flow_manager = FlowManager(
        task=task,
        llm=llm,
        context_aggregator=context_aggregator,
        transport=transport,
    )
    
    @audiobuffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        if len(audio) == 0:
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(audio_dir, f"audio_{timestamp}.wav")
        
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio)
    
    @transport.event_handler('on_client_connected')
    async def handle_client_connected(transport: SmallWebRTCTransport, client):
        await audiobuffer.start_recording()
        
        tz = pytz.timezone('Asia/Karachi')
        current_time = datetime.now(tz)
        print(f"\n📡 CLIENT CONNECTED | {current_time.strftime('%I:%M %p')}")
        
        await flow_manager.initialize(create_greet_node())
    
    @transport.event_handler('on_client_disconnected')
    async def handle_client_disconnected(transport: SmallWebRTCTransport, client):
        await audiobuffer.stop_recording()
        print("\n👋 CLIENT DISCONNECTED")
        await task.cancel()
    
    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()