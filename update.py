# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "beautifulsoup4",
#     "humanize",
#     "requests",
# ]
# ///

from bs4 import BeautifulSoup
import datetime
import humanize

import requests
from pathlib import Path

BASE_URL = "https://howthelightgetsin.org/FullEventListPage_Controller/getevents?offset={offset}&limit={limit}&isInternationalFestival=0&festival=hay"


def download_programme():
    result = ""
    offset = 0
    chunks = 25
    while True:
        print(f"Downloading offset: {offset}")
        response = requests.get(BASE_URL.format(offset=offset, limit=chunks))
        response.raise_for_status()
        if "(no events found)" in response.text:
            break
        result += "<!--- CHUNK MARKER --->"
        result += response.text
        offset += chunks
    Path("download.html").write_text(result)
        

def main() -> None:
    download_programme()

    raw_programme = Path("download.html").read_text()

    soup = BeautifulSoup(raw_programme, 'html.parser')

    known_ids = set()

    # Ensure there are no duplicates
    for event in soup.find_all('div', class_="productItem"):
        a = event.find("a")
        name = a.attrs["name"]
        assert name.startswith("product-id")
        id = name.split("-")[2]
        assert id not in known_ids, id
        known_ids.add(id)


    # Update all links
    for a in soup.find_all("a"):
        if not a.get("href"):
            continue
        if not a["href"].startswith("http"):
            a["href"] = "https://howthelightgetsin.org/" + a["href"]
        a["target"] = "_blank"
    for img in soup.find_all("img"):
        if not img["src"].startswith("http"):
            img["src"] = "https://howthelightgetsin.org/" + img["src"]

    # Remove the ticket forms
    for ticket_form in soup.find_all(class_="ht-fpe--event-ticket-wrapper"):
        ticket_form.extract()

    # disable fastpass headers
    for fastpass in soup.find_all(class_="ht-fpe--fast-pass-header"):
        del fastpass["href"]

    # disable generic ticket link
    for ticket in soup.find_all(class_="ht-fpe--festival-ticket"):
        ticket.extract()

    dates_seen = set()
    date_navs = []
    for candidate in list(soup.find_all("h2", class_="htlgi-heading__small--text")):
        if candidate.get_text() in dates_seen:
            candidate.parent.extract()
            continue
        id = len(date_navs)
        candidate["id"] = f"nav-day-{id}"
        date_navs.append((id, candidate))
        dates_seen.add(candidate.get_text())

    print(f"Found {len(known_ids)} events.")

    result = """<!DOCTYPE html>
<html lang="en-US">
<head>
<title>The Age of the Universe &raquo; HowTheLightGetsIn </title>

    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <link rel="shortcut icon" href="https://howthelightgetsin.org/favicon.ico" />
    <link rel="stylesheet" href="https://use.typekit.net/vfv1goc.css">
    <link href="https://fonts.googleapis.com/css?family=Arvo:400,400i,700,700i" rel="stylesheet">

    <link rel="stylesheet" type="text/css" href="https://howthelightgetsin.org//htlgiecommerce/css/EcommerceGeneric.css?m=1655470222" />
    <link rel="stylesheet" type="text/css" href="https://howthelightgetsin.org//themes/default/css/index.css?m=1743680491" />
    <link rel="stylesheet" type="text/css" href="https://howthelightgetsin.org//htlgiecommerce/css/ecommerce.css?m=1655470222" />
    <link rel="stylesheet" type="text/css" href="https://howthelightgetsin.org//htlgiecommerce/css/EventProduct.css?m=1655470222" />

<style type="text/css">

#warning {
    border: 2px solid salmon;
    background: mistyrose;
    padding:1em;
}

@media (max-width:1024px)  { 
    /* smartphones, portrait iPhone, portrait 480x320 phones (Android) */

    #warning {
        margin-bottom: 1em;
    }

}
@media (min-width:1025px) {
   /* big landscape tablets, laptops,and desktops */ 

    #warning {
        position: absolute;
        width:40em;
        padding: 1em;
        right: 1em;
        top: 1em;
    }

    header {
        height: 17em;
        position: sticky;
        top: 0;
        padding-top: 1em;
        z-index: 2;
        background: white;
    }
}
</style>
</head>
<body>

<main>
<header>
<div id="warning">
<h3>This is NOT the official HTLGI website.</h3>
<p>
This is a helper to navigate the programme faster than the official site. 
This has been made for the Dave Snowden & friends @ HTLGI group.
</p>

<p>Get in touch on the Whatsapp group for feedback and improvement requests.</p>

<p>All links open on the official site where you can buy fastpasses and tickets. To avoid confusion I have disabled those features here.</p>
</div>

"""

    result += """
<ul>
"""
    for date in date_navs:
        result += f"""
    <li><a href="#nav-day-{date[0]}">{date[1].get_text()}</a></li>
    """

    last_update = datetime.datetime.now(datetime.UTC)

    result += f"""
</ul>

<p>
Last updated: {last_update.strftime("%Y-%m-%d %H:%M:%S")} (UTC)
</p>
</header>

"""

    result += soup.prettify()
    result += """
</main>
</body>
</html>
"""

    Path("result.html").write_text(result)


if __name__ == "__main__":
    main()
