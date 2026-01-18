from bs4 import BeautifulSoup

def main():
    try:
        with open("order_entry_dump.html", "r", encoding="utf-8") as f:
            html = f.read()
    except:
        print("Dump file not found.")
        return

    soup = BeautifulSoup(html, "html.parser")
    
    print("--- Finding Tables ---")
    tables = soup.find_all("table")
    print(f"Found {len(tables)} tables.")
    
    for i, table in enumerate(tables):
        print(f"\nTABLE #{i}")
        classes = table.get("class", [])
        print(f"Classes: {classes}")
        parent = table.parent
        print(f"Parent: <{parent.name} class='{parent.get('class')}'>")
        
        # Print Headers
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        print(f"Headers: {headers}")
        
        # Check first 3 rows
        rows = table.find_all("tr")
        print(f"Total Rows: {len(rows)}")
        for j, row in enumerate(rows[:3]):
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if cells:
                print(f"  Row {j}: {cells}")

    print("\n--- Finding 'Daily Order Book' Container ---")
    # Finding by text
    # In BeautifulSoup 4, searching by string finds NavigableString
    daily = soup.find(string="Daily Order Book")
    if daily:
        print(f"FOUND 'Daily Order Book' node: {daily}")
        parent = daily.parent
        print(f"Parent tag: {parent.name}")
        grandparent = parent.parent
        print(f"Grandparent tag: {grandparent.name if grandparent else 'None'}")
        if grandparent:
             print(f"Grandparent class: {grandparent.get('class')}")

    print("\n--- Finding 'Historic Order Book' Container ---")
    hist = soup.find(string="Historic Order Book")
    if hist:
        print(f"FOUND 'Historic Order Book' node: {hist}")
        print(f"Parent class: {hist.parent.get('class')}")

if __name__ == "__main__":
    main()
