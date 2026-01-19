
from bs4 import BeautifulSoup
import os

file_path = 'order_entry_decoded.html'

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit()

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

with open('analysis_output.txt', 'w', encoding='utf-8') as out:
    out.write(f"HTML Title: {soup.title.string if soup.title else 'No Title'}\n\n")
    
    # 1. Analyze Buttons
    out.write("="*50 + "\n")
    out.write("BUTTONS ANALYSIS\n")
    out.write("="*50 + "\n\n")
    
    buttons = soup.find_all('button')
    out.write(f"Found {len(buttons)} buttons.\n\n")
    
    for i, btn in enumerate(buttons):
        out.write(f"--- Button {i+1} ---\n")
        out.write(f"Classes: {btn.get('class', [])}\n")
        out.write(f"Type: {btn.get('type', '')}\n")
        out.write(f"Text: {btn.get_text(strip=True)[:50]}\n")
        parent = btn.find_parent('div')
        if parent:
            out.write(f"Parent Class: {parent.get('class', [])}\n")
        out.write("\n")
    
    # 2. Analyze Form Structure
    out.write("="*50 + "\n")
    out.write("FORM STRUCTURE ANALYSIS (RECORDS 7)\n")
    out.write("="*50 + "\n\n")
    
    # Check specifically for the order entry box
    container = soup.select_one('.box-order-entry') or soup.find('form')
    
    if container:
        out.write(f"Container: {container.name} | Classes: {container.get('class', [])}\n")
        # Check inputs
        inputs = container.find_all('input')
        out.write(f"Inputs: {len(inputs)}\n")
        # Check buttons
        btns = container.find_all('button')
        out.write(f"Buttons inside: {len(btns)}\n")
        for b in btns:
            out.write(f"  - Btn: {b.get('class', [])} Text: '{b.get_text(strip=True)}' Type: {b.get('type')}\n")
    else:
        out.write("❌ No .box-order-entry or form found!\n")

print("Analysis saved to analysis_output.txt")
