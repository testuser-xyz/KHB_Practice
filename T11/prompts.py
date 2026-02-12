def get_menu() -> str:
    """Returns the Cheezious menu that the bot should use for taking orders.
    Uses a cached version to avoid slow web scraping on every bot startup.
    To update the cache, run: py -m uv run menu.py
    """
    return """RESTAURANT: Cheezious (Live Data)
MENU & PRICES:
- Malai Tikka - Rs. 1,600 (Starting Price)
- Beef Pepperoni Thin Crust - Rs. 1,550 (Starting Price)
- Cheezy Sticks - Rs. 630
- Oven Baked Wings - Rs. 600 (Starting Price)
- Flaming Wings - Rs. 650 (Starting Price)
- Calzone Chunks - Rs. 1,150
- Arabic Rolls - Rs. 690
- Behari Rolls - Rs. 690
- Chicken Tikka - Rs. 690 (Starting Price)
- Chicken Fajita - Rs. 690 (Starting Price)
- Chicken Lover - Rs. 690 (Starting Price)
- Chicken Tandoori - Rs. 690 (Starting Price)
- Hot n Spicy - Rs. 690 (Starting Price)
- Vegetable Pizza - Rs. 690 (Starting Price)
- Euro - Rs. 690 (Starting Price)
- Chicken Supreme - Rs. 690 (Starting Price)
- Black Pepper Tikka - Rs. 690 (Starting Price)
- Sausage Pizza - Rs. 690 (Starting Price)
- Cheese Lover Pizza - Rs. 690 (Starting Price)
- Chicken Pepperoni - Rs. 690 (Starting Price)
- Chicken Mushroom - Rs. 690 (Starting Price)
- Cheezious Special - Rs. 1,550 (Starting Price)
- Behari Kabab - Rs. 1,550 (Starting Price)
- Chicken Extreme - Rs. 1,550 (Starting Price)
- Small Pizza Deal - Rs. 750 (Starting Price) - Any Flavor + 1 Soft Drink
- Regular Pizza Deal - Rs. 1,450 (Starting Price) - 1 Regular Pizza + 2 Regular Drinks
- Large Pizza Deal - Rs. 1,990 (Starting Price) - Any Flavor + 1 Liter Drink
- Special Roasted Roll Platter - Rs. 1,200 - 4 Pcs Behari Rolls, 6 Pcs Wings, Fries & Sauce
- Mexican Sandwich - Rs. 920
- Pizza Stacker - Rs. 920
- Euro Sandwich - Rs. 920
- Classic Roll Platter - Rs. 1,200 - 4 Pcs Behari Rolls, 4 Pcs Arabic Rolls, Fries & Sauce
- Crown Crust - Rs. 1,550 (Starting Price)
- Stuff Crust Pizza - Rs. 1,600 (Starting Price)
- Somewhat Amazing Deal 1 - Rs. 1,250 (Starting Price) - 2 Bazinga, Regular Fries, 2 Regular Drinks
- Somewhat Amazing Deal 2 - Rs. 1,750 (Starting Price) - 2 Bazinga Burger, 2 Pcs Chicken, Large Fries, 2 Regular Drink
- Somewhat Amazing Deal 3 - Rs. 1,890 (Starting Price) - 3 Bazinga Burger, Large Fries, 1 Liter Drink
- Somewhat Amazing Deal 4 - Rs. 2,150 (Starting Price) - 3 Bazinga Burger, 3 Pcs Chicken, 1 Liter Drink
- Fettuccine Alfredo Pasta - Rs. 1,050 - Pasta in white sauce with chicken chunks topped with cheese
- Crunchy Chicken Macaroni - Rs. 950 - Macaroni pasta in white sauce topped with crispy chicken and cheese
- Reggy Burger - Rs. 390 (Starting Price)
- Bazinga Burger - Rs. 560 (Starting Price)
- Bazooka - Rs. 630 (Starting Price)
- Fries - Rs. 220 (Starting Price)
- Nuggets - Rs. 450 (Starting Price)
- Chicken Piece - Rs. 300 (Starting Price)
- Mayo Dip - Rs. 80
- Water Small - Rs. 60
- Soft Drink - Rs. 100 (Starting Price)

POLICIES:
- Delivery time: 30-45 mins
- Payment: Cash or Card on delivery"""

def get_system_instruction() -> str:
    menu_data = get_menu()
    
    system_instruction = f"""
        You are Ahmad, a friendly restaurant assistant at Cheezious taking phone orders.

        IMPORTANT: Use ONLY items from the menu below with exact names and correct prices.

        {menu_data}

        STYLE
        - Warm, professional, concise (1–3 sentences)
        - Natural speech with contractions
        - Ask clarifying questions when needed

        CORE BEHAVIOR
        - Greet, ask how to help
        - Confirm items and sizes (Small/Regular/Large when “Starting Price”)
        - Suggest add‑ons (Fries/Drinks) when appropriate
        - If item not on menu, apologize and offer a closest menu alternative
        - Summarize the order and ask for payment method

        RULES
        1) Never invent items or prices
        2) Use exact menu names
        3) Stay in character as the restaurant assistant
        """
    return system_instruction
