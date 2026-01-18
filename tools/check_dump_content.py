from bs4 import BeautifulSoup

def main():
    try:
        with open("dashboard_dump.html", "r", encoding="utf-8") as f:
            html = f.read()
        
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        
        print(f"--- Dump Text Content ({len(text)} chars) ---")
        print(text[:5000]) # First 5000 chars
        
        print("\n--- Searching Keywords ---")
        keywords = ["Collateral", "Limit", "Fund", "Turnover", "Nepse", "Dashboard"]
        for k in keywords:
            if k in text:
                print(f"FOUND: '{k}'")
            else:
                print(f"MISSING: '{k}'")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
