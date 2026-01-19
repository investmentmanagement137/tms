
from bs4 import BeautifulSoup
import os

file_path = 'order_entry_decoded.html'

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit()

with open(file_path, 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

with open('analysis_output.txt', 'w', encoding='utf-8') as out:
    out.write(f"HTML Title: {soup.title.string if soup.title else 'No Title'}\n")

    tables = soup.find_all('table')
    out.write(f"Found {len(tables)} tables.\n")

    for i, table in enumerate(tables):
        out.write(f"\n--- Table {i+1} ---\n")
        out.write(f"Classes: {table.get('class', [])}\n")
        out.write(f"ID: {table.get('id', '')}\n")
        
        # Headers
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        out.write(f"Headers: {headers}\n")
        
        # Ancestors
        ancestors = []
        for parent in table.parents:
            if parent.name == 'html':
                break
            name = parent.name
            classes = parent.get('class', [])
            ancestors.append(f"{name}.{'.'.join(classes) if classes else ''}")
            if len(ancestors) > 5: break
        out.write(f"Ancestors: {' > '.join(ancestors)}\n")

        # Rows (first 5)
        rows = table.find_all('tr')
        out.write(f"Total Rows: {len(rows)}\n")
        for j, row in enumerate(rows[:5]):
            cols = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
            out.write(f"  Row {j}: {cols}\n")

print("Analysis saved to analysis_output.txt")
