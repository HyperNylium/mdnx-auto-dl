import re
import json
from bs4 import BeautifulSoup

# getting the simulcast page content directly from CR is a bitch.
# just copy the "<html>" element content and paste it here.
CR_SIMULCAST_HTML = r"""



"""


def extract_series_ids(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    collection = soup.find("div", class_="erc-browse-cards-collection")
    if not collection:
        return []

    series_ids = []
    pattern = re.compile(r"^/series/([A-Z0-9]+)/")

    for card in collection.find_all("div", class_="browse-card", recursive=False):
        for a in card.find_all("a", href=True):
            match = pattern.match(a["href"])
            if match:
                series_ids.append(match.group(1))
                break

    return series_ids


ids = extract_series_ids(CR_SIMULCAST_HTML)

output = {
    "cr_monitor_series_id": {}
}

for series_id in ids:
    output["cr_monitor_series_id"][series_id] = {}

print(json.dumps(output, indent=2))
