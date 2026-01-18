from bs4 import BeautifulSoup
import re

def main():
    with open("dashboard_dump.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    soup = BeautifulSoup(html, "html.parser")
    
    with open("structure.txt", "w", encoding="utf-8") as out:
        def log(msg):
            out.write(str(msg) + "\n")
            print(msg) # Still print for debug

        # helper to print hierarchy
        def print_hierarchy(elem):
            path = []
            curr = elem
            while curr and curr.name != '[document]':
                name = curr.name
                classes = ".".join(curr.get("class", []))
                if classes:
                    name += f".{classes}"
                path.append(name)
                curr = curr.parent
            log(" > ".join(reversed(path)))

        log("--- Searching for 'Collateral' ---")
        # visual search for text
        matches = soup.find_all(string=re.compile("Collateral", re.I))
        for m in matches:
            if m.parent.name in ['style', 'script', 'head', 'title', 'meta']:
                continue
            log(f"\nMatch: '{m.strip()}' inside <{m.parent.name}>")
            parent = m.parent
            print_hierarchy(parent)
            # Check siblings for values (numbers)
            log("  Siblings/Children:")
            # If parent is a container (like div), look at its children too
            if parent.name in ['div', 'tr', 'ul']:
                 for child in parent.find_all(recursive=False):
                    text = child.get_text(strip=True)[:50]
                    log(f"    Child <{child.name} class='{child.get('class')}'>: {text}")
            
            # check next siblings of the text node's parent
            for sib in parent.next_siblings:
                if sib.name:
                    text = sib.get_text(strip=True)[:50]
                    log(f"    Sibling <{sib.name} class='{sib.get('class')}'>: {text}")
                    
        log("\n--- Searching for 'Limit' ---")
        matches = soup.find_all(string=re.compile("Limit", re.I))
        for m in matches:
            if m.parent.name in ['style', 'script', 'head', 'title', 'meta']:
                continue
            log(f"\nMatch: '{m.strip()}' inside <{m.parent.name}>")
            parent = m.parent
            print_hierarchy(parent)
             # If parent is a container (like div), look at its children too
            if parent.name in ['div', 'tr', 'ul']:
                 for child in parent.find_all(recursive=False):
                    text = child.get_text(strip=True)[:50]
                    log(f"    Child <{child.name} class='{child.get('class')}'>: {text}")
            
            for sib in parent.next_siblings:
                 if sib.name:
                    text = sib.get_text(strip=True)[:50]
                    log(f"    Sibling <{sib.name} class='{sib.get('class')}'>: {text}")

if __name__ == "__main__":
    main()
