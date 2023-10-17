# The-Morning

![Embed Example](https://github.com/ibrahimmudassar/The-Morning/assets/22484328/67dca18f-7c29-4f53-96b1-b3cc037953b1) <br />

I wanted to create a bot that would automatically send me The Morning Newsletter from The New York Times to my Discord Server.

Scrapes using requests_html and deployed using GitHub Actions.

This code works with Restful APIs as well, just comment out the discord specific function.

#### Warning!
This code is not going to work unless you define a couple environment variables. This can be done a couple of ways:

- Control Panel > Advanced System Settings > Advanced > Environment Variables
- Create a .env file in the folder and define the required environment variables there  

If you are using discord embeds you will need to define a WEBHOOKS variable as such:
WEBHOOKS=exampleapi.discord.com,exampleapi.discord.com

## RESTful APIs

I have a function set up and its implementation is for my Amazon Alexa. You only need to change the url as the function just uses a post request.
