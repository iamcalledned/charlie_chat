# Function to validate and correct entities in the file
def validate_and_correct_entities(file_lines):
    corrected_lines = []

    for line in file_lines:
        # Evaluating each line as a dictionary
        try:
            line_data = eval(line.strip())
        except (SyntaxError, NameError):
            # Skip lines that cannot be evaluated
            continue

        text = line_data.get("text", "")
        entities = line_data.get("entities", [])

        # Initialize corrected entities list
        corrected_entities = []

        # Extract and validate entities
        for start, end, label in entities:
            # Ensure that the start and end indices are within bounds
            if 0 <= start < end <= len(text):
                entity_text = text[start:end]

                # Correcting entity labels based on the content
                if label == 'UNIT' and not entity_text.isalpha():
                    # If the 'UNIT' label does not contain only alphabetic characters, consider it as 'INGREDIENT'
                    corrected_entities.append((start, end, 'INGREDIENT'))
                else:
                    corrected_entities.append((start, end, label))

        corrected_line = {"text": text, "entities": corrected_entities}
        corrected_lines.append(corrected_line)

    return corrected_lines

# Validate and correct the entities
corrected_data = validate_and_correct_entities(file_contents)

# Displaying the first 10 corrected entries for review
corrected_data[:10]

