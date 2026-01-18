from bs4 import BeautifulSoup
import re

def main():
    with open("order_entry_dump.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    soup = BeautifulSoup(html, "html.parser")
    
    with open("order_entry_structure.txt", "w", encoding="utf-8") as out:
        def log(msg):
            out.write(str(msg) + "\n")
            print(msg)

        def print_elem_info(elem):
            attrs = [f'{k}="{v}"' for k, v in elem.attrs.items()]
            log(f"  <{elem.name} {' '.join(attrs)} >")
            # print parent
            if elem.parent:
                 log(f"    Parent: <{elem.parent.name} class='{elem.parent.get('class')}'>")
            # print label if nearby
            

        log("--- Searching for INPUTs ---")
        inputs = soup.find_all("input")
        for i, inp in enumerate(inputs):
            log(f"Input #{i}:")
            print_elem_info(inp)
            
        log("\n--- Searching for SELECTs ---")
        selects = soup.find_all("select")
        for i, sel in enumerate(selects):
            log(f"Select #{i}:")
            print_elem_info(sel)
            
        log("\n--- Searching for any element with 'instrument' in attributes ---")
        for elem in soup.find_all():
            for k, v in elem.attrs.items():
                if "instrument" in str(k).lower() or "instrument" in str(v).lower():
                    log(f"Match in <{elem.name}> attribute {k}='{v}'")
                    print_elem_info(elem)

        log("\n--- Searching for LABELS (Text matches) ---")
        for term in ["Instrument", "Symbol", "Qty", "Price", "Order Book", "Equity", "Mutual"]:
            log(f"Searching for '{term}':")
            matches = soup.find_all(string=re.compile(term, re.I))
            for m in matches:
                if m.parent.name not in ['script', 'style']:
                    log(f"  Found text '{m.strip()}' in <{m.parent.name} class='{m.parent.get('class')}'>")
                    print_elem_info(m.parent)

if __name__ == "__main__":
    main()
