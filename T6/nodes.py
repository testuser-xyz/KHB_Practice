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
                "content": "You are an internal router. You do not speak. Your only job is to pick the correct function to start the conversation."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": "Wait for the user to say hello. Then IMMEDIATELY call one of the functions (place_order, ask_info, make_reservation, check_status) to begin the scenario."
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
        description="Submits the order details to the system.",
        properties={
            "items": {"type": "string", "description": "The list of food items ordered"}
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
                "content": "You are a customer calling a restaurant. You are hungry and direct."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": "Order a meal naturally (e.g., 'I would like a large pepperoni pizza'). call the 'confirm_order' function with the items you mentioned."
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
        description="Submits delivery and payment details.",
        properties={
            "delivery_address": {"type": "string", "description": "The delivery address"},
            "payment_method": {"type": "string", "description": "Payment method (e.g. cash, card)"}
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
                "content": "You are the CUSTOMER."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """You just placed your order. Wait for the restaurant to respond.
                
                If they ask for your address or payment method, provide it naturally and call 'provide_details'.
                
                Do not volunteer information until asked."""
            }
        ],
        functions=[provide_details_func]
    )


def create_order_details_node() -> NodeConfig:
    return NodeConfig(
        name="order_details",
        role_messages=[{"role": "system", "content": "You are the CUSTOMER."}],
        task_messages=[{"role": "system", "content": "You have finished giving your details. Say 'Thank you' and hang up."}],
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
        description="Logs the specific question asked.",
        properties={
            "question": {"type": "string", "description": "The question content"}
        },
        required=["question"], 
        handler=ask_question_handler,
    )
    
    return NodeConfig(
        name="info",
        respond_immediately=True,
        role_messages=[
            {
                "role": "system",
                "content": "You are a customer calling a restaurant."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": "Ask one specific question about the restaurant (e.g., 'Do you have vegan options?'). Call 'ask_question' with your query."
            }
        ],
        functions=[ask_question_func],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET)
    )


def create_info_response_node() -> NodeConfig:
    return NodeConfig(
        name="info_response",
        respond_immediately=False,
        role_messages=[{"role": "system", "content": "You are the CUSTOMER."}],
        task_messages=[{"role": "system", "content": "Listen to the answer. Say 'Thanks, that helps' and hang up."}],
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
        description="Logs the reservation request.",
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
        respond_immediately=True,
        role_messages=[
            {
                "role": "system",
                "content": "You are a customer calling a restaurant."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": "Request a table reservation naturally (e.g., 'I need a table for 2 at 8pm'). Call 'request_booking' with the details."
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
        description="Call this if the restaurant confirms the table is available.",
        properties={}, 
        required=[], 
        handler=available_handler,
    )

    not_available_func = FlowsFunctionSchema(
        name="table_not_available",
        description="Call this if the restaurant says the table is NOT available.",
        properties={}, 
        required=[], 
        handler=not_available_handler,
    )
    
    return NodeConfig(
        name="reservation_check",
        respond_immediately=False,
        role_messages=[
            {
                "role": "system",
                "content": "You are the CUSTOMER."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """Listen to the response.
                
                - If they say 'Yes' or 'Available': Call 'table_available'.
                - If they say 'No' or 'Full': Call 'table_not_available'.
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
        description="Finalizes the booking.",
        properties={}, 
        required=[], 
        handler=confirm_booking_handler,
    )
    
    return NodeConfig(
        name="reservation_booking",
        respond_immediately=True,
        role_messages=[{"role": "system", "content": "You are the CUSTOMER."}],
        task_messages=[
            {
                "role": "system",
                "content": "The table is available. Say 'Great, please book it.' and call 'confirm_booking'."
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
        description="Accepts the new time proposed.",
        properties={"new_time": {"type": "string"}},
        required=["new_time"], 
        handler=accept_alternative_handler,
    )

    decline_alternative_func = FlowsFunctionSchema(
        name="decline_alternative",
        description="Declines the offer.",
        properties={}, 
        required=[], 
        handler=decline_alternative_handler,
    )
    
    return NodeConfig(
        name="reservation_suggest",
        respond_immediately=True,
        role_messages=[{"role": "system", "content": "You are the CUSTOMER."}],
        task_messages=[
            {
                "role": "system",
                "content": """The restaurant offered a different time.
                - To accept: Say 'That works' and call 'accept_alternative'.
                - To decline: Say 'No thanks' and call 'decline_alternative'."""
            }
        ],
        functions=[accept_alternative_func, decline_alternative_func],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET)
    )


def create_reservation_confirm_node() -> NodeConfig:
    return NodeConfig(
        name="reservation_confirm",
        role_messages=[{"role": "system", "content": "You are the CUSTOMER."}],
        task_messages=[{"role": "system", "content": "Say 'Thank you, see you then' and hang up."}],
        functions=[],
        post_actions=[{"type": "end_conversation"}]
    )


def create_reservation_end_node() -> NodeConfig:
    return NodeConfig(
        name="reservation_end",
        role_messages=[{"role": "system", "content": "You are the CUSTOMER."}],
        task_messages=[{"role": "system", "content": "Say 'Okay, maybe next time, bye' and hang up."}],
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
        description="Logs the status check.",
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
                "content": "You are a customer calling a restaurant."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": "Ask 'Where is my order?'. Call 'ask_status'."
            }
        ],
        functions=[ask_status_func],
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET)
    )


def create_status_update_node() -> NodeConfig:
    return NodeConfig(
        name="status_update",
        role_messages=[{"role": "system", "content": "You are the CUSTOMER."}],
        task_messages=[{"role": "system", "content": "Listen to the update. Say 'Okay thanks' and hang up."}],
        functions=[],
        post_actions=[{"type": "end_conversation"}]
    )