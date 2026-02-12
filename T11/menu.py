# /// script
# dependencies = [
#   "selenium",
#   "webdriver-manager",
# ]
# ///

import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_live_menu():
    print("⏳ Launching browser to fetch live menu (this takes ~10s)...")
    menu_text = "RESTAURANT: Cheezious (Live Data)\nMENU & PRICES:\n"

    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get("https://cheezious.com/menu")
        time.sleep(10) # Wait for dynamic content to load

        # Strategy: Find product cards by looking for clickable elements or specific structure
        # Try multiple selectors to find product containers
        product_cards = []
        
        # Try finding by common card container patterns
        try:
            # Look for elements that contain both h1 and price
            all_divs = driver.find_elements(By.TAG_NAME, "div")
            for div in all_divs:
                try:
                    # Check if div contains an h1 (product name)
                    h1_elements = div.find_elements(By.TAG_NAME, "h1")
                    if len(h1_elements) == 1:  # Exactly one h1 means likely a product card
                        div_text = div.text
                        # Should have product name and price, but not be too large
                        if 'Rs.' in div_text and 30 < len(div_text) < 400:
                            product_cards.append(div)
                except:
                    continue
        except:
            pass
        
        seen_items = set()
        count = 0

        for card in product_cards:
            try:
                # Get product name from h1 - try multiple ways to get full untruncated text
                product_name = None
                try:
                    h1 = card.find_element(By.TAG_NAME, "h1")
                    product_name = h1.text.strip()
                    
                    # If truncated (has ...), try to find full name from parent or siblings
                    if '...' in product_name:
                        # Try to find an img element with alt text (often has full product name)
                        try:
                            img = card.find_element(By.TAG_NAME, "img")
                            alt_text = img.get_attribute("alt")
                            if alt_text and len(alt_text) > 5 and alt_text != "img":
                                product_name = alt_text
                        except:
                            pass
                        
                        # If still truncated, try finding a link with title or full text
                        if '...' in product_name:
                            try:
                                links = card.find_elements(By.TAG_NAME, "a")
                                for link in links:
                                    link_title = link.get_attribute("title")
                                    if link_title and len(link_title) > len(product_name):
                                        product_name = link_title
                                        break
                            except:
                                pass
                except:
                    # Fallback to first line of card text
                    card_text = card.text.strip()
                    lines = [line.strip() for line in card_text.split('\n') if line.strip()]
                    if len(lines) >= 1:
                        product_name = lines[0]
                
                # Skip if no name found or name is too short or generic
                if not product_name or len(product_name) < 3 or product_name in ['Starting Price', 'ADD TO CART']:
                    continue
                
                # Get card text for price extraction
                card_text = card.text.strip()
                lines = [line.strip() for line in card_text.split('\n') if line.strip()]
                
                if len(lines) < 2:
                    continue
                
                # Find price and check for "Starting Price"
                price = None
                has_starting_price = False
                description = None
                
                for line in lines[1:]:
                    if 'Rs.' in line:
                        price_match = re.search(r'Rs\.\s*[\d,]+', line)
                        if price_match:
                            price = price_match.group(0)
                            has_starting_price = 'Starting Price' in card_text
                            break
                    # Capture description (text between name and price, excluding buttons)
                    elif description is None and line not in ['Starting Price', 'ADD TO CART', '+'] and len(line) > 10:
                        description = line
                
                if price and product_name:
                    # Format the item
                    price_text = f"{price} (Starting Price)" if has_starting_price else price
                    
                    # Add description if available and product name is truncated or it's a deal
                    if description and ('...' in product_name or 'Deal' in product_name or 'Amazing' in product_name):
                        item_line = f"{product_name} - {price_text} - {description}"
                    else:
                        item_line = f"{product_name} - {price_text}"
                    
                    # Avoid duplicates
                    if item_line not in seen_items:
                        menu_text += f"- {item_line}\n"
                        seen_items.add(item_line)
                        count += 1
                    
            except Exception:
                continue

        driver.quit()
        
        if count == 0:
            print("⚠️ No items scraped. Structure might have changed.")
        else:
            print(f"✅ Successfully scraped {count} items.")

        # Policies
        menu_text += "\nPOLICIES:\n- Delivery time: 30-45 mins\n- Payment: Cash or Card on delivery"
        return menu_text

    except Exception as e:
        print(f"❌ Fetch failed: {e}")
        return "BACKUP MENU DATA..."

if __name__ == "__main__":
    print(get_live_menu())
