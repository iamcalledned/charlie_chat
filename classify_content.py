import re

async def classify_content(message_content):
    # Define patterns that are commonly found in recipes
    title_pattern = re.compile(r'\b(recipe for|servings|prep time|cook time|total time)\b', re.IGNORECASE)
    ingredients_pattern = re.compile(r'\b(ingredients|cups?|tablespoons?|teaspoons?|ounces?|pounds?|grams?|kilograms?)\b', re.IGNORECASE)
    instructions_pattern = re.compile(r'\b(instructions|steps|method|directions)\b', re.IGNORECASE)
    step_pattern = re.compile(r'\b(step \d+|\d+\.)', re.IGNORECASE)

    # Check for patterns in the text
    has_title = bool(title_pattern.search(message_content))
    has_ingredients = bool(ingredients_pattern.search(message_content))
    has_instructions = bool(instructions_pattern.search(message_content))
    has_steps = bool(step_pattern.search(message_content))

    # Determine if the text is likely a recipe and return the corresponding label
    if has_title and has_ingredients and has_instructions and has_steps:
        return "recipe"
    else:
        return "other"
