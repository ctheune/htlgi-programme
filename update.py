# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "beautifulsoup4",
#     "humanize",
#     "requests",
# ]
# ///


import argparse
from zoneinfo import ZoneInfo
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
        

def main(download=True) -> None:
    if download:
        download_programme()

    raw_programme = Path("download.html").read_text()

    soup = BeautifulSoup(raw_programme, 'html.parser')

    known_ids = set()

    # Remove the hrs
    for hr in soup.find_all("hr"):
        hr.unwrap()

    # Ensure there are no duplicates
    for event in soup.find_all('div', class_="productItem"):
        a = event.find("a")
        name = a.attrs["name"]
        assert name.startswith("product-id")
        id = name.split("-")[2]
        assert id not in known_ids, id
        known_ids.add(id)
        hr = soup.new_tag("hr")
        event.insert(0, hr)

        # Mark venue elements
        venue = event.find(class_="product_details_inner").find_all("div")[2]
        assert "Venue:" in event.get_text()
        venue["class"] = "venue"

        # Mark epoch time for this event
        date = event.find(class_="programme-page--date").text.strip()
        time = event.find(class_="programme-page--time").text.strip()
        # 'Fri 23 May 4:15pm'
        event_time = datetime.datetime.strptime(f"{date} {time};2025", "%a %d %b %I:%M%p;%Y")
        timestamp = event_time.replace(tzinfo=ZoneInfo("Europe/London")).astimezone(datetime.timezone.utc).timestamp()
        event["timestamp"] = str(timestamp * 1000) # js works in milliseconds


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

    # Date navigation

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

    # Category filtering
    sessiontypes = set()
    for candidate in soup.find_all(class_="sessiontype"):
        sessiontypes.add(candidate.get_text())
    sessiontypes = ["- All -"] + sorted(sessiontypes)

    # Location filtering
    locations = set()
    for candidate in soup.find_all("div"):
        text = candidate.get_text()
        if text.startswith("Venue: "):
            locations.add(text.split(": ", maxsplit=1)[1])
    locations = ["- All -"] + sorted(locations)


    last_update = datetime.datetime.now(ZoneInfo("Europe/London"))

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


<script type="text/hyperscript">
    def updateLocationForFilters()
        log "Updating location for filters"
        set :location to #filterLocation
        set :sessiontype to #filterSessiontype
        log :location
        log :sessiontype
        set :hash to document.location.hash
        log :hash
        if :hash is null then
            set :hash to ""
        end
        call history.pushState({}, document.title, "?location=" + encodeURIComponent(:location.value) + "&sessiontype=" + encodeURIComponent(:sessiontype.value) + :hash)
        call updateQRCode()
        call applyFilters()
    end

    def applyFilters()
        log "Applying filters"
        set :location_filter to (the (value of #filterLocation))
        set :sessiontype_filter to (the (value of #filterSessiontype))
        remove .hidden from .productItem
        if :location_filter is not '- All -' then
            for i in .productItem 
                if (the first of .venue in i)'s textContent does not contain :location_filter then
                    add .hidden to i
                end
            end
        end
        if :sessiontype_filter is not '- All -' then
            for i in .productItem 
                if (the first of .sessiontype in i)'s textContent does not contain :sessiontype_filter then
                    add .hidden to i
                end
            end
        end
    end

    def loadFilters() 
        js
            return new URLSearchParams(window.location.search);
        end
        set :search to it
        set :location to :search.get("location")
        if :location is not null then
            for candidate in <#filterLocation option />
                if candidate's @value is :location then
                    set candidate's @selected to true
                end
            end
        end
        set :sessiontype to :search.get("sessiontype")
        if :sessiontype is not null then
            for candidate in <#filterSessiontype option />
                if candidate's @value is :sessiontype then
                    set candidate's @selected to true
                end
            end
        end
    end

    def updateLocationForNextEvent()
        log "Updating Location for next event"
        call history.pushState({}, document.title, "#next-event")
        call updateQRCode()
        call handleNextEventJump()
    end

    def handleNextEventJump()
        log "handleNextEventJump"
        set :location to window.location
        if :location's hash is not "#next-event" then
            exit
        end
        set :now to Date.now()
        for i in .productItem 
            if i matches .hidden then
                continue
            end
            set :event_time to i's @timestamp as an Int
            if :event_time > :now then
                go to i smoothly
                break
            end
        end
    end

    def markPastEvents()
        log "Marking past events"
        set :now to Date.now()
        for i in .productItem 
            set :event_time to i's @timestamp as an Int
            if :event_time < :now then
                add .elapsed to it
                continue
            end
            break
        end
    end

    def initQRCode()
        js 
            return new QRCode(document.getElementById("qrcode"), {
                text: window.location.href,
                width: 256,
                height: 256});
        end
        set $qrcode to it
    end

    def updateQRCode()
        set qrcode to $qrcode
        log qrcode
        js (qrcode)
            qrcode.clear();
            qrcode.makeCode(window.location.href);
        end
    end
</script>

    <script src="https://unpkg.com/hyperscript.org@0.9.14"></script>
    <script src="./qrcode.min.js"></script>

<style type="text/css">

#warning {
    border: 2px solid salmon;
    background: mistyrose;
    padding:1em;
    padding-bottom: 0;
    cursor: zoom-in;
}

.col {
    width: 20em;
    float: left;
}

.elapsed {
  opacity: 0.3;
}

.hidden {
    display: none;
}

#qrcodeContainer {
  position: fixed; /* Sit on top of the page content */
  width: 100%; /* Full width (cover the whole page) */
  height: 100%; /* Full height (cover the whole page) */
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0,0,0,0.5); /* Black background with opacity */
  z-index: 2; /* Specify a stack order in case you're using a different order for other elements */
  cursor: pointer; /* Add a pointer on hover */
}

#qrcodeContainer .wrapper {
  display: block;
  margin-left: auto;
  margin-right: auto;
  margin-top: 10em;
  width: 30em;
  height: 30em;
  background-color: white;
  padding: 1em;
  border: 1px solid #cccccc;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
  border-radius: 8px;
}

#qrcode {
  display: flex;
  justify-content: center;
  align-items: center;
}

@media (max-width:1024px)  { 
    /* smartphones, portrait iPhone, portrait 480x320 phones (Android) */

    #warning {
        margin-bottom: 1em;
    }

}
@media (min-width:1025px) {
   /* big landscape tablets, laptops,and desktops */ 

   #share {
    width: 20em;
    position: absolute;
    top: 7em;
    right: 0;
   }
    #warning {
        margin-bottom: 1em;
        width: 20em;
        position: absolute;
        right: 0;
        top: 1em;
    }

    header {
        position: sticky;
        top: 0;
        padding-top: 1em;
        z-index: 1;
        background: white;
    }

    html {
            scroll-behavior: smooth;
            scroll-padding-top: 11em; 
    }

}
</style>
</head>""" + f"""
<body _="init
    markPastEvents()
    loadFilters()
    applyFilters()
    handleNextEventJump()
    initQRCode()
    ">

<main>

<div id="qrcodeContainer" _="on click toggle my *display" style="display:none;">
    <div class="wrapper">
        <h2>Share this page</h2>
        <div id="qrcode"></div>
    </div>
</div>

<header>
<div id="warning" _="on click toggle the *display of the .explain in me">
<h3>This is NOT the official HTLGI website. <span style="font-size:10pt; font-style: italic; font-weight:normal;">Click for details and help ...</span></h3>
<div class="explain" style="display:none;">
    <p>
    This is a helper to navigate the programme faster than the official site. 
    This has been made for the Dave Snowden & friends @ HTLGI group.
    </p>

    <p>Get in touch on the Whatsapp group for feedback and improvement requests.</p>

    <p>All links open on the official site where you can buy fastpasses and tickets. To avoid confusion I have disabled those features here.</p>

    <p>Last updated: {last_update.strftime("%Y-%m-%d %H:%M:%S")} (Europe/London)</p>
</div>
</div>
"""

    result += """

<div id="share" _="on click toggle the *display of the #qrcodeContainer">
    Share this page ...
</div>

<div class="col">
<label>Time</label>

<ul>
    <li style="margin-bottom: 1em;"><a _="on click updateLocationForNextEvent()">Jump to next event</a></li>
"""
    for date in date_navs:
        result += f"""
    <li><a href="#nav-day-{date[0]}">{date[1].get_text()}</a></li>
    """


    result += f"""
</ul>
</div>

<div class="col">

<form>
    <div class="field">
    <label for="filter_location">Location</label>
    <select name="filter_location" id="filterLocation" _="on change updateLocationForFilters()"> """
    for i, location in enumerate(locations):
        selected = " selected" if not i else ""
        result += f"""
        <option value="{location}" {selected}>{location}</option>
"""

    result += """
    </select>
    </div>

    <div class="field">
    <label for="filter_sessiontype">Session Type</label>
    <select name="filter_sessiontype" id="filterSessiontype" _="on change updateLocationForFilters()">
"""

    for i, sessiontype in enumerate(sessiontypes):
        selected = " selected" if not i else ""
        result += f"""
        <option value="{sessiontype}" {selected}>{sessiontype}</option>
"""

    result += """
    </select>
    </div>
</form>    
</div>
<div style="clear:both"></div>
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
    parser = argparse.ArgumentParser(
        description='Update the HTLGI programme')
    parser.add_argument('--skip-download', action="store_true")
    args = parser.parse_args()
    main(not args.skip_download)
