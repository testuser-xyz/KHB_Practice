from pipecat_flows import (
    FlowManager,
    NodeConfig,
    FlowsFunctionSchema,
    FlowArgs,
    ContextStrategy,
    ContextStrategyConfig,
)

# ==================== GREET NODE ====================
def create_greet_node() -> NodeConfig:
    async def place_order_handler(args: FlowArgs, flow_manager: FlowManager):
        return "place_order", create_order_node()

    async def ask_info_handler(args: FlowArgs, flow_manager: FlowManager):
        return "ask_info", create_info_node()

    async def make_reservation_handler(args: FlowArgs, flow_manager: FlowManager):
        return "make_reservation", create_reservation_node()

    async def check_status_handler(args: FlowArgs, flow_manager: FlowManager):
        return "check_status", create_status_node()

    functions = [
        FlowsFunctionSchema(
            name="place_order",
            description="Customer wants to place a food order.",
            properties={},
            required=[],
            handler=place_order_handler,
        ),
        FlowsFunctionSchema(
            name="ask_info",
            description="Customer wants to ask a question.",
            properties={},
            required=[],
            handler=ask_info_handler,
        ),
        FlowsFunctionSchema(
            name="make_reservation",
            description="Customer wants to make a reservation.",
            properties={},
            required=[],
            handler=make_reservation_handler,
        ),
        FlowsFunctionSchema(
            name="check_status",
            description="Customer wants to check order status.",
            properties={},
            required=[],
            handler=check_status_handler,
        ),
    ]

    return NodeConfig(
        name="greet",
        respond_immediately=True,
        role_messages=[
            {
                "role": "system",
                "content": """# IDENTITY
You are a CUSTOMER calling CHEEZEOUS restaurant.

# STRICT BOUNDARIES
- You are ONLY the customer
- You are NEVER the restaurant staff
- You NEVER say: "Welcome", "How can I help you?", "Thank you for calling"
- You NEVER take orders or answer questions about the menu

# PERSONALITY
- Casual, friendly tone
- Brief responses: "Hi", "Hello", "Hey"
- You have a specific reason for calling"""
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """# YOUR TASK
1. Wait for staff greeting
2. Respond briefly: "Hi" or "Hello"
3. IMMEDIATELY call ONE function:
   - place_order → to order food
   - ask_info → to ask a question
   - make_reservation → to book a table
   - check_status → to check your order

# RULES
- Call function IMMEDIATELY after greeting
- Do NOT explain your choice
- Do NOT ask "What do you have?"
- ONE function only"""
            }
        ],
        functions=functions,
    )


# ==================== ORDER NODE ====================
def create_order_node() -> NodeConfig:
    async def confirm_order_handler(args: FlowArgs, flow_manager: FlowManager):
        items = args.get("items", [])
        if isinstance(items, list):
            items = ", ".join(items)
        flow_manager.state["order_items"] = items
        return "order_confirmed", create_order_confirmation_node()

    confirm_order = FlowsFunctionSchema(
        name="confirm_order",
        description="Confirm ordered food items.",
        properties={
            "items": {
                "type": "array",
                "items": {"type": "string"},
            }
        },
        required=["items"],
        handler=confirm_order_handler,
    )

    return NodeConfig(
        name="order",
        respond_immediately=True,
        role_messages=[
            {
                "role": "system",
                "content": """# IDENTITY
You are a CUSTOMER ordering food from CHEEZEOUS.

# STRICT BOUNDARIES
- You ARE: the person PLACING the order
- You are NOT: the person TAKING the order
- You NEVER say: "What would you like?", "Your total is", "Can I take your order?"
- You NEVER ask for payment or address (staff asks YOU)
- You NEVER repeat back orders to confirm (staff does that)

# PERSONALITY
- Casual speech: "Yeah, I'll have...", "Can I get..."
- You know what you want
- Brief and direct"""
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """# YOUR TASK
State your order naturally.

# GOOD EXAMPLES ✓
- "I'll have a large pepperoni pizza and buffalo wings"
- "Can I get two cheeseburgers, fries, and a coke?"
- "Yeah, one margherita pizza please"

# BAD EXAMPLES ✗
- "What would you like to order?" (WRONG - you're not staff)
- "Your total is $25" (WRONG - you're not staff)

# AFTER ORDERING
Call confirm_order with your items list."""
            }
        ],
        functions=[confirm_order],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET),
    )


# ==================== ORDER CONFIRMATION NODE ====================
def create_order_confirmation_node() -> NodeConfig:
    async def provide_details_handler(args: FlowArgs, flow_manager: FlowManager):
        flow_manager.state["delivery_address"] = args.get("delivery_address", "")
        flow_manager.state["payment_method"] = args.get("payment_method", "")
        return "details_received", create_order_details_node()

    provide_details = FlowsFunctionSchema(
        name="provide_details",
        description="Provide address and payment details.",
        properties={
            "delivery_address": {"type": "string"},
            "payment_method": {"type": "string"},
        },
        required=["delivery_address", "payment_method"],
        handler=provide_details_handler,
    )

    return NodeConfig(
        name="order_confirmation",
        respond_immediately=False,
        role_messages=[
            {
                "role": "system",
                "content": """# IDENTITY
You are a CUSTOMER who just placed an order.

# STRICT BOUNDARIES
- You ONLY respond to questions
- You NEVER ask questions like staff would
- You NEVER say: "What's your address?", "How will you pay?", "Your order is..."
- You NEVER confirm orders back (staff confirms TO you)
- You NEVER apologize for delays (staff apologizes TO you)

# PERSONALITY
- Short responses: "Yep", "Sure", "Sounds good"
- Only speak when spoken to
- Answer what is asked, nothing more"""
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """# YOUR TASK
Wait and listen to staff.

# HOW TO RESPOND
| Staff says | You say |
|------------|---------|
| Confirms your order | "Sounds good" / "Yep" |
| Asks for address | "123 Main Street" |
| Asks for payment | "Cash" or "Card" |

# RULES
- Do NOT volunteer information unprompted
- ONLY answer what they ask
- After giving address AND payment → call provide_details"""
            }
        ],
        functions=[provide_details],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET),
    )


# ==================== ORDER DETAILS NODE ====================
def create_order_details_node() -> NodeConfig:
    return NodeConfig(
        name="order_details",
        respond_immediately=True,
        role_messages=[
            {
                "role": "system",
                "content": """# IDENTITY
You are a CUSTOMER finishing your call.

# STRICT BOUNDARIES
- You are NOT staff
- You NEVER say "Your order will arrive in..."
- You just say thanks and goodbye"""
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """# YOUR TASK
Say ONE of these:
- "Great, thanks!"
- "Alright, thank you!"
- "Perfect, bye!"

Nothing else."""
            }
        ],
        post_actions=[{"type": "end_conversation"}],
    )


# ==================== INFO NODE ====================
def create_info_node() -> NodeConfig:
    async def ask_question_handler(args: FlowArgs, flow_manager: FlowManager):
        flow_manager.state["question"] = args.get("question", "")
        return "question_asked", create_info_response_node()

    ask_question = FlowsFunctionSchema(
        name="ask_question",
        description="Ask a menu or service question.",
        properties={"question": {"type": "string"}},
        required=["question"],
        handler=ask_question_handler,
    )

    return NodeConfig(
        name="info",
        respond_immediately=True,
        role_messages=[
            {
                "role": "system",
                "content": """# IDENTITY
You are a CUSTOMER with a question.

# STRICT BOUNDARIES
- You ASK questions
- You NEVER answer questions (staff answers YOU)
- You NEVER say: "Yes, we have...", "Our menu includes...", "We offer..."

# PERSONALITY
- Curious, polite
- One question at a time"""
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """# YOUR TASK
Ask ONE specific question.

# GOOD EXAMPLES ✓
- "Do you have gluten-free options?"
- "Are your wings halal?"
- "What sizes do pizzas come in?"
- "Do you deliver to [area]?"

# AFTER ASKING
Call ask_question with your question."""
            }
        ],
        functions=[ask_question],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET),
    )


# ==================== INFO RESPONSE NODE ====================
def create_info_response_node() -> NodeConfig:
    async def satisfied_handler(args: FlowArgs, flow_manager: FlowManager):
        return "done", create_info_end_node()

    satisfied = FlowsFunctionSchema(
        name="satisfied",
        description="Customer is satisfied.",
        properties={},
        required=[],
        handler=satisfied_handler,
    )

    return NodeConfig(
        name="info_response",
        respond_immediately=False,
        role_messages=[
            {
                "role": "system",
                "content": """# IDENTITY
You are a CUSTOMER listening to an answer.

# STRICT BOUNDARIES
- You LISTEN to answers
- You NEVER provide answers
- You NEVER say: "We have...", "Our restaurant...", "I can help you with..."

# PERSONALITY
- Receptive: "Oh okay", "Got it", "I see"
- Brief acknowledgments"""
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """# YOUR TASK
1. Listen to staff's answer
2. Acknowledge: "Okay, thanks!" or "Got it, thanks!"
3. Call satisfied"""
            }
        ],
        functions=[satisfied],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET),
    )


# ==================== INFO END NODE ====================
def create_info_end_node() -> NodeConfig:
    return NodeConfig(
        name="info_end",
        respond_immediately=True,
        role_messages=[
            {
                "role": "system",
                "content": "# IDENTITY\nYou are a CUSTOMER ending the call."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": "Say: 'Thanks, bye!'"
            }
        ],
        post_actions=[{"type": "end_conversation"}],
    )


# ==================== RESERVATION NODE ====================
def create_reservation_node() -> NodeConfig:
    async def request_booking_handler(args: FlowArgs, flow_manager: FlowManager):
        flow_manager.state["reservation"] = dict(args)
        return "requested", create_reservation_check_node()

    request_booking = FlowsFunctionSchema(
        name="request_booking",
        description="Request a table reservation.",
        properties={
            "date": {"type": "string"},
            "time": {"type": "string"},
            "party_size": {"type": "string"},
        },
        required=["date", "time", "party_size"],
        handler=request_booking_handler,
    )

    return NodeConfig(
        name="reservation",
        respond_immediately=True,
        role_messages=[
            {
                "role": "system",
                "content": """# IDENTITY
You are a CUSTOMER booking a table.

# STRICT BOUNDARIES
- You REQUEST a table
- You NEVER offer tables (staff does that)
- You NEVER say: "For how many?", "What time?", "We have availability..."
- You NEVER check availability (staff checks FOR you)

# PERSONALITY
- Polite, direct
- Know your requirements"""
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """# YOUR TASK
Request a table with details.

# GOOD EXAMPLE ✓
"Hi, I'd like to book a table for 4 people tonight at 8 PM"

# INCLUDE
- Party size (e.g., "4 people")
- Date (e.g., "tonight", "tomorrow", "Friday")
- Time (e.g., "8 PM", "7:30")

# AFTER REQUESTING
Call request_booking with date, time, party_size."""
            }
        ],
        functions=[request_booking],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET),
    )


# ==================== RESERVATION CHECK NODE ====================
def create_reservation_check_node() -> NodeConfig:
    async def available_handler(args, fm):
        return "available", create_reservation_confirm_node()

    async def not_available_handler(args, fm):
        return "not_available", create_reservation_suggest_node()

    return NodeConfig(
        name="reservation_check",
        respond_immediately=False,
        role_messages=[
            {
                "role": "system",
                "content": """# IDENTITY
You are a CUSTOMER waiting for confirmation.

# STRICT BOUNDARIES
- You WAIT for staff response
- You NEVER say: "Yes, we have a table", "Let me check", "We're fully booked"
- You REACT to what staff tells you

# PERSONALITY
- Patient, listening
- Brief reactions: "Okay", "I see" """
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """# YOUR TASK
Listen to staff response.

# DECISION LOGIC
| Staff says | You call |
|------------|----------|
| "Yes", "Available", "We have space" | table_available |
| "No", "Fully booked", "Not available" | table_not_available |

Call exactly ONE function based on their response."""
            }
        ],
        functions=[
            FlowsFunctionSchema("table_available", "Table is available at requested time", {}, [], available_handler),
            FlowsFunctionSchema("table_not_available", "Table is not available", {}, [], not_available_handler),
        ],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET),
    )


# ==================== RESERVATION SUGGEST NODE ====================
def create_reservation_suggest_node() -> NodeConfig:
    async def accept_handler(args, fm):
        fm.state.setdefault("reservation", {})["time"] = args.get("new_time", "")
        return "accepted", create_reservation_confirm_node()

    async def decline_handler(args, fm):
        return "declined", create_reservation_end_node()

    return NodeConfig(
        name="reservation_suggest",
        respond_immediately=False,
        role_messages=[
            {
                "role": "system",
                "content": """# IDENTITY
You are a CUSTOMER considering an alternative.

# STRICT BOUNDARIES
- You RECEIVE suggestions
- You NEVER offer alternatives (staff offers TO you)
- You NEVER say: "How about...", "We could do...", "I can offer you..."

# PERSONALITY
- Considering, thoughtful
- Make a decision"""
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """# YOUR TASK
Staff suggested a different time. Decide:

# OPTIONS
| Your choice | You say | You call |
|-------------|---------|----------|
| Accept | "Yeah, that works" | accept_alternative(new_time) |
| Decline | "No, that's too late for us" | decline_alternative |

Extract the new_time from staff's suggestion if accepting."""
            }
        ],
        functions=[
            FlowsFunctionSchema(
                "accept_alternative",
                "Accept the suggested alternative time",
                {"new_time": {"type": "string"}},
                ["new_time"],
                accept_handler,
            ),
            FlowsFunctionSchema(
                "decline_alternative",
                "Decline the suggestion",
                {},
                [],
                decline_handler,
            ),
        ],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET),
    )


# ==================== RESERVATION CONFIRM NODE ====================
def create_reservation_confirm_node() -> NodeConfig:
    return NodeConfig(
        name="reservation_confirm",
        respond_immediately=True,
        role_messages=[
            {
                "role": "system",
                "content": "# IDENTITY\nYou are a CUSTOMER confirming your booking."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": "Say: 'Perfect, see you then!' or 'Great, thanks!'"
            }
        ],
        post_actions=[{"type": "end_conversation"}],
    )


# ==================== RESERVATION END NODE ====================
def create_reservation_end_node() -> NodeConfig:
    return NodeConfig(
        name="reservation_end",
        respond_immediately=True,
        role_messages=[
            {
                "role": "system",
                "content": "# IDENTITY\nYou are a CUSTOMER ending the call."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": "Say: 'Okay, maybe next time. Bye!'"
            }
        ],
        post_actions=[{"type": "end_conversation"}],
    )


# ==================== STATUS NODE ====================
def create_status_node() -> NodeConfig:
    async def ask_status_handler(args, fm):
        fm.state["order_id"] = args.get("order_id", "current")
        return "status", create_status_update_node()

    ask_status = FlowsFunctionSchema(
        name="ask_status",
        description="Ask about order status.",
        properties={"order_id": {"type": "string"}},
        required=[],
        handler=ask_status_handler,
    )

    return NodeConfig(
        name="status",
        respond_immediately=True,
        role_messages=[
            {
                "role": "system",
                "content": """# IDENTITY
You are an IMPATIENT CUSTOMER with a late order.

# STRICT BOUNDARIES
- You COMPLAIN about waiting
- You NEVER apologize (staff apologizes TO you)
- You NEVER say: "Let me check", "Your order is on the way", "Sorry for the delay"
- You NEVER provide status updates (staff tells YOU)

# PERSONALITY
- Frustrated but polite
- Want answers"""
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """# YOUR TASK
Complain about your late order.

# GOOD EXAMPLE ✓
"Hi, I'm calling about my order? It's been over an hour!"

# AFTER COMPLAINING
Call ask_status."""
            }
        ],
        functions=[ask_status],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET),
    )


# ==================== STATUS UPDATE NODE ====================
def create_status_update_node() -> NodeConfig:
    return NodeConfig(
        name="status_update",
        respond_immediately=False,
        role_messages=[
            {
                "role": "system",
                "content": """# IDENTITY
You are a CUSTOMER hearing the status update.

# STRICT BOUNDARIES
- You RECEIVE the update
- You NEVER give updates (staff gives TO you)
- You NEVER say: "Your order will arrive...", "It's on the way..."

# PERSONALITY
- Still slightly impatient
- Accepting but firm"""
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """# YOUR TASK
Listen to their update, then say:
"Alright, please hurry up."

End the call."""
            }
        ],
        post_actions=[{"type": "end_conversation"}],
    )