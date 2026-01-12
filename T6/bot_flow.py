import os
import wave
from datetime import datetime
from dotenv import load_dotenv
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.base_transport import TransportParams
from pipecat.runner.types import RunnerArguments
from pipecat_flows import FlowManager, FlowsFunctionSchema, NodeConfig
from pipecat_flows.types import FlowResult
from observer import SessionObserver as LatencyObserver

load_dotenv()


# Node 1: Greeting & Small Talk
# Node 2: Menu Browsing
# Node 3: Placing Order
# Node 4: Closing/Completing Order

#function handlers

async def browse_menu_handler(args, flow_manager: FlowManager) -> tuple[FlowResult, NodeConfig]:
    # Handle transition to menu browsing
    interest = args.get("interest", "")
    print(f"🍕 Transitioning to menu browsing. Interest: {interest}")
    return {"interest": interest}, create_menu_browsing_node()


async def place_order_handler(args, flow_manager: FlowManager) -> tuple[FlowResult, NodeConfig]:
    # Handle transition to ordering
    item = args.get("item", "")
    print(f"📝 Transitioning to ordering. Item: {item}")
    return {"item": item}, create_ordering_node()


async def complete_order_handler(args, flow_manager: FlowManager) -> tuple[FlowResult, NodeConfig]:
    # Handle order completion
    ready = args.get("ready", True)
    print(f"✅ Completing order. Ready: {ready}")
    return {"ready": ready}, create_closing_node()

#nodes

def create_greeting_node() -> NodeConfig:
    # Create the initial greeting node
    browse_menu_func = FlowsFunctionSchema(
        name="browse_menu",
        description="Transition to browsing the menu when customer shows interest in menu options or asks about food items",
        required=[],
        handler=browse_menu_handler,
        properties={
            "interest": {
                "type": "string",
                "description": "What the customer is interested in (e.g., 'pizza', 'burger', 'specials')"
            }
        }
    )
    
    return NodeConfig(
        name="greeting_node",
        role_messages=[
            {
                "role": "system",
                "content": """You are Zara, a friendly restaurant customer at Cheezeous (pizzas, burgers, fries).
                                Speak naturally with contractions, keep responses short (1-3 sentences).

                            **GREETING & SMALL TALK:**
                            - Greet naturally: "Hi there!" or "Good evening!"
                            - Make light small talk about the day or mood
                            - Ask for suggestions or popular items
                            - When ready to browse, transition by asking about menu items"""
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """Greet the server warmly and engage in brief small talk."
                                Do not call any function unless the user explicitly asks about menu items or recommendations;
                                otherwise respond with text only. When the user asks to browse the menu or for recommendations,
                                then use the browse_menu function to transition."""
            }
        ],
        functions=[browse_menu_func]
    )


def create_menu_browsing_node() -> NodeConfig:
    """Create the menu browsing node."""
    place_order_func = FlowsFunctionSchema(
        name="place_order",
        description="Transition to placing an order when customer has decided what to eat",
        required=[],
        handler=place_order_handler,
        properties={
            "item": {
                "type": "string",
                "description": "The item(s) the customer wants to order"
            }
        }
    )
    
    return NodeConfig(
        name="menu_browsing_node",
        task_messages=[
            {
                "role": "system",
                "content": """You are Zara browsing the menu at Cheezeous. Keep responses short (1-3 sentences).

                            - Ask about specials, ingredients, sizes, or prices
                            - Show realistic indecision and ask for recommendations
                            - When you've decided what to order, use the place_order function to proceed"""
            }
        ],
        functions=[place_order_func]
    )


def create_ordering_node() -> NodeConfig:
    """Create the ordering node."""
    complete_order_func = FlowsFunctionSchema(
        name="complete_order",
        description="Transition to completing the order when customer is satisfied with their order",
        required=[],
        handler=complete_order_handler,
        properties={
            "ready": {
                "type": "boolean",
                "description": "Whether the customer is ready to finalize"
            }
        }
    )
    
    return NodeConfig(
        name="ordering_node",
        task_messages=[
            {
                "role": "system",
                "content": """You are Zara placing your order at Cheezeous. Keep responses short (1-3 sentences).

                            - Specify items clearly (e.g., "I'll take one Medium Chicken Tikka Pizza, please")
                            - Answer questions about size, add-ons, or customization
                            - Ask for extras or make changes naturally
                            - When you're satisfied with your order, use the complete_order function to finalize"""
            }
        ],
        functions=[complete_order_func]
    )


def create_closing_node() -> NodeConfig:
    """Create the closing node."""
    return NodeConfig(
        name="closing_node",
        task_messages=[
            {
                "role": "system",
                "content": """You are Zara finalizing your order at Cheezeous. Keep responses short (1-3 sentences).

                            - Confirm your final order with the server
                            - Ask about wait time or payment if needed
                            - Thank the server and wrap up the conversation naturally"""
            }
        ],
        functions=[]
    )

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
    )

    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.1-8b-instant"
    )

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id=os.getenv("CARTESIA_VOICE"),
    )

    context = OpenAILLMContext()
    context_aggregator = llm.create_context_aggregator(context)

    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_dir = os.path.join(os.path.dirname(__file__), "Recordings", session_timestamp)
    os.makedirs(audio_dir, exist_ok=True)

    audiobuffer = AudioBufferProcessor(
        num_channels=1,
        buffer_size=0,
    )

    observer = LatencyObserver(filename=os.path.join(audio_dir, "conversation_metrics.json"))

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        audiobuffer,
    ])

    task = PipelineTask(
        pipeline=pipeline,
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
        """Save audio when recording stops."""
        if len(audio) == 0:
            return
        
        os.makedirs("Recordings", exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Recordings/audio_{timestamp}.wav"
        
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio)
        
        print(f"Audio saved: {filename}")

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        """Start recording and initialize flow when client connects."""
        await audiobuffer.start_recording()
        print("Recording started")
        print("🌊 Initialized - Starting with greeting_node")
        # Initialize the flow with the first node
        await flow_manager.initialize(create_greeting_node())

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        """Stop recording when client disconnects."""
        await audiobuffer.stop_recording()
        print("Recording stopped")

    runner = PipelineRunner(handle_sigint=True)
    await runner.run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
