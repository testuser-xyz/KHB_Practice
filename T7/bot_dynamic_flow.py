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
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.base_transport import TransportParams
from pipecat.runner.types import RunnerArguments
from pipecat_flows import FlowManager, FlowsFunctionSchema, NodeConfig, FlowConfig
from typing import Optional

# Import observers from T5
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'T5'))
from observer import TurnMetricsObserver as LatencyObserver

load_dotenv()

# ============================================================================
# DYNAMIC FLOW - NODE GENERATORS
# ============================================================================
# This approach uses Python functions to generate NodeConfig objects at runtime
# and FlowsFunctionSchema handlers to manage state transitions dynamically.
# ============================================================================

class ZaraFlowBuilder:
    """
    Dynamic Flow Builder for Zara (the customer bot).
    
    Instead of defining the full flow upfront, we create nodes dynamically
    as the conversation progresses, using function handlers to transition
    between states.
    """
    
    def __init__(self, flow_manager: FlowManager):
        self.flow_manager = flow_manager
    
    # ========================================================================
    # NODE GENERATORS
    # ========================================================================
    
    def create_greeting_node(self) -> NodeConfig:
        """
        NODE 1: Greeting & Small Talk
        Based on USE CASE 1 from prompts.py
        """
        return NodeConfig(
            role_messages=[
                {
                    "role": "system",
                    "content": """You are Zara, a friendly and realistic restaurant customer at Cheezeous (a fast food restaurant known for pizzas, burgers, and fries).

**YOUR PERSONALITY:**
- Warm, curious, and polite
- Speak naturally with casual human speech, including contractions ("I'd like", "I'm thinking")
- Add small talk or light humor occasionally ("This place smells amazing!", "I hope I don't make a tough choice")
- Keep responses short (1-3 sentences) as this is a voice conversation
- React appropriately to staff responses and follow-up questions

**CURRENT PHASE: GREETING & SMALL TALK**
- Greet the server naturally: "Hi there!" or "Good evening!"
- Make small talk about time, day, or mood: "It's such a busy evening"
- Respond politely to server greetings
- Ask for suggestions or popular items

**BEHAVIOR RULES:**
1. Keep Responses Short: Max 1-2 sentences for voice clarity
2. Be Polite: Always courteous, never rude
3. Natural Speech: Use contractions, casual tone, small fillers
4. Be Curious: Show interest in exploring options
5. Stay in Character: You are the customer, not an assistant or AI

**IMPORTANT:**
- When you're ready to browse the menu or ask about food items, call the browse_menu function
- Keep it conversational and natural
- React appropriately to staff responses"""
                }
            ],
            functions=[
                FlowsFunctionSchema(
                    name="browse_menu",
                    description="Transition to browsing the menu when customer shows interest in menu options or asks about food items",
                    parameters={
                        "type": "object",
                        "properties": {
                            "interest": {
                                "type": "string",
                                "description": "What the customer is interested in (e.g., 'pizza', 'burger', 'specials')"
                            }
                        },
                        "required": []
                    },
                    handler=self.handle_browse_menu
                )
            ]
        )
    
    def create_menu_browsing_node(self) -> NodeConfig:
        """
        NODE 2: Menu Browsing
        Based on USE CASE 2 & 4 from prompts.py
        """
        return NodeConfig(
            role_messages=[
                {
                    "role": "system",
                    "content": """You are Zara, continuing your conversation at Cheezeous.

**YOUR PERSONALITY:**
- Warm, curious, and polite
- Show realistic indecision sometimes and ask for recommendations
- Keep responses short (1-3 sentences)
- Be expressive and react naturally to suggestions

**CURRENT PHASE: MENU BROWSING**
- Ask about menu options for the current time (breakfast/lunch/dinner)
- Ask about specials, ingredients, portion sizes, or prices
- Show indecision: "Hmm, I'm not sure what to pick. What do you recommend?"
- Ask for clarification if items are unclear
- Inquire politely about prices or combos: "How much is the Zinger Burger today?"
- Compare items if needed: "Is the Chicken Fajita Pizza more expensive than the Tikka one?"

**HANDLING RECOMMENDATIONS (USE CASE 5):**
- Accept suggestions politely: "Sounds great! I'll try that."
- Decline politely if not interested: "Maybe next time, thanks!"
- Ask follow-up questions: "What makes it special?"

**HANDLING CONFUSION (USE CASE 6):**
- Ask for repetition if not heard clearly: "Sorry, could you say that again?"
- Express confusion naturally: "Hmm, I'm a bit lost. Can you explain the options again?"
- Respond calmly if item unavailable: "No problem, what would you suggest instead?"

**IMPORTANT:**
- When you've decided what to order, call the place_order function
- If you need more information, keep asking questions naturally
- React to staff recommendations naturally
- Don't rush - show realistic decision-making"""
                }
            ],
            functions=[
                FlowsFunctionSchema(
                    name="place_order",
                    description="Transition to placing an order when customer has decided what to eat",
                    parameters={
                        "type": "object",
                        "properties": {
                            "item": {
                                "type": "string",
                                "description": "The item(s) the customer wants to order"
                            },
                            "confidence": {
                                "type": "string",
                                "enum": ["certain", "uncertain"],
                                "description": "How confident the customer is about their choice"
                            }
                        },
                        "required": []
                    },
                    handler=self.handle_place_order
                ),
                FlowsFunctionSchema(
                    name="ask_more_questions",
                    description="Stay in menu browsing if customer needs more information or clarification",
                    parameters={
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "What the customer wants to know more about"
                            }
                        },
                        "required": []
                    },
                    handler=self.handle_ask_more_questions
                )
            ]
        )
    
    def create_ordering_node(self) -> NodeConfig:
        """
        NODE 3: Placing Order
        Based on USE CASE 3 & 4 from prompts.py
        """
        return NodeConfig(
            role_messages=[
                {
                    "role": "system",
                    "content": """You are Zara, now placing your order at Cheezeous.

**YOUR PERSONALITY:**
- Clear and decisive when ordering
- Polite and responsive to questions
- Natural and conversational
- Show appreciation for help

**CURRENT PHASE: PLACING ORDER**
- Specify items clearly and confirm: "I'll take one Medium Chicken Tikka Pizza, please"
- Answer questions about size, add-ons, or customization: "Medium size, please"
- Ask for extras naturally: "Can I add some fries with that?"
- Change mind if needed: "Actually, can I make that large instead?"
- Accept suggestions politely: "Sounds great! I'll add that."
- Decline politely if not interested: "Maybe next time, thanks!"

**HANDLING QUESTIONS:**
- Size: Respond with preference (Small/Medium/Large)
- Add-ons: Consider and respond ("Yes, please" or "No, thanks")
- Customization: Be specific ("No onions, please" or "Extra cheese")
- Recommendations: React naturally

**IMPORTANT:**
- When you're done ordering and ready to finalize, call the complete_order function
- If you want to add more items or make changes, call the modify_order function
- Respond to confirmation questions from staff clearly
- Keep track of what you've ordered mentally"""
                }
            ],
            functions=[
                FlowsFunctionSchema(
                    name="complete_order",
                    description="Transition to completing the order when customer is satisfied with their complete order",
                    parameters={
                        "type": "object",
                        "properties": {
                            "ready": {
                                "type": "boolean",
                                "description": "Whether the customer is ready to finalize and complete the order"
                            },
                            "order_summary": {
                                "type": "string",
                                "description": "Brief summary of what was ordered"
                            }
                        },
                        "required": []
                    },
                    handler=self.handle_complete_order
                ),
                FlowsFunctionSchema(
                    name="modify_order",
                    description="Stay in ordering phase if customer wants to modify, add items, or make changes",
                    parameters={
                        "type": "object",
                        "properties": {
                            "modification": {
                                "type": "string",
                                "description": "What the customer wants to change or add"
                            }
                        },
                        "required": []
                    },
                    handler=self.handle_modify_order
                )
            ]
        )
    
    def create_closing_node(self) -> NodeConfig:
        """
        NODE 4: Closing/Completing Order
        Based on USE CASE 7 & 8 from prompts.py
        """
        return NodeConfig(
            role_messages=[
                {
                    "role": "system",
                    "content": """You are Zara, finalizing your order at Cheezeous.

**YOUR PERSONALITY:**
- Appreciative and polite
- Confirm understanding
- End on a positive note
- Show excitement about the food

**CURRENT PHASE: COMPLETING ORDER**
- Confirm the final order before server finalizes: "So that's 1 Medium Chicken Tikka Pizza and a Large Fries, right?"
- Ask about estimated waiting time: "How long will that take?"
- Thank the server: "Thanks! Can't wait to try it." or "Thanks so much!"
- Compliment: "This smells amazing!" or "Looks delicious!"

**ADDITIONAL QUESTIONS (USE CASE 8):**
- Payment: "Do you accept cards?" or "Can I pay with cash?"
- Takeaway: "Can I get this to-go?" or "Is this for dine-in?"
- Dietary concerns if applicable: "Is this vegetarian?" (only if relevant)
- Other logistics as needed

**IMPORTANT:**
- This is the final phase of the conversation
- Keep responses warm and appreciative
- Wrap up naturally but don't rush
- Handle any last-minute questions or concerns politely
- Thank the server sincerely
- You can end the conversation naturally after all questions are addressed"""
                }
            ],
            functions=[
                # No functions in closing node - this is the end state
                # Customer can still ask questions, but won't transition to other nodes
            ]
        )
    
    # ========================================================================
    # FUNCTION HANDLERS (State Transition Logic)
    # ========================================================================
    
    async def handle_browse_menu(self, function_name: str, tool_call_id: str, args: dict, result_callback):
        """
        Handler for browse_menu function.
        Transitions from greeting to menu browsing.
        """
        print(f"🔄 [FLOW TRANSITION] greeting → menu_browsing")
        print(f"   Interest: {args.get('interest', 'general menu')}")
        
        # Generate the menu browsing node
        menu_node = self.create_menu_browsing_node()
        
        # Transition to the new node
        await self.flow_manager.set_node(menu_node)
        
        # Call the result callback (required by Pipecat Flows)
        await result_callback(f"Now browsing menu for {args.get('interest', 'items')}")
    
    async def handle_place_order(self, function_name: str, tool_call_id: str, args: dict, result_callback):
        """
        Handler for place_order function.
        Transitions from menu browsing to ordering.
        """
        print(f"🔄 [FLOW TRANSITION] menu_browsing → ordering")
        print(f"   Item: {args.get('item', 'undecided')}")
        print(f"   Confidence: {args.get('confidence', 'unknown')}")
        
        # Generate the ordering node
        ordering_node = self.create_ordering_node()
        
        # Transition to the new node
        await self.flow_manager.set_node(ordering_node)
        
        # Call the result callback
        await result_callback(f"Proceeding to order {args.get('item', 'your selection')}")
    
    async def handle_ask_more_questions(self, function_name: str, tool_call_id: str, args: dict, result_callback):
        """
        Handler for ask_more_questions function.
        Stays in menu browsing node (no transition).
        """
        print(f"🔄 [FLOW STATE] Staying in menu_browsing")
        print(f"   Topic: {args.get('topic', 'general')}")
        
        # Stay in the same node - just acknowledge
        await result_callback(f"Let me help you with {args.get('topic', 'that')}")
    
    async def handle_complete_order(self, function_name: str, tool_call_id: str, args: dict, result_callback):
        """
        Handler for complete_order function.
        Transitions from ordering to closing.
        """
        print(f"🔄 [FLOW TRANSITION] ordering → closing")
        print(f"   Ready: {args.get('ready', 'yes')}")
        print(f"   Order Summary: {args.get('order_summary', 'N/A')}")
        
        # Generate the closing node
        closing_node = self.create_closing_node()
        
        # Transition to the new node
        await self.flow_manager.set_node(closing_node)
        
        # Call the result callback
        await result_callback(f"Finalizing order: {args.get('order_summary', 'your order')}")
    
    async def handle_modify_order(self, function_name: str, tool_call_id: str, args: dict, result_callback):
        """
        Handler for modify_order function.
        Stays in ordering node (no transition).
        """
        print(f"🔄 [FLOW STATE] Staying in ordering")
        print(f"   Modification: {args.get('modification', 'change requested')}")
        
        # Stay in the same node - just acknowledge
        await result_callback(f"Updating order: {args.get('modification', 'your change')}")


async def bot(runner_args: RunnerArguments):
    """
    Main bot function using DYNAMIC FLOW pattern.
    Nodes are generated at runtime, and transitions are managed via function handlers.
    """
    # ========================================================================
    # TRANSPORT SETUP
    # ========================================================================
    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        )
    )

    # ========================================================================
    # SERVICES SETUP
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
        voice_id=os.getenv("CARTESIA_VOICE"),
    )

    # ========================================================================
    # FLOW MANAGER SETUP (DYNAMIC)
    # ========================================================================
    flow_manager = FlowManager(
        task_context=None,  # Will be set later
        llm=llm,
        tts=tts,
    )
    
    # Create the flow builder
    flow_builder = ZaraFlowBuilder(flow_manager)
    
    # Initialize with the greeting node
    initial_node = flow_builder.create_greeting_node()
    await flow_manager.set_node(initial_node)

    # ========================================================================
    # AUDIO RECORDING SETUP
    # ========================================================================
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_dir = os.path.join(os.path.dirname(__file__), "Recordings", session_timestamp)
    os.makedirs(audio_dir, exist_ok=True)

    audiobuffer = AudioBufferProcessor(
        num_channels=1,
        buffer_size=0,
    )

    # ========================================================================
    # PIPELINE SETUP
    # ========================================================================
    pipeline = Pipeline([
        transport.input(),
        stt,
        flow_manager,  # FlowManager replaces context_aggregator + llm + tts
        transport.output(),
        audiobuffer,
    ])

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================
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
        """Start recording when client connects."""
        await audiobuffer.start_recording()
        print("Recording started")
        print("🌊 Dynamic Flow initialized - Starting with greeting_node")
        print("   Nodes will be generated dynamically as conversation progresses")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        """Stop recording when client disconnects."""
        await audiobuffer.stop_recording()
        print("Recording stopped")

    # ========================================================================
    # TASK & RUNNER SETUP
    # ========================================================================
    observer = LatencyObserver(filename=os.path.join(audio_dir, "conversation_metrics.json"))
    
    task = PipelineTask(
        pipeline=pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            observers=[observer],
        )
    )

    # Set the task context for flow_manager
    flow_manager._task_context = task

    runner = PipelineRunner(handle_sigint=True)
    await runner.run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
