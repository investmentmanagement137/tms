from bs4 import BeautifulSoup

def main():
    try:
        with open("order_entry_dump.html", "r", encoding="utf-8") as f:
            html = f.read()
    except:
        print("Dump file not found.")
        return

    soup = BeautifulSoup(html, "html.parser")
    
    print("--- 1. Order Book Pagination Check ---")
    # Look for common pager classes or text "Next"
    pager = soup.find(class_=lambda x: x and ('pager' in x or 'pagination' in x))
    if pager:
        print(f"Potential Pager Found: <{pager.name} class='{pager.get('class')}'>")
        print(pager.prettify()[:500])
    
    # Kendo Grid distinct pagination
    kendo_pager = soup.find(class_="k-pager-wrap")
    if kendo_pager:
        print("Kind Grid Pager Found (k-pager-wrap)!")
        print(kendo_pager.prettify()[:500])
    else:
        print("No Kendo Pager found.")

    print("\n--- 2. Action Links Check ---")
    # Find table rows
    rows = soup.find_all("tr")
    print(f"Found {len(rows)} rows.")
    for i, row in enumerate(rows[:5]): # Check first 5 rows
        print(f"\nRow {i}:")
        # Check for links or buttons
        actions = row.find_all(['a', 'button'])
        if actions:
            for a in actions:
                print(f"  Action Found: Tag=<{a.name}> Text='{a.get_text(strip=True)}' Class='{a.get('class')}' Href='{a.get('href')}' Title='{a.get('title')}'")
        else:
            print("  No action links/buttons found.")
            
if __name__ == "__main__":
    main()
