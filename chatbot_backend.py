import pymongo
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import re

# Load GPT-2 or a similar model (replace with your model if needed)
tokenizer = AutoTokenizer.from_pretrained("gpt2")
model = AutoModelForCausalLM.from_pretrained("gpt2").to("cuda" if torch.cuda.is_available() else "cpu")

# Set the padding token to eos_token (End of Sequence token) to avoid padding errors
tokenizer.pad_token = tokenizer.eos_token

# Connect to MongoDB
client = pymongo.MongoClient("mongodb+srv://tacobell2:utd@cluster0.u91bm.mongodb.net/")
db = client["taco_bell_menu"]
menu_items = db["menu_items"]

# Retrieve all menu items
menu_items = list(menu_items.find({}))

# Define modification patterns
modification_patterns = [
    (r"\b(?:no|without)\b\s*(\w+)", "remove"),  # e.g., "no pickles" or "without pickles" 
    (r"\b(?:extra|additional|more)\b\s*(\w+)", "add"),  # e.g., "extra cheese"
    (r"\b(?:substitute|swap|replace)\b\s*(\w+)\s*with\s*(\w+)", "substitute"),  # e.g., "substitute lettuce with onions"
]

# A dictionary to map written numbers to their numeric values
word_to_number = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20
}

# Split input into items (e.g. "2 tacos and 2 burritos" -> ["2 tacos", "2 burritos"])
def split_items(user_input):
    # This regex splits based on common separators such as 'and' or commas, while also considering numbers.
    return re.split(r'(?<=\d)\s*(?:and|,)\s*', user_input.lower())

# Detect item, quantity, and modifications from a chunk of the input (e.g., "2 tacos with no lettuce")
def detect_item_and_modifications(item_text):
    quantity = detect_quantity(item_text)
    item = detect_item(item_text)
    modifications = detect_modifications(item_text, item) if item else []
    return item, quantity, modifications

# Detect the quantity (e.g., "2" in "2 tacos" or "one" in "one taco")
def detect_quantity(item_text):
    # First, try to detect the quantity as a written number (e.g., "one", "two")
    for word, num in word_to_number.items():
        if word in item_text:
            return num
    
    # If no written number is found, fallback to detecting numeric digits
    quantity_match = re.search(r'(\d+)\s*', item_text)
    if quantity_match:
        return int(quantity_match.group(1))
    
    return 1  # Default to 1 if no quantity is mentioned

# Detect the item in the order (e.g., "Burger", "Pizza")
def detect_item(input_text):
    
    for item in menu_items:
        if item["name"].lower() in input_text:
            return item
    return None

# Detect modifications (like "no lettuce", "extra cheese", etc.)
def detect_modifications(input_text, item):
    
    modifications = []
    for pattern, action in modification_patterns:
        matches = re.findall(pattern, input_text, flags=re.IGNORECASE)
        for match in matches:
            if action == "remove":
                if match.lower() in item["ingredients"]:
                    modifications.append(f"no {match}")
                    # item["ingredients"].remove(match.lower())
            elif action == "add":
                if match.lower() not in item["ingredients"]:
                    modifications.append(f"add {match}")
                    # item["ingredients"].append(match.lower())
            elif action == "substitute":
                parts = match.split(" with ")
                if len(parts) == 2:
                    old, new = parts
                    if old.lower() in item["ingredients"]:
                        modifications.append(f"substitute {old} with {new}")
                        # item["ingredients"].remove(old.lower())
                        # item["ingredients"].append(new.lower())
    return modifications

# Apply modifications to an item and return a summary of the changes
def apply_modifications(modifications):
    if not modifications:
        return "No modifications."
    return ", ".join(modifications)

def get_price(user_input):
    for item in menu_items:
        if item['name'].lower() in user_input.lower():
            return f"The price of {item['name']} is ${item['price']}."
    return "I couldn't find that item in the menu."

def get_description(user_input):
    for item in menu_items:
        if item['name'].lower() in user_input.lower():
            return f"{item['description']}"
    return ""

def show_tacos():
    tacos = "\n\n".join([f"{item['name']} - ${item['price']}" for item in menu_items if "taco" in item["tags"]])
    return f"We’ve got a variety of delicious tacos to choose from. Here are some of our options:\n\n{tacos}"

def show_burritos():
    burritos = "\n\n".join([f"{item['name']} - ${item['price']}" for item in menu_items if "taco" in item["tags"]])
    return f"Here’s a list of our delicious burritos at Taco Bell:\n\n{burritos}"

def show_nachos():
    nachos = "\n\n".join([f"{item['name']} - ${item['price']}" for item in menu_items if "nachos" in item["tags"]])
    return f"Great question! We have several delicious nacho options for you:\n\n{nachos}"

def show_sides():
    sides = "\n\n".join([f"{item['name']} - ${item['price']}" for item in menu_items if "side" in item["tags"]])
    return f"Here are the sides we offer at Taco Bell:\n\n{sides}"

def show_drinks():
    drinks = "\n\n".join([f"{item['name']} - ${item['price']}" for item in menu_items if "drink" in item["tags"]])
    return f"At Taco Bell, we offer a variety of refreshing drinks to complement your meal. Here's what we have:\n\n{drinks}"

def show_sauces():
    sauces = "\n\n".join([f"{item['name']} - ${item['price']}" for item in menu_items if "sauce" in item["tags"]])
    return f"At Taco Bell, we have a variety of delicious sauces to choose from! Here’s a list of what we offer:\n\n{sauces}"

def show_dairy():
    dairy = "\n\n".join([f"{item['name']} - ${item['price']}" for item in menu_items if "dairy" in item["tags"]])
    return f"Many of our menu items contain dairy, including cheese, sour cream, and sauces. Some of the items that typically contain dairy include:\n\n{dairy}"

def show_gluten_free():
    gluten_free = "\n\n".join([f"{item['name']} - ${item['price']}" for item in menu_items if "gluten" not in item["tags"]])
    return f"At Taco Bell, we offer several gluten-free options, though please keep in mind that cross-contamination is always possible due to shared kitchen equipment. Here are some of our gluten-free choices:\n\n{gluten_free}"

def show_menu():
    menu_str = "\n\n".join([f"{item['name']} - ${item['price']} : {item['description']}" for item in menu_items])
    return f"Here's what's on our Taco Bell menu:\n\n{menu_str}"

# Function to generate conversational responses using GPT-2 or another model
def generate_conversational_response(context):
    system_prompt = (
        "You are a chatbot for a Taco Bell restaurant. Your job is to assist customers in answering questions about the menu and placing their orders. "
        "Only respond to questions or commands related to ordering food. Do not generate any other kind of response. "
    )
    
    # Combine the system prompt with the current context
    full_prompt = f"{system_prompt}\n\n{context}"
    
    inputs = tokenizer(full_prompt, return_tensors="pt", padding=True, truncation=True).to(model.device)
    outputs = model.generate(
        inputs["input_ids"], 
        attention_mask=inputs["attention_mask"],  
        max_length=150, 
        pad_token_id=tokenizer.eos_token_id,  
        do_sample=True
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response.strip()