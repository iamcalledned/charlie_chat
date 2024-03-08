import mysql.connector

# Assuming you have a config.py file with a class Config containing the database configurations
from config import Config

# Database configuration
DB_CONFIG = {
    "host": Config.DB_HOST,
    "port": Config.DB_PORT,
    "user": Config.DB_USER,
    "password": Config.DB_PASSWORD,
    "database": Config.DB_NAME,
}

def fetch_all_recipes(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT title FROM recipes")
    all_recipes = cursor.fetchall()
    cursor.close()
    return [recipe[0] for recipe in all_recipes]  # Extracting recipe titles from the tuples

def ask_user_for_recipe(all_recipes):
    print("Available Recipes:")
    for recipe in all_recipes:
        print(f" - {recipe}")
    selected_title = input("Which recipe would you like to see? ")
    return selected_title

def fetch_recipe_details(connection, title):
    cursor = connection.cursor(dictionary=True)

    # Fetch recipe main details
    cursor.execute("SELECT recipe_id, title, servings, prep_time, cook_time, total_time FROM recipes WHERE title = %s", (title,))
    recipe_details = cursor.fetchone()

    if recipe_details is None:
        cursor.close()
        return None  # Recipe not found

    recipe_id = recipe_details['recipe_id']

    # Fetch ingredients
    cursor.execute("SELECT item, category FROM ingredients WHERE recipe_id = %s", (recipe_id,))
    ingredients = cursor.fetchall()

    # Fetch instructions
    cursor.execute("SELECT step_number, description FROM instructions WHERE recipe_id = %s ORDER BY step_number", (recipe_id,))
    instructions = cursor.fetchall()

    cursor.close()

    # Combine data into a structured format
    recipe_data = {
        "title": recipe_details['title'],
        "servings": recipe_details['servings'],
        "prep_time": recipe_details['prep_time'],
        "cook_time": recipe_details['cook_time'],
        "total_time": recipe_details['total_time'],
        "ingredients": ingredients,
        "instructions": instructions
    }

    return recipe_data

def format_recipe(recipe):
    if not recipe:
        return "Recipe not found."

    # Format the title and basic details
    formatted_recipe = f"Recipe Title: {recipe['title']}\n"
    formatted_recipe += f"Servings: {recipe['servings']}\n"
    formatted_recipe += f"Preparation Time: {recipe['prep_time']}\n"
    formatted_recipe += f"Cooking Time: {recipe['cook_time']}\n"
    formatted_recipe += f"Total Time: {recipe['total_time']}\n"

    # Format ingredients
    formatted_recipe += "\nIngredients:\n"
    for ingredient in recipe['ingredients']:
        formatted_recipe += f" - {ingredient['item']}"
        if ingredient['category']:
            formatted_recipe += f" (Category: {ingredient['category']})"
        formatted_recipe += "\n"

    # Format instructions
    formatted_recipe += "\nInstructions:\n"
    for instruction in recipe['instructions']:
        formatted_recipe += f" {instruction['step_number']}. {instruction['description']}\n"

    return formatted_recipe

# Usage
connection = mysql.connector.connect(**DB_CONFIG)

# Fetch and list all recipes
all_recipes = fetch_all_recipes(connection)
selected_recipe_title = ask_user_for_recipe(all_recipes)

# Fetch and print the details of the selected recipe
recipe = fetch_recipe_details(connection, selected_recipe_title)
if recipe:
    formatted_output = format_recipe(recipe)
    print(formatted_output)
else:
    print("Recipe not found.")

# Close the database connection
connection.close()
