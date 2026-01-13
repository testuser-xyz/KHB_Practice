import os
import wave
from datetime import datetime
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat_flows import FlowManager, FlowsFunctionSchema, NodeConfig
from pipecat_flows.types import ActionConfig, FlowResult

load_dotenv()


class SpokenResult(FlowResult):
    """FlowResult subclass that carries a spoken message."""

    def __init__(self, message: str, status: str = "ok"):
        super().__init__(status=status, error="")
        self["message"] = message


def ensure_order_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Guarantee order scaffolding in the shared flow state."""
    order = state.setdefault("order", {})
    order.setdefault("category", None)
    order.setdefault("items", [])
    order.setdefault("notes", [])
    return order


def summarize_order(order: Dict[str, Any]) -> str:
    items = order.get("items", [])
    if not items:
        return "no items yet"
    parts: List[str] = []
    for entry in items:
        details = [entry.get("name", "item")]
        if entry.get("size"):
            details.append(entry["size"])
        if entry.get("quantity"):
            details.append(f"x{entry['quantity']}")
        if entry.get("extras"):
            details.append(entry["extras"])
        parts.append(" ".join(details))
    return ", ".join(parts)


class RestaurantFlowBuilder:
    """Creates dynamic nodes for the restaurant ordering journey."""

    def __init__(self, flow_manager: FlowManager):
        self.flow_manager = flow_manager
        self.shared_note_function = self._create_shared_note_function()

    def _phase_action(self, phase_name: str) -> ActionConfig:
        async def marker(args: Dict[str, Any], manager: FlowManager):
            manager.state["phase"] = phase_name

        return ActionConfig(type="function", handler=marker, text=f"phase:{phase_name}")

    def _snapshot_order_action(self) -> ActionConfig:
        async def snapshot(args: Dict[str, Any], manager: FlowManager):
            order = ensure_order_state(manager.state)
            manager.state["last_summary"] = summarize_order(order)

        return ActionConfig(type="function", handler=snapshot, text="snapshot:order")

    def _create_shared_note_function(self) -> FlowsFunctionSchema:
        async def store_note(args: Dict[str, Any], manager: FlowManager):
            note = args.get("note", "")
            order = ensure_order_state(manager.state)
            if note:
                order["notes"].append(note)
            return SpokenResult("Saved that note."), None

        return FlowsFunctionSchema(
            name="record_note",
            description="Persist a customer note that applies across the conversation",
            required=[],
            properties={
                "note": {
                    "type": "string",
                    "description": "Allergy, timing, or preference note to store in order state",
                }
            },
            handler=store_note,
        )

    # Node factories -----------------------------------------------------
    def build_intro_node(self) -> NodeConfig:
        category_selector = FlowsFunctionSchema(
            name="select_food_category",
            description="Move to category exploration once the caller names what they want",
            required=[],
            properties={
                "category": {
                    "type": "string",
                    "description": "One of pizza, burgers, sides, drinks, or desserts",
                }
            },
            handler=self._handle_category_choice,
        )

        return NodeConfig(
            name="intro_stage",
            role_messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Zara, a friendly customer calling Cheezeous to place an order. "
                        "Speak casually for voice, use contractions, stay concise with one or two sentences. "
                        "No emojis, no markdown, no special characters."
                    ),
                }
            ],
            task_messages=[
                {
                    "role": "system",
                    "content": (
                        "Greet the staff, ask what they recommend, then guide them to choose a food category "
                        "like pizza, burgers, sides, drinks, or desserts. Call select_food_category when they decide."
                    ),
                }
            ],
            functions=[category_selector, self.shared_note_function],
            pre_actions=[self._phase_action("intro")],
            post_actions=[],
        )

    def build_category_node(self) -> NodeConfig:
        detail_start = FlowsFunctionSchema(
            name="open_item_details",
            description="Begin capturing item specifics for the chosen category",
            required=[],
            properties={
                "focus": {
                    "type": "string",
                    "description": "What in the category caught their attention",
                }
            },
            handler=self._handle_enter_details,
        )

        return NodeConfig(
            name="category_stage",
            task_messages=[
                {
                    "role": "system",
                    "content": (
                        "You are helping the caller browse their chosen category. "
                        "Offer quick highlights, portion sizes, combos, and prices. "
                        "Keep it light and conversational; ask one question at a time. "
                        "Use open_item_details when they are ready to talk specifics."
                    ),
                }
            ],
            functions=[detail_start, self.shared_note_function],
            pre_actions=[self._phase_action("category")],
            post_actions=[],
        )

    def build_detail_node(self) -> NodeConfig:
        add_item = FlowsFunctionSchema(
            name="capture_item",
            description="Store item details for the order",
            required=["name"],
            properties={
                "name": {"type": "string", "description": "Menu item name"},
                "size": {"type": "string", "description": "Size or portion"},
                "quantity": {"type": "integer", "description": "How many"},
                "extras": {"type": "string", "description": "Add-ons or customizations"},
            },
            handler=self._handle_item_capture,
        )

        request_review = FlowsFunctionSchema(
            name="review_order",
            description="Move to confirmation and read back the current order",
            required=[],
            properties={},
            handler=self._handle_review_request,
        )

        return NodeConfig(
            name="detail_stage",
            task_messages=[
                {
                    "role": "system",
                    "content": (
                        "Collect specifics for the chosen category. Ask about size, toppings, combos, and quantity. "
                        "After capturing details, call capture_item. When they are ready to hear the order, call review_order."
                    ),
                }
            ],
            functions=[add_item, request_review, self.shared_note_function],
            pre_actions=[self._phase_action("details")],
            post_actions=[],
        )

    def build_review_node(self) -> NodeConfig:
        order = ensure_order_state(self.flow_manager.state)
        summary_text = summarize_order(order)

        approve = FlowsFunctionSchema(
            name="finalize_checkout",
            description="Confirm the order and move to closing",
            required=[],
            properties={
                "confirm": {"type": "boolean", "description": "True when the caller is satisfied"},
            },
            handler=self._handle_final_confirmation,
        )

        revise = FlowsFunctionSchema(
            name="revise_items",
            description="Let the caller change items and return to detail capture",
            required=[],
            properties={
                "change": {"type": "string", "description": "What to adjust or add"},
            },
            handler=self._handle_revise_request,
        )

        return NodeConfig(
            name="review_stage",
            task_messages=[
                {
                    "role": "system",
                    "content": (
                        f"Read back the order: {summary_text}. Ask if anything needs to change. "
                        "Offer to adjust sizes, swap flavors, or add sides. Use finalize_checkout to lock it in or revise_items to change it."
                    ),
                }
            ],
            functions=[approve, revise, self.shared_note_function],
            pre_actions=[self._phase_action("review")],
            post_actions=[self._snapshot_order_action()],
        )

    def build_close_node(self) -> NodeConfig:
        order = ensure_order_state(self.flow_manager.state)
        summary_text = summarize_order(order)

        return NodeConfig(
            name="farewell_stage",
            task_messages=[
                {
                    "role": "system",
                    "content": (
                        f"Thank the staff, confirm the final order ({summary_text}), ask for pickup or delivery timing, "
                        "and end politely. No emojis or special characters."
                    ),
                }
            ],
            functions=[self.shared_note_function],
            pre_actions=[self._phase_action("closing")],
            post_actions=[],
            respond_immediately=True,
        )

    # Handlers -----------------------------------------------------------
    async def _handle_category_choice(self, args: Dict[str, Any], manager: FlowManager) -> Tuple[FlowResult, NodeConfig]:
        order = ensure_order_state(manager.state)
        chosen = args.get("category", "menu")
        order["category"] = chosen
        return SpokenResult(f"Looking at {chosen} now."), self.build_category_node()

    async def _handle_enter_details(self, args: Dict[str, Any], manager: FlowManager) -> Tuple[FlowResult, NodeConfig]:
        focus = args.get("focus", "the options")
        return SpokenResult(f"Let us lock in details for {focus}.", status="ok"), self.build_detail_node()

    async def _handle_item_capture(self, args: Dict[str, Any], manager: FlowManager) -> Tuple[FlowResult, NodeConfig]:
        order = ensure_order_state(manager.state)
        item = {
            "name": args.get("name", "item"),
            "size": args.get("size"),
            "quantity": args.get("quantity", 1),
            "extras": args.get("extras"),
        }
        order["items"].append(item)
        message = summarize_order(order)
        return SpokenResult(f"Added it. Current order: {message}"), self.build_detail_node()

    async def _handle_review_request(self, args: Dict[str, Any], manager: FlowManager) -> Tuple[FlowResult, NodeConfig]:
        order = ensure_order_state(manager.state)
        summary = summarize_order(order)
        return SpokenResult(f"Here is what I have: {summary}"), self.build_review_node()

    async def _handle_final_confirmation(self, args: Dict[str, Any], manager: FlowManager) -> Tuple[FlowResult, NodeConfig]:
        confirm = bool(args.get("confirm", False))
        if confirm:
            return SpokenResult("Order confirmed."), self.build_close_node()
        return SpokenResult("I will keep the order open."), self.build_review_node()

    async def _handle_revise_request(self, args: Dict[str, Any], manager: FlowManager) -> Tuple[FlowResult, NodeConfig]:
        change = args.get("change", "a change")
        order = ensure_order_state(manager.state)
        if order.get("items"):
            order["items"] = order["items"][:-1]
        return SpokenResult(f"No problem, we will adjust {change} now."), self.build_detail_node()


async def bot(runner_args: RunnerArguments):
    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        ),
    )

    stt = GroqSTTService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="whisper-large-v3",
    )

    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.1-8b-instant",
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

    audiobuffer = AudioBufferProcessor(num_channels=1, buffer_size=0)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
            audiobuffer,
        ]
    )

    task = PipelineTask(
        pipeline=pipeline,
        params=PipelineParams(
            allow_interruptions=True,
        ),
    )

    flow_manager = FlowManager(
        task=task,
        llm=llm,
        context_aggregator=context_aggregator,
        tts=tts,
        transport=transport,
    )

    builder = RestaurantFlowBuilder(flow_manager)

    @audiobuffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        if len(audio) == 0:
            return
        filename = os.path.join(audio_dir, f"audio_{datetime.now().strftime('%H%M%S')}.wav")
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio)

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        await audiobuffer.start_recording()
        await flow_manager.initialize(builder.build_intro_node())

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await audiobuffer.stop_recording()
        await task.cancel()

    runner = PipelineRunner(handle_sigint=True)
    await runner.run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
