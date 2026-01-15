"""
Node factory functions for restaurant chatbot using pipecat-flows Dynamic Flows pattern.

Each node is created by a factory function that returns a NodeConfig.
Uses FlowsFunctionSchema for transitions and function calls.
"""

from typing import Optional
from pipecat_flows import (
    FlowManager,
    NodeConfig,
    FlowResult,
    FlowsFunctionSchema,
    FlowArgs,
)


# ============================================================================
# GREET NODE - Initial entry point
# ============================================================================

def create_greet_node() -> NodeConfig:
    """
    Create the initial greeting node.
    
    This is the entry point of the conversation. The bot greets the customer
    and offers multiple paths: view menu, place order, check status, reserve table, or talk to human.
    """
    
    async def go_to_menu_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        """
        Transition to menu viewing.
        """
        return "Showing menu", create_menu_node()

    async def go_to_order_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        """
        Start the ordering process.
        """
        return "Starting order", create_order_node()

    async def go_to_status_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        """
        Check order status.

        Args:
            order_id (str): The order ID to check status for
        """
        order_id: str = args["order_id"]
        return f"Checking status for order {order_id}", create_status_node(order_id)

    async def go_to_reserve_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        """
        Start table reservation process.
        """
        return "Starting reservation", create_reserve_node()

    async def go_to_human_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        """
        Transfer to human representative.
        """
        return "Transferring to human", create_human_node()

    go_to_menu_func = FlowsFunctionSchema(
        name="go_to_menu",
        description="Transition to showing the restaurant menu.",
        required=[],
        handler=go_to_menu_handler,
        properties={},
    )

    go_to_order_func = FlowsFunctionSchema(
        name="go_to_order",
        description="Begin the ordering process.",
        required=[],
        handler=go_to_order_handler,
        properties={},
    )

    go_to_status_func = FlowsFunctionSchema(
        name="go_to_status",
        description="Check the status of a specific order by ID.",
        required=["order_id"],
        handler=go_to_status_handler,
        properties={"order_id": {"type": "string"}},
    )

    go_to_reserve_func = FlowsFunctionSchema(
        name="go_to_reserve",
        description="Start the table reservation process.",
        required=[],
        handler=go_to_reserve_handler,
        properties={},
    )

    go_to_human_func = FlowsFunctionSchema(
        name="go_to_human",
        description="Transfer the conversation to a human representative.",
        required=[],
        handler=go_to_human_handler,
        properties={},
    )

    # Backwards-compatible aliases the LLM might attempt to call
    view_menu_func = FlowsFunctionSchema(
        name="view_menu",
        description="Alias for go_to_menu",
        required=[],
        handler=go_to_menu_handler,
        properties={},
    )

    show_menu_func = FlowsFunctionSchema(
        name="show_menu",
        description="Alias for go_to_menu",
        required=[],
        handler=go_to_menu_handler,
        properties={},
    )
    
    return NodeConfig(
        name="greet",
        role_messages=[
            {
                "role": "system",
                "content": "You are a friendly restaurant assistant. Be warm, professional, and helpful. Keep responses concise since this is a voice conversation."
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": """Greet the customer warmly and ask how you can help them today. 
                
                Let them know you can help with:
                - Viewing the menu
                - Placing an order
                - Checking order status
                - Reserving a table
                - Connecting them with a human representative
                
                Once you understand their request, use the appropriate function to proceed."""
            }
        ],
        functions=[
            go_to_menu_func,
            view_menu_func,
            show_menu_func,
            go_to_order_func,
            go_to_status_func,
            go_to_reserve_func,
            go_to_human_func,
        ]
    )


# ============================================================================
# MENU NODE - Static response, ends chat
# ============================================================================

def create_menu_node() -> NodeConfig:
    """
    Show menu to customer and end conversation.
    
    This is a terminal node - it displays the menu and ends the chat.
    """
    
    return NodeConfig(
        name="menu",
        task_messages=[
            {
                "role": "system",
                "content": """Share the restaurant menu with the customer:

                Pizzas:
                - Margherita: $12 (Small), $18 (Large)
                - Pepperoni: $14 (Small), $20 (Large)
                - Vegetarian: $13 (Small), $19 (Large)
                
                Burgers:
                - Classic Burger: $8
                - Chicken Burger: $9
                - Veggie Burger: $8
                
                Sides:
                - Fries: $4
                - Salad: $5
                - Garlic Bread: $4
                
                After sharing the menu, thank them and end the conversation."""
            }
        ],
        functions=[],
        post_actions=[
            {
                "type": "end_conversation"
            }
        ]
    )


# ============================================================================
# STATUS NODE - Static response with order ID, ends chat
# ============================================================================

def create_status_node(order_id: str) -> NodeConfig:
    """
    Check order status and end conversation.
    
    Args:
        order_id: The order ID to check status for
        
    This is a terminal node - it provides status information and ends the chat.
    """
    
    return NodeConfig(
        name="status",
        task_messages=[
            {
                "role": "system",
                "content": f"""The customer wants to check the status of order {order_id}.
                
                Tell them: "Your order {order_id} is being prepared and will be ready in 15-20 minutes."
                
                Thank them and end the conversation."""
            }
        ],
        functions=[],
        post_actions=[
            {
                "type": "end_conversation"
            }
        ]
    )


# ============================================================================
# HUMAN NODE - Handoff message, ends chat
# ============================================================================

def create_human_node() -> NodeConfig:
    """
    Transfer to human representative and end bot conversation.
    
    This is a terminal node - it hands off to a human.
    """
    
    return NodeConfig(
        name="human",
        task_messages=[
            {
                "role": "system",
                "content": """Tell the customer: "I'm connecting you with one of our team members who will assist you shortly. Please hold."
                
                Then end the conversation to allow human handoff."""
            }
        ],
        functions=[],
        post_actions=[
            {
                "type": "end_conversation"
            }
        ]
    )


# ============================================================================
# ORDER NODE - Initializes cart, transitions to Items
# ============================================================================

def create_order_node() -> NodeConfig:
    """
    Initialize the ordering process.
    
    Initializes an empty cart in flow_manager.state and transitions to the items node
    where the customer can add items to their order.
    """
    
    async def start_adding_items_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        """
        Initialize empty cart and move to items selection.
        """
        # Initialize cart in state
        flow_manager.state["cart"] = []
        return "Cart initialized", create_items_node()

    start_adding_items_func = FlowsFunctionSchema(
        name="start_adding_items",
        description="Initialize an empty cart and transition to the items node.",
        required=[],
        handler=start_adding_items_handler,
        properties={},
    )
    
    return NodeConfig(
        name="order",
        task_messages=[
            {
                "role": "system",
                "content": """Tell the customer you're ready to take their order.
                
                Say something like: "Great! I'm ready to take your order. What would you like to have?"
                
                Then use the start_adding_items function to begin the ordering process."""
            }
        ],
        functions=[start_adding_items_func]
    )


# ============================================================================
# ITEMS NODE - The ordering loop
# ============================================================================

def create_items_node() -> NodeConfig:
    """
    The main ordering loop where customers add items.
    
    Customers can:
    - Add items to cart (loops back to this node)
    - Finish ordering (goes to confirm node)
    """
    
    async def add_item_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        """
        Add an item to the cart and loop back to Items node.

        Args:
            item_name (str): Name of the item to add
            quantity (int): Quantity of the item (default: 1)
            size (str): Size of the item if applicable (e.g., "Small", "Large")
        """
        # Get current cart
        cart = flow_manager.state.get("cart", [])

        # Extract args with defaults
        item_name: str = args["item_name"]
        quantity: int = int(args.get("quantity", 1))
        size: Optional[str] = args.get("size")

        # Add item to cart
        item = {
            "name": item_name,
            "quantity": quantity,
            "size": size,
        }
        cart.append(item)
        flow_manager.state["cart"] = cart

        # Confirm addition and loop back to this node
        size_text = f" {size}" if size else ""
        result = f"Added {quantity}{size_text} {item_name} to cart"
        return result, create_items_node()

    async def finish_ordering_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        """
        Complete the ordering process and move to confirmation.
        """
        return "Finishing order", create_confirm_order_node()

    add_item_func = FlowsFunctionSchema(
        name="add_item",
        description="Add an item to the cart with optional quantity and size.",
        required=["item_name"],
        handler=add_item_handler,
        properties={
            "item_name": {"type": "string"},
            "quantity": {"type": "integer"},
            "size": {"type": "string"},
        },
    )

    # Aliases often generated by LLMs or by templates
    add_items_func = FlowsFunctionSchema(
        name="add_items",
        description="Alias for add_item",
        required=["item_name"],
        handler=add_item_handler,
        properties={
            "item_name": {"type": "string"},
            "quantity": {"type": "integer"},
            "size": {"type": "string"},
        },
    )

    finish_ordering_func = FlowsFunctionSchema(
        name="finish_ordering",
        description="Finish adding items and proceed to order confirmation.",
        required=[],
        handler=finish_ordering_handler,
        properties={},
    )

    # Checkout / finish aliases
    go_to_checkout_func = FlowsFunctionSchema(
        name="go_to_checkout",
        description="Alias to finish ordering and go to checkout/confirmation.",
        required=[],
        handler=finish_ordering_handler,
        properties={},
    )

    finish_order_func = FlowsFunctionSchema(
        name="finish_order",
        description="Alias to finish ordering",
        required=[],
        handler=finish_ordering_handler,
        properties={},
    )
    
    return NodeConfig(
        name="items",
        task_messages=[
            {
                "role": "system",
                "content": """Help the customer add items to their order.
                
                For each item they mention:
                - Confirm the item name
                - Ask about size if it's a pizza (Small/Large)
                - Ask about quantity if not specified
                - Use the add_item function to add it to the cart
                - Acknowledge the addition: "Got it! Added [item] to your order."
                
                After adding items, ask if they want anything else.
                
                When they're done ordering, use the finish_ordering function to proceed to confirmation."""
            }
        ],
        functions=[add_item_func, add_items_func, finish_ordering_func, go_to_checkout_func, finish_order_func]
    )


# ============================================================================
# CONFIRM ORDER NODE - Reads state, summarizes order, ends chat
# ============================================================================

def create_confirm_order_node() -> NodeConfig:
    """
    Confirm the order with the customer.
    
    Reads cart from flow_manager.state, summarizes the order, and ends the conversation.
    This is a terminal node.
    """
    
    return NodeConfig(
        name="confirm_order",
        task_messages=[
            {
                "role": "system",
                "content": """Review the customer's order from the cart and confirm it with them.
                
                Say something like:
                "Perfect! Let me confirm your order:
                [List each item with quantity and size]
                
                Your order will be ready in 15-20 minutes. Thank you for your order!"
                
                Then end the conversation."""
            }
        ],
        functions=[],
        post_actions=[
            {
                "type": "end_conversation"
            }
        ]
    )


# ============================================================================
# RESERVE NODE - Asks for details, includes check_availability
# ============================================================================

def create_reserve_node() -> NodeConfig:
    """
    Collect reservation details and check availability.
    
    Asks for date, time, and party size, then checks availability.
    """
    
    async def check_availability_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        """
        Check table availability for the requested reservation.

        Args:
            date (str): Requested date for reservation
            time (str): Requested time for reservation
            party_size (int): Number of people in the party
        """
        date: str = args["date"]
        time: str = args["time"]
        party_size: int = int(args["party_size"])

        # Store reservation details in state
        flow_manager.state["reservation"] = {
            "date": date,
            "time": time,
            "party_size": party_size,
        }

        # Mock availability check: if time is "7pm", suggest different time
        normalized = time.strip().lower().replace(" ", "")
        if normalized in {"7pm", "7:00pm", "19:00"}:
            return f"No availability at {time}", create_suggest_time_node()
        else:
            return f"Available at {time}", create_confirm_table_node()

    check_availability_func = FlowsFunctionSchema(
        name="check_availability",
        description="Check table availability for the provided date, time, and party size.",
        required=["date", "time", "party_size"],
        handler=check_availability_handler,
        properties={
            "date": {"type": "string"},
            "time": {"type": "string"},
            "party_size": {"type": "integer"},
        },
    )
    
    return NodeConfig(
        name="reserve",
        task_messages=[
            {
                "role": "system",
                "content": """Help the customer reserve a table.
                
                Ask them for:
                1. What date they'd like to reserve (e.g., "January 15th")
                2. What time they prefer (e.g., "6pm", "7:30pm")
                3. How many people will be dining
                
                Once you have all three pieces of information, use the check_availability function to check if a table is available."""
            }
        ],
        functions=[check_availability_func]
    )


# ============================================================================
# CONFIRM TABLE NODE - Success message, ends chat
# ============================================================================

def create_confirm_table_node() -> NodeConfig:
    """
    Confirm successful table reservation.
    
    This is a terminal node - confirms the reservation and ends the conversation.
    """
    
    return NodeConfig(
        name="confirm_table",
        task_messages=[
            {
                "role": "system",
                "content": """Great news! The table is available.
                
                Confirm the reservation details from the state (date, time, party size).
                
                Say something like: "Perfect! I've reserved a table for [party_size] people on [date] at [time]. We look forward to seeing you!"
                
                Then end the conversation."""
            }
        ],
        functions=[],
        post_actions=[
            {
                "type": "end_conversation"
            }
        ]
    )


# ============================================================================
# SUGGEST TIME NODE - Failure message, loops back to availability check
# ============================================================================

def create_suggest_time_node() -> NodeConfig:
    """
    Suggest alternative time when requested time is unavailable.
    
    Suggests a different time and loops back to the reserve node for another attempt.
    """
    
    async def try_different_time_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[str, NodeConfig]:
        """
        Return to reservation node to try a different time.
        """
        return "Trying different time", create_reserve_node()

    try_different_time_func = FlowsFunctionSchema(
        name="try_different_time",
        description="Loop back to the reservation details to try another time.",
        required=[],
        handler=try_different_time_handler,
        properties={},
    )
    
    return NodeConfig(
        name="suggest_time",
        task_messages=[
            {
                "role": "system",
                "content": """Unfortunately, the requested time is not available.
                
                Apologize and suggest alternative times: "I'm sorry, but we're fully booked at that time. We have availability at 6pm or 8pm. Would either of those work for you?"
                
                Use the try_different_time function to go back and check availability for a new time."""
            }
        ],
        functions=[try_different_time_func]
    )
