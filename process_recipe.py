import re
from chat_bot_database import save_recipe_to_db
from config import Config
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
import spacy
import os

app = FastAPI()

# Load the spaCy model
#nlp = spacy.load("en_core_web_sm")
model_path = os.path.expanduser("~/projects/generic_chat/model")

nlp = spacy.load(model_path)
print("loaded nlp from", model_path)


def analyze_ingredient(ingredient_text):
    # Process the text with spaCy
    cleaned_ingredient_text = ingredient_text.lstrip('- ').strip()
    
    pattern = r'\(\d[^)]*\)'
    cleaned_ingredient_text = re.sub(pattern, '', cleaned_ingredient_text)
    cleaned_ingredient_text = re.sub(r'\s+', ' ', cleaned_ingredient_text)  # Collapse multiple spaces into one
    
    doc = nlp(cleaned_ingredient_text)

    # Extract relevant information (e.g., quantity, unit, ingredient)
    # This part depends on your specific needs and might require a custom model
    # For demonstration, I'm just printing the entities spaCy finds
    for ent in doc.ents:
        print(f"Entity: {ent.text}, Label: {ent.label_}")




async def process_recipe(pool, message_content, userID):
            # Handle the save recipe action
            recipe_text = message_content
            #recipe_text = recipe_text.replace("\n", " ").replace("\t", " ")
            # Regular expression for extracting title, servings, and times
            title_match = re.search(r"A recipe for: (.+?)\n", recipe_text)
            servings_match = re.search(r"Servings: (.+?)\n", recipe_text)
            prep_time_match = re.search(r"Prep time: (.+?)\n", recipe_text)
            cook_time_match = re.search(r"Cook time: (.+?)\n", recipe_text)
            total_time_match = re.search(r"Total time: (.+?)\n", recipe_text)

            # Ingredient extraction
            ingredients_match = re.search(r"Ingredients:\n(.*?)\n\nInstructions:", recipe_text, re.DOTALL)
            if ingredients_match:
                ingredients_text = ingredients_match.group(1)
                ingredients_lines = [line.strip() for line in ingredients_text.split('\n') if line.strip()]
                ingredients = []
                current_category = None
                for line in ingredients_lines:
                    if line.endswith(':'):
                        current_category = line[:-1]
                    else:
                        ingredient = {'item': line, 'category': current_category}
                        ingredients.append(ingredient)
            else:
                ingredients = []  # or handle the error appropriately

            # Instruction extraction
            instructions_section_match = re.search(r"(Instructions|Directions):\n", recipe_text)
            if instructions_section_match:
                # Find the start index of instructions
                start_index = instructions_section_match.end()
                
                # Extract text starting from 'Instructions' or 'Directions'
                following_text = recipe_text[start_index:]

                # Use regex to find all lines starting with a number
                instructions = re.findall(r"^\d+\.\s*(.+)$", following_text, re.MULTILINE)
            else:
                instructions = []  # Handle the case where instructions are not found



            # Structured recipe data
            recipe_data = {
                "title": title_match.group(1) if title_match else None,
                "servings": servings_match.group(1) if servings_match else None,
                "prep_time": prep_time_match.group(1) if prep_time_match else None,
                "cook_time": cook_time_match.group(1) if cook_time_match else None,
                "total_time": total_time_match.group(1) if total_time_match else None,
                "ingredients": ingredients,
                "instructions": instructions
            }
            for ingredient_dict in recipe_data['ingredients']:
                ingredient_text = ingredient_dict['item']
                print("ingredient text:", ingredient_text)
                analyze_ingredient(ingredient_text)
            

            
            # Initialize save_result with a default value
            save_result = 'not processed'  # You can set a default value that makes sense for your application  
            
            print("userID from process_recipe:", userID)
            print("recipe data", recipe_data)
            save_result = await save_recipe_to_db(pool, userID, recipe_data)                
            print("save result:", save_result)
            