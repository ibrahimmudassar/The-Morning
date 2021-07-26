# The-Morning

I wanted to create a bot that would automatically send me The Morning Newsletter from The New York Times to my Discord Server.

Scrapes using selenium and deployed using Heroku.

uses build packages in Heroku so the chromedriver is not added.

#### Warning!
This code is not going to work unless you define a WEBHOOKS env variable. The value will look like so (including the quotes and brackets:
    ["URL HERE", "URL HERE"]
