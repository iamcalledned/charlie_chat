#!/bin/bash

# Define source and destination directories
SOURCE_DIR="/home/charlie/charlie_chat/html"
DESTINATION_DIR="/var/www/iamcalledcharlie"

# Prompt the user for the file names to copy
echo "Please enter the file names to copy, separated by spaces:"
read -a file_names

# Loop through each file name provided
for file_name in "${file_names[@]}"; do
    # Use sudo to copy the file, overwriting the destination file if it exists
    sudo cp -f "$SOURCE_DIR/$file_name" "$DESTINATION_DIR/"
done

echo "Files have been copied."
