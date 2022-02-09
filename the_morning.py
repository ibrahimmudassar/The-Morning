import io  # For ColorThief raw file
import json
from datetime import datetime  # For time

import metadata_parser  # For Opengraph
import psycopg2  # Heroku Database
import pytz  # Timezone
import requests  # Download image link
from colorthief import ColorThief  # Find the dominant color
from discord_webhook import DiscordEmbed, DiscordWebhook  # Connect to discord
from environs import Env  # For environment variables
from selenium import webdriver  # Browser prereq
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# Setting up environment variables
env = Env()
env.read_env()  # read .env file, if it exists

# Connecting with the heroku database
DATABASE_URL = env('DATABASE_URL')

conn = psycopg2.connect(DATABASE_URL, sslmode='require')


# I use opengraph to simplify the collection process
def embed_to_discord(data, nyt_link):
    # Webhooks to send to
    webhook = DiscordWebhook(url=env.list("WEBHOOKS"))

    # create embed object for webhook
    embed = DiscordEmbed(title=data["og:title"], description=data["og:description"],
                         color=dominant_image_color(data["og:image"]))

    # Mentioning the link to the article
    embed.add_embed_field(
        name="Link", value=" [Read Full Article Here](" + nyt_link + ")", inline=False)

    # Captioning the image
    if no_entry_mitigator(data["og:image:alt"]):
        embed.add_embed_field(
            name="Caption", value=data["og:image:alt"], inline=False)

    # Author
    if no_entry_mitigator(data["byl"]):
        embed.set_author(name=data["byl"])

    # set image
    if no_entry_mitigator(data["og:image"]):
        embed.set_image(url=data["og:image"])

    # set thumbnail
    embed.set_thumbnail(
        url='https://static01.nyt.com/images/2020/05/04/pageoneplus/04morning-icon/04morning-icon-mobileMasterAt3x.png')

    # set footer
    embed.set_footer(text='The Morning Newsletter')

    # set timestamp (needs unix int)
    nyt_date = browser.find_element(By.TAG_NAME, "time").get_attribute(
        "datetime")  # get the unix time
    # converts to datetime object
    date = datetime.strptime(nyt_date, "%Y-%m-%dT%H:%M:%S%z")
    time_as_int = (date - pytz.utc.localize(datetime(1970, 1, 1))
                   ).total_seconds()  # converts to unix int
    embed.set_timestamp(time_as_int)

    # add embed object to webhook(s)
    webhook.add_embed(embed)
    webhook.execute()

# A simple message


def send_to_discord(message):
    webhook = DiscordWebhook(url=env.list("WEBHOOKS"), content=message)
    webhook.execute()


def restful_send(notification):
    body = json.dumps({

        "notification": notification,

        "accessCode": env("ACCESS_CODE")

    })

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
    hex = '%02x%02x%02x' % dominant_color
    return hex


# Create new Instance of Chrome
options = webdriver.ChromeOptions()
options.binary_location = env("GOOGLE_CHROME_BIN")
options.add_argument("--headless")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")

browser = webdriver.Chrome(service=Service(env(
    'CHROMEDRIVER_PATH')), options=options)
browser.get("https://www.nytimes.com/series/us-morning-briefing")


# This function matches today's date to the newest article's date to determine
# if there is a newsletter for today
elems = browser.find_elements(By.TAG_NAME, 'a')
there_is_a_newsletter_today = False
today = pytz.timezone(
    'US/Eastern').localize(datetime.now()).strftime("%Y/%m/%d")

for elem in elems:
    if "https://www.nytimes.com/" + today in elem.get_attribute('href'):
        there_is_a_newsletter_today = True
        briefing_link = elem.get_attribute('href')

if there_is_a_newsletter_today:
    browser.get(briefing_link)

    # Getting Opengraph data
    og_page = metadata_parser.MetadataParser(
        search_head_only=False, url=briefing_link)
    data = og_page.metadata["meta"]

    embed_to_discord(data, briefing_link)

    restful_send("The Morning Newsletter," + data["og:title"])

else:
    send_to_discord("There is no Morning Newsletter today :sob:")
    restful_send("There is no Morning Newsletter today")

browser.quit()
