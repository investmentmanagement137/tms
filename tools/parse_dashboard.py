from bs4 import BeautifulSoup

def parse():
    with open("dashboard_dump.html", "r", encoding="utf-8") as f:
        html = f.read()
        
    soup = BeautifulSoup(html, 'html.parser')
    
    print("--- Parsing Dashboard Dump ---")
    
    # Strategy 1: Look for "data__summary" items (Top bar stats)
    summary_items = soup.select(".data__summary--item")
    print(f"Found {len(summary_items)} summary items.")
    
    for item in summary_items:
        try:
            label = item.find('span').get_text(strip=True)
            # The number is usually in a class like "data__summary--num" or just the second span
            num_span = item.select_one(".data__summary--num")
            value = num_span.get_text(strip=True) if num_span else "N/A"
            print(f"Summary: {label} = {value}")
        except Exception as e:
            print(f"Skipping item: {e}")
            
    # Strategy 2: Look for collateral/limit specific boxes
    # Often in TMS there are boxes for "Collateral", "Trade Limit"
    
    print("\n--- Searching for Boxes ---")
    boxes = soup.select(".box")
    for box in boxes:
        title_el = box.select_one(".box__title h2")
        if title_el:
            title = title_el.get_text(strip=True)
            print(f"Box: {title}")
            # Try to grab table data inside
            rows = box.select("tbody tr")
            if rows:
                print(f"  - Found {len(rows)} rows of data")
                for row in rows[:3]: # First 3
                    cols = [c.get_text(strip=True) for c in row.find_all('td')]
                    print(f"    {cols}")

if __name__ == "__main__":
    parse()
