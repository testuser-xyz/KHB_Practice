from pipecat_flows import FlowManager, NodeConfig, FlowsFunctionSchema, FlowArgs, ContextStrategy, ContextStrategyConfig

# ==============================================================================
# GREET / ROUTER NODE
# ==============================================================================

def create_greet_node() -> NodeConfig:
    
    async def place_order_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        return "Intent selected: place_order", create_order_node()

    async def ask_info_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        return "Intent selected: ask_info", create_info_node()

    async def make_reservation_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        return "Intent selected: make_reservation", create_reservation_node()

    async def check_status_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        return "Intent selected: check_status", create_status_node()

    place_order_func = FlowsFunctionSchema(
        name="place_order",
        description="Select this intent to place an order.",
        properties={}, 
        required=[], 
        handler=place_order_handler,
    )

    ask_info_func = FlowsFunctionSchema(
        name="ask_info",
        description="Select this intent to ask about menu or services.",
        properties={}, 
        required=[], 
        handler=ask_info_handler,
    )

    make_reservation_func = FlowsFunctionSchema(
        name="make_reservation",
        description="Select this intent to make a table reservation.",
        properties={}, 
        required=[], 
        handler=make_reservation_handler,
    )

    check_status_func = FlowsFunctionSchema(
        name="check_status",
        description="Select this intent to check order status.",
        properties={}, 
        required=[], 
        handler=check_status_handler,
    )
    
    return NodeConfig(
        name="greet",
        respond_immediately=False,
        role_messages=[
            {
                "role": "system",
                "content": "You are an internal decision engine. You do NOT speak. Your ONLY job is to call a function to start the scenario."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """Wait for the call to connect.
                
                IMMEDIATELY and SILENTLY call one of these functions to start the scenario:
                - place_order
                - ask_info
                - make_reservation
                - check_status
                
                Pick one randomly. Do not output text. JUST CALL THE FUNCTION."""
            }
        ],
        functions=[place_order_func, ask_info_func, make_reservation_func, check_status_func]
    )


# ==============================================================================
# ORDERING FLOW
# ==============================================================================

def create_order_node() -> NodeConfig:
    
    async def confirm_order_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        items_list = args.get("items", "")
        flow_manager.state["order_items"] = items_list
        return f"Ordered: {items_list}", create_order_confirmation_node()

    confirm_order_func = FlowsFunctionSchema(
        name="confirm_order",
        description="Submit the list of items you want to order.",
        properties={
            "items": {"type": "string", "description": "List of items to order"}
        },
        required=["items"], 
        handler=confirm_order_handler,
    )
    
    return NodeConfig(
        name="order",
        respond_immediately=True, # Bot speaks first here
        role_messages=[
            {
                "role": "system",
                "content": "You are a customer calling a restaurant. Speak naturally."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """You want to place a food order.
                
                1. Speak your order naturally (e.g., "I'd like a pepperoni pizza").
                2. IMMEDIATELY after speaking, call 'confirm_order' with the items.
                """
            }
        ],
        functions=[confirm_order_func],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET)
    )


def create_order_confirmation_node() -> NodeConfig:
    
    async def provide_details_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        address = args.get("delivery_address", "")
        payment = args.get("payment_method", "")
        flow_manager.state["delivery_address"] = address
        flow_manager.state["payment_method"] = payment
        return f"Details: {address}, {payment}", create_order_details_node()

    provide_details_func = FlowsFunctionSchema(
        name="provide_details",
        description="Submit delivery address and payment method.",
        properties={
            "delivery_address": {"type": "string", "description": "Your delivery address"},
            "payment_method": {"type": "string", "description": "Payment method (cash/card)"}
        },
        required=["delivery_address", "payment_method"],
        handler=provide_details_handler,
    )
    
    return NodeConfig(
        name="order_confirmation",
        respond_immediately=False, # FIX: Wait for user to ask for details
        role_messages=[
            {
                "role": "system",
                "content": "You are a customer calling a restaurant."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """You have just stated your order.
                
                STOP SPEAKING. Wait for the restaurant to respond (e.g., confirming price or asking for address).
                
                ONLY when they ask for details:
                1. Provide your address and payment method naturally.
                2. Call 'provide_details'.
                """
            }
        ],
        functions=[provide_details_func]
    )


def create_order_details_node() -> NodeConfig:
    return NodeConfig(
        name="order_details",
        role_messages=[{"role": "system", "content": "Customer."}],
        task_messages=[{"role": "system", "content": "Listen to the final confirmation. Say 'Thank you' and allow the call to end."}],
        functions=[],
        post_actions=[{"type": "end_conversation"}]
    )


# ==============================================================================
# INFORMATION FLOW
# ==============================================================================

def create_info_node() -> NodeConfig:
    
    async def ask_question_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        question = args.get("question", "")
        flow_manager.state["question"] = question
        return f"Asked: {question}", create_info_response_node()

    ask_question_func = FlowsFunctionSchema(
        name="ask_question",
        description="Log the question you asked.",
        properties={
            "question": {"type": "string", "description": "The question asked"}
        },
        required=["question"], 
        handler=ask_question_handler,
    )
    
    return NodeConfig(
        name="info",
        respond_immediately=True, # Bot speaks first here
        role_messages=[
            {
                "role": "system",
                "content": "You are a customer calling a restaurant. Speak naturally."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """Pick ONE question (e.g., hours, vegetarian options).
                Ask it naturally, then call 'ask_question'."""
            }
        ],
        functions=[ask_question_func],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET)
    )


def create_info_response_node() -> NodeConfig:
    return NodeConfig(
        name="info_response",
        respond_immediately=False, # FIX: Wait for answer
        role_messages=[{"role": "system", "content": "Customer."}],
        task_messages=[
            {
                "role": "system", 
                "content": """You just asked a question. STOP SPEAKING. 
                Wait for the restaurant to answer. Once answered, say 'Thank you' and end call."""
            }
        ],
        functions=[],
        post_actions=[{"type": "end_conversation"}]
    )


# ==============================================================================
# RESERVATION FLOW
# ==============================================================================

def create_reservation_node() -> NodeConfig:
    
    async def request_booking_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        date = args.get("date", "")
        time = args.get("time", "")
        party_size = args.get("party_size", "")
        
        flow_manager.state["reservation"] = {"date": date, "time": time, "party_size": party_size}
        return f"Booking req: {party_size} ppl, {date} {time}", create_reservation_check_node()

    request_booking_func = FlowsFunctionSchema(
        name="request_booking",
        description="Log the reservation request details.",
        properties={
            "date": {"type": "string"},
            "time": {"type": "string"},
            "party_size": {"type": "string"}
        },
        required=["date", "time", "party_size"], 
        handler=request_booking_handler,
    )
    
    return NodeConfig(
        name="reservation",
        respond_immediately=True, # Bot speaks first here
        role_messages=[
            {
                "role": "system",
                "content": "You are a customer calling a restaurant. Speak naturally."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """Request a table reservation naturally (e.g., "Table for 4 Friday at 7pm").
                Then call 'request_booking'."""
            }
        ],
        functions=[request_booking_func],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET)
    )


def create_reservation_check_node() -> NodeConfig:
    
    async def available_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        return "Available", create_reservation_booking_node()

    async def not_available_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        return "Not Available", create_reservation_suggest_node()

    available_func = FlowsFunctionSchema(
        name="table_available",
        description="Call if restaurant says table is available.",
        properties={}, 
        required=[], 
        handler=available_handler,
    )

    not_available_func = FlowsFunctionSchema(
        name="table_not_available",
        description="Call if restaurant says table is NOT available.",
        properties={}, 
        required=[], 
        handler=not_available_handler,
    )
    
    return NodeConfig(
        name="reservation_check",
        respond_immediately=False, # FIX: Wait for user to check schedule
        role_messages=[
            {
                "role": "system",
                "content": "You are a customer."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """You just requested a table. STOP SPEAKING.
                
                Listen to the restaurant's response.
                - If they say "Yes/Available": Call 'table_available'.
                - If they say "No/Full/Booked": Call 'table_not_available'.
                """
            }
        ],
        functions=[available_func, not_available_func]
    )


def create_reservation_booking_node() -> NodeConfig:
    
    async def confirm_booking_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        return "Confirmed", create_reservation_confirm_node()

    confirm_booking_func = FlowsFunctionSchema(
        name="confirm_booking",
        description="Confirm the booking.",
        properties={}, 
        required=[], 
        handler=confirm_booking_handler,
    )
    
    return NodeConfig(
        name="reservation_booking",
        respond_immediately=True, # Bot responds to "Available"
        role_messages=[{"role": "system", "content": "Customer."}],
        task_messages=[
            {
                "role": "system",
                "content": """The table is available.
                Say: "Perfect! Please book that for me."
                Then call 'confirm_booking'."""
            }
        ],
        functions=[confirm_booking_func],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET)
    )


def create_reservation_suggest_node() -> NodeConfig:
    
    async def accept_alternative_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        new_time = args.get("new_time", "")
        flow_manager.state["reservation"]["time"] = new_time
        return f"Accepted: {new_time}", create_reservation_confirm_node()

    async def decline_alternative_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        return "Declined", create_reservation_end_node()

    accept_alternative_func = FlowsFunctionSchema(
        name="accept_alternative",
        description="Accept alternative time.",
        properties={"new_time": {"type": "string"}},
        required=["new_time"], 
        handler=accept_alternative_handler,
    )

    decline_alternative_func = FlowsFunctionSchema(
        name="decline_alternative",
        description="Decline alternative.",
        properties={}, 
        required=[], 
        handler=decline_alternative_handler,
    )
    
    return NodeConfig(
        name="reservation_suggest",
        respond_immediately=True, # Bot responds to "Not Available"
        role_messages=[{"role": "system", "content": "Customer."}],
        task_messages=[
            {
                "role": "system",
                "content": """The restaurant suggested a new time.
                - To accept: Say "That works" and call 'accept_alternative'.
                - To decline: Say "No thanks" and call 'decline_alternative'."""
            }
        ],
        functions=[accept_alternative_func, decline_alternative_func],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET)
    )


def create_reservation_confirm_node() -> NodeConfig:
    return NodeConfig(
        name="reservation_confirm",
        role_messages=[{"role": "system", "content": "Customer."}],
        task_messages=[{"role": "system", "content": "Confirm details. Say 'Thank you' and allow the call to end."}],
        functions=[],
        post_actions=[{"type": "end_conversation"}]
    )


def create_reservation_end_node() -> NodeConfig:
    return NodeConfig(
        name="reservation_end",
        role_messages=[{"role": "system", "content": "Customer."}],
        task_messages=[{"role": "system", "content": "Politely say goodbye and allow the call to end."}],
        functions=[],
        post_actions=[{"type": "end_conversation"}]
    )


# ==============================================================================
# STATUS CHECK FLOW
# ==============================================================================

def create_status_node() -> NodeConfig:
    
    async def ask_status_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        order_id = args.get("order_id", "current")
        flow_manager.state["order_id"] = order_id
        return f"Status check for: {order_id}", create_status_update_node()

    ask_status_func = FlowsFunctionSchema(
        name="ask_status",
        description="Log status check.",
        properties={"order_id": {"type": "string"}},
        required=[], 
        handler=ask_status_handler,
    )
    
    return NodeConfig(
        name="status",
        respond_immediately=True, # Bot speaks first here
        role_messages=[
            {
                "role": "system",
                "content": "You are a customer calling a restaurant. Speak naturally."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """Ask about your order status naturally (e.g., "Where is my order?").
                Then call 'ask_status'."""
            }
        ],
        functions=[ask_status_func],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET)
    )


def create_status_update_node() -> NodeConfig:
    return NodeConfig(
        name="status_update",
        respond_immediately=False, # FIX: Wait for answer
        role_messages=[{"role": "system", "content": "Customer."}],
        task_messages=[{"role": "system", "content": "You just asked about status. STOP SPEAKING. Wait for the update."}],
        functions=[],
        post_actions=[{"type": "end_conversation"}]
    )