import re
import json
from bs4 import BeautifulSoup

# getting the simulcast page content directly from CR is a bitch.
# just copy the "<html>" element content and paste it here.
CR_SIMULCAST_HTML = r"""



"""


def extract_series_info(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")

    collection = soup.find("div", class_="erc-browse-cards-collection")
    if not collection:
        return []

    series = []
    pattern = re.compile(r"^/series/([A-Z0-9]+)/([^/?#]+)")

    for card in collection.find_all("div", class_="browse-card", recursive=False):
        for a in card.find_all("a", href=True):
            match = pattern.match(a["href"])
            if match:
                series_id = match.group(1)
                series_name = match.group(2)
                series.append((series_id, series_name))
                break

    return series


series_info = extract_series_info(CR_SIMULCAST_HTML)

output = {
    "cr_monitor_series_id": {}
}

text_lines = []

for series_id, series_name in series_info:
    output["cr_monitor_series_id"][series_id] = {}
    text_lines.append(f"{series_id} - {series_name}")

print(json.dumps(output, indent=4))
print()
print("\n".join(text_lines))
