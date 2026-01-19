
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
    
    # Find all buttons
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
        out.write(f"Disabled: {btn.get('disabled')}\n\n")
    
    # Find Order Book table
    out.write("="*50 + "\n")
    out.write("ORDER BOOK TABLE\n")
    out.write("="*50 + "\n\n")
    
    # Look for kendo grid content
    kendo_content = soup.select('.k-grid-content tbody tr')
    out.write(f"Rows in .k-grid-content tbody tr: {len(kendo_content)}\n")
    for row in kendo_content[:5]:
        cols = [td.get_text(strip=True) for td in row.find_all('td')]
        out.write(f"  Row: {cols}\n")

print("Analysis saved to analysis_output.txt")
