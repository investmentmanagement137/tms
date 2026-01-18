
with open(r"c:\Users\purib\Downloads\antigravity\APIFy\tms captch new\dashboard_dump.html", "r", encoding="utf-8") as f:
    content = f.read()

index = content.find("My Trade Summary")
if index != -1:
    start = max(0, index - 500)
    end = min(len(content), index + 1000)
    print(content[start:end])
else:
    print("String not found")
