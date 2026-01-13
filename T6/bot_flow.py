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
from observer import SessionObserver as LatencyObserver

load_dotenv()

# Node 1: Greeting & Small Talk
# Node 2: Menu Browsing
# Node 3: Placing Order
# Node 4: Closing/Completing Order

# function handlers

async def browse_menu_handler(args, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
    # Handle transition to menu browsing
    interest = args.get("interest", "the general menu")
    # Store interest in state for future nodes
    flow_manager.state["last_interest"] = interest
    print(f"🍕 Transitioning to menu browsing. Interest: {interest}")
    # Return a status message for the LLM and the next node object
    return f"The user is interested in {interest}. Move to menu browsing.", create_menu_browsing_node()


async def place_order_handler(args, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
    # Handle transition to ordering
    item = args.get("item", "")
    # Maintain an order list in state
    if "order_list" not in flow_manager.state:
        flow_manager.state["order_list"] = []
    
    if item:
        flow_manager.state["order_list"].append(item)
        
    print(f"📝 Transitioning to ordering. Item added: {item}")
    return f"Added {item} to order. Transition to ordering node.", create_ordering_node()


async def complete_order_handler(args, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
    # Handle order completion
    ready = args.get("ready", True)
    print(f"✅ Completing order. Ready: {ready}")
    # Final check of the state
    order_summary = ", ".join(flow_manager.state.get("order_list", ["nothing yet"]))
    return f"Order finalized: {order_summary}", create_closing_node()

# nodes

def create_greeting_node() -> NodeConfig:
    # Create the initial greeting node
    browse_menu_func = FlowsFunctionSchema(
        name="browse_menu",
        description="Call this AFTER server tells you menu options. Pass your food interest (pizza, burger, etc.)",
        required=[],
        handler=browse_menu_handler,
        properties={
            "interest": {
                "type": "string",
                "description": "The type of food you're interested in (e.g., 'pizza', 'burgers', 'deals')"
            }
        }
    )
    
    return NodeConfig(
        name="greeting_node",
        respond_immediately=False,
        role_messages=[
            {
                "role": "system",
                "content": """You are Zara, a friendly customer at Cheezeous restaurant. 
                             Speak naturally with contractions, keep responses short (1-3 sentences).
                             Your persona is consistent throughout the session.
                             You must ALWAYS use one of the available functions to progress the conversation."""
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """Greet the server and ask what they have on the menu.
                               WAIT for them to tell you the menu options (burgers, pizzas, etc.).
                               ONLY AFTER they tell you what's available, call browse_menu with your interest.
                               Example: Server says 'We have burgers and pizzas' -> You call browse_menu with interest='pizza'."""
            }
        ],
        functions=[browse_menu_func]
    )


def create_menu_browsing_node() -> NodeConfig:
    """Create the menu browsing node."""
    place_order_func = FlowsFunctionSchema(
        name="place_order",
        description="Call this function when you decide what item to order. This transitions to the ordering phase.",
        required=["item"],
        handler=place_order_handler,
        properties={
            "item": {
                "type": "string",
                "description": "The specific item you decided to order (e.g., 'chicken tikka pizza', 'cheeseburger')"
            }
        }
    )
    
    return NodeConfig(
        name="menu_browsing_node",
        task_messages=[
            {
                "role": "system",
                "content": """Ask about ONE menu item (What's in the chicken tikka pizza? What sizes do you have?).
                               After getting the answer, decide what you want.
                               Then call the place_order function - do NOT just say it, actually invoke the function.
                               The function call will handle the ordering, you just need to decide and call it."""
            }
        ],
        functions=[place_order_func]
    )


def create_ordering_node() -> NodeConfig:
    """Create the ordering node."""
    complete_order_func = FlowsFunctionSchema(
        name="complete_order",
        description="Transition to completing the order when satisfied",
        required=[],
        handler=complete_order_handler,
        properties={
            "ready": {
                "type": "boolean",
                "default": True
            }
        }
    )
    
    return NodeConfig(
        name="ordering_node",
        task_messages=[
            {
                "role": "system",
                "content": """Confirm your order or ask about one add-on (drink, fries, size).
                               After the server responds, confirm you're done.
                               Then call the complete_order function to finalize everything."""
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
                "content": """Finalize the conversation. Thank the server.
                               Ask for the estimated wait time. Wrap up naturally."""
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
        context_aggregator.assistant(),
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
        """Save audio segments."""
        if len(audio) == 0:
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(audio_dir, f"audio_{timestamp}.wav")
        
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio)

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        """Initialize flow when client connects."""
        await audiobuffer.start_recording()
        print("🌊 Initialized - Starting with greeting_node")
        # Initialize with the start node
        await flow_manager.initialize(create_greeting_node())

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        """Clean up on disconnect."""
        await audiobuffer.stop_recording()

    runner = PipelineRunner(handle_sigint=True)
    await runner.run(task)

if __name__ == "__main__":
    from pipecat.runner.run import main
    main()