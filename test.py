import io  # For ColorThief raw file
import urllib.parse
from datetime import datetime  # For time

import httpx
import psycopg2
import pytz  # Timezone
from colorthief import ColorThief  # Find the dominant color
from discord_webhook import DiscordEmbed, DiscordWebhook  # Connect to discord
from environs import Env  # For environment variables
from playwright.sync_api import sync_playwright

env = Env()
env.read_env()  # read .env file, if it exists


conn = psycopg2.connect(env("DB_KEY"))
curs = conn.cursor()

today = pytz.timezone("US/Eastern").localize(datetime.now()).strftime("%Y/%m/%d")

there_is_a_newsletter_today = False
briefing_link = ""
og_data = {}


def no_entry_mitigator(x):
    if len(x) == 0:
        return False
    return True


def dominant_image_color(image_link):
    r = httpx.get(image_link, follow_redirects=True)

    color_thief = ColorThief(io.BytesIO(r.content))
    dominant_color = color_thief.get_color(quality=3)
    hex = "%02x%02x%02x" % dominant_color
    return hex


def embed_to_discord(data, nyt_link):

    # create embed object for webhook
    embed = DiscordEmbed(
        title=data["og:title"],
        description=data["og:description"],
        color=dominant_image_color(data["og:image"]),
    )

    safe_nyt_link = urllib.parse.quote_plus(nyt_link, safe="")
    bypass_link = f"https://archive.today/?run=1&url={safe_nyt_link}"

    embed.add_embed_field(
        name="Link",
        value=f"[Read Full Article Here]({nyt_link})\n[Archive Article Here]({bypass_link})",
        inline=False,
    )

    # Captioning the image
    if no_entry_mitigator(data["twitter:image:alt"]):
        embed.add_embed_field(
            name="Caption", value=data["twitter:image:alt"], inline=False
        )

    # Author
    if no_entry_mitigator(data["byl"]):
        embed.set_author(name=data["byl"])

    # set image
    if no_entry_mitigator(data["og:image"]):
        embed.set_image(url=data["og:image"])

    # set thumbnail
    embed.set_thumbnail(
        url="https://static01.nyt.com/images/2020/05/04/pageoneplus/04morning-icon/04morning-icon-mobileMasterAt3x.png"
    )

    # set footer
    embed.set_footer(text="The Morning Newsletter")

    # set timestamp
    embed.set_timestamp(
        datetime.fromisoformat(data["article:published_time"])
    )  # type: ignore

    # add embed object to webhook(s)
    # Webhooks to send to
    for webhook_url in env.list("WEBHOOKS"):
        webhook = DiscordWebhook(url=webhook_url)
        webhook.add_embed(embed)
        webhook.execute()


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page()

    url = "https://www.nytimes.com/series/us-morning-briefing"
    page.goto(url)

    # Get all links from the page
    links = page.query_selector_all("a")

    for link in links:
        if today in link.get_attribute("href"):
            briefing_link = f"https://www.nytimes.com{link.get_attribute('href')}"
            there_is_a_newsletter_today = True
            break
    
    if briefing_link == "":
        exit()
    
    page.goto(briefing_link)

    metas = page.query_selector_all("meta")
    for meta in metas:
        if meta.get_attribute("content"):
            key = ""
            value = meta.get_attribute("content")

            # one or the other should be there
            if meta.get_attribute("property"):
                key = meta.get_attribute("property")
            if meta.get_attribute("name"):
                key = meta.get_attribute("name")

            og_data[key] = value

    curs.execute("SELECT * from nyt")
    has_link = False
    for i in curs.fetchall():
        if i[0] == briefing_link:
            has_link = True
            break

    if there_is_a_newsletter_today and not has_link:
        embed_to_discord(og_data, briefing_link)

        curs.execute(
            f"INSERT INTO nyt (link, timereceived) VALUES ('{briefing_link}','{datetime.now().isoformat()}')"
        )
        conn.commit()
