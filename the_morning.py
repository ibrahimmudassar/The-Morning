import io  # For ColorThief raw file
import json
from datetime import datetime  # For time
from pprint import pprint

import psycopg2
import pytz  # Timezone
import requests  # Download image link
from bs4 import BeautifulSoup
from colorthief import ColorThief  # Find the dominant color
from discord_webhook import DiscordEmbed, DiscordWebhook  # Connect to discord
from environs import Env  # For environment variables
from requests_html import HTMLSession

# Setting up environment variables
env = Env()
env.read_env()  # read .env file, if it exists

conn = psycopg2.connect(env("DB_KEY"))
curs = conn.cursor()

# Connecting with the database (originally this was meant so I could run every 5 minutes for real time posting)
# DATABASE_URL = env('DATABASE_URL')

# I use opengraph to simplify the collection process
# Although I'm not using the builtin package for it I can read the metadata that NYT provides


def embed_to_discord(data, nyt_link):

    # create embed object for webhook
    embed = DiscordEmbed(
        title=data["og:title"],
        description=data["og:description"],
        color=dominant_image_color(data["og:image"]),
    )

    bypass_link = f"{nyt_link}"

    embed.add_embed_field(
        name="Link",
        value=f"[Read Full Article Here]({nyt_link})\n[Archive Article Here]({bypass_link})",
        inline=False,
    )

    # Captioning the image
    if no_entry_mitigator(data["og:image"]):
        embed.add_embed_field(name="Caption", value=data["og:image"], inline=False)

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


# A simple message


def send_to_discord(message):
    for webhook_url in env.list("WEBHOOKS"):
        webhook = DiscordWebhook(url=webhook_url, content=message)
        webhook.execute()


def restful_send(notification):
    body = json.dumps({"notification": notification, "accessCode": env("ACCESS_CODE")})

    requests.post(url="https://api.notifymyecho.com/v1/NotifyMe", data=body)


# checks to see if the entry is of length 0, and if it is, returns an empty string
# this makes it fail proof and will still let the embed on discord without causing problems


def no_entry_mitigator(x):
    if len(x) == 0:
        return False
    return True


# Takes the image link, downloads it, and then returns a hex color code of the most dominant color


def dominant_image_color(image_link):
    r = requests.get(image_link, allow_redirects=True)

    color_thief = ColorThief(io.BytesIO(r.content))
    dominant_color = color_thief.get_color(quality=3)
    hex = "%02x%02x%02x" % dominant_color
    return hex


url = "https://www.nytimes.com/series/us-morning-briefing"

session = HTMLSession()
r = session.get(url)

# today = pytz.timezone(
#     'US/Eastern').localize(datetime.now()).strftime("%Y/%m/%d")
today = "2024/08/20"

elems = r.html.find("a")  # type: ignore
elems = [i.attrs["href"] for i in elems if "href" in i.attrs]

there_is_a_newsletter_today = False

for href in elems:
    if today in href:
        briefing_link = f"https://www.nytimes.com{href}"
        there_is_a_newsletter_today = True
        break

curs.execute("SELECT * from nyt")
has_link = False
for i in curs.fetchall():
    if i[0] == briefing_link:
        has_link = True
        break

if there_is_a_newsletter_today and not has_link:

    send_to_discord(briefing_link)

    curs.execute(
        f"INSERT INTO nyt (link, timereceived) VALUES ('{briefing_link}','{datetime.now().isoformat()}')"
    )
    conn.commit()
    # soup = BeautifulSoup(requests.get(bypass_link).content, 'html.parser')
    # metas = soup.find_all('meta')

    # data = {}
    # for meta in metas:
    #     if 'content' in meta.attrs:
    #         key = ''
    #         value = meta.attrs['content']

    #         # one or the other should be there
    #         if 'property' in meta.attrs:
    #             key = meta.attrs['property']
    #         if 'name' in meta.attrs:
    #             key = meta.attrs['name']

    #         data[key] = value
    # pprint(data)
    # embed_to_discord(data, briefing_link)

    # restful_send("The Morning Newsletter," + data["og:title"])

# else:
#     send_to_discord("There is no Morning Newsletter today :sob:")
# restful_send("There is no Morning Newsletter today")
