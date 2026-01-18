from bs4 import BeautifulSoup

def parse():
    with open("dashboard_dump.html", "r", encoding="utf-8") as f:
        html = f.read()
        
    soup = BeautifulSoup(html, 'html.parser')
    
    print("--- Parsing Dashboard Dump (Context Hunt) ---")
    
    # helper
    def find_parent_classes(text_query, dump_html=False):
        print(f"\nSearching for '{text_query}'...")
        # Find element containing text
        element = soup.find(string=lambda t: t and text_query in t)
        if element:
            print(f"Found text node: {element.strip()}")
            parent = element.parent
            while parent and parent.name != 'body':
                classes = parent.get('class', [])
                if 'card' in classes:
                    print(f"    -> Found Card container! Dumping HTML to {text_query}_card.html")
                    if dump_html:
                        with open(f"{text_query.replace(' ', '_')}_card.html", "w", encoding="utf-8") as f:
                            f.write(parent.prettify())
                    return # Stop after finding the card
                parent = parent.parent
        else:
            print("Text not found.")

    find_parent_classes("My Trade Summary", dump_html=True)
    find_parent_classes("My Collateral Summary", dump_html=True)
    find_parent_classes("Fund Summary", dump_html=True)

if __name__ == "__main__":
    parse()
