
import os

file_path = 'c:/Users/purib/Downloads/antigravity/APIFy/tms captch new/main.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []

# Keep lines 0-124 (up to empty line before '3. Perform Login')
# Line 125 (index 124) is the comment line.
# We want to insert valid 'try:' before it.
new_lines.extend(lines[:125])

# Insert 'try:' at level 3 (12 spaces)
new_lines.append('            try:\n')

# Append the rest
new_lines.extend(lines[125:])

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Successfully inserted try block.")
