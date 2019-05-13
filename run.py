import asyncio
import json
from pathlib import Path
from random import randint

import lxml.html as lhtml
from aioauth_client import TwitterClient
from aiohttp import ClientSession, web


class ApiProxy():
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.config = None

        with Path("config.json").open() as f:
            self.config = json.load(f)

        self.session = ClientSession()
        self.twitter = TwitterClient(
            consumer_key=self.config['consumer_key'],
            consumer_secret=self.config['consumer_secret'],
            oauth_token=self.config['oauth_token'],
            oauth_token_secret=self.config['oauth_token_secret']
        )
        self.preshared = self.config['preshared']

    # GET /weather
    async def get_weather(self, request):
        root = None
        endpoint = "https://tenki.jp/forecast/3/16/4410/13108/"

        key = request.headers.get('X-SARISIA-PRESHARED')
        if not key or not key == self.preshared:
            return web.Response(status=403)

        async with self.session.get(endpoint) as res:
            root = lhtml.fromstring(await res.text())

        ret = {
            "today": {
                "weather_telop": root.xpath('//*[@id="main-column"]/section/div[1]/section[1]/div[1]/div[1]/p')[0].text,
                "max": root.xpath('//*[@id="main-column"]/section/div[1]/section[1]/div[1]/div[2]/dl/dd[1]/span[1]')[0].text,
                "min": root.xpath('//*[@id="main-column"]/section/div[1]/section[1]/div[1]/div[2]/dl/dd[3]/span[1]')[0].text
            },
            "tomorrow": {
                "weather_telop": root.xpath('//*[@id="main-column"]/section/div[1]/section[2]/div[1]/div[1]/p')[0].text,
                "max": root.xpath('//*[@id="main-column"]/section/div[1]/section[2]/div[1]/div[2]/dl/dd[1]/span[1]')[0].text,
                "min": root.xpath('//*[@id="main-column"]/section/div[1]/section[2]/div[1]/div[2]/dl/dd[3]/span[1]')[0].text
            }
        }

        return web.json_response(ret)

    # GET /spotify
    async def get_spotify(self, request):
        spotify_csv = None
        endpoint = "https://spotifycharts.com/regional/jp/weekly/latest/download"

        key = request.headers.get('X-SARISIA-PRESHARED')
        if not key or not key == self.preshared:
            return web.Response(status=403)

        async with self.session.get(endpoint) as res:
            spotify_csv = await res.text()

        csv_lines = spotify_csv.split('\n')
        # print(csv_lines)
        ret = {k: "{0[2]} の {0[1]}".format(v.split(',')) for k, v in enumerate(csv_lines[2:5])}

        return web.json_response(ret)

    async def get_twitter(self, request):
        endpoint = "https://api.twitter.com/1.1/trends/place.json"
        params = {"id": 1118370} # Tokyo

        key = request.headers.get('X-SARISIA-PRESHARED')
        if not key or not key == self.preshared:
            return web.Response(status=403)

        twitter_ret = await self.twitter.request('GET', "trends/place.json", params=params)
        trend_words = list(filter(lambda x: not x['name'].startswith('#'), twitter_ret[0]['trends']))
        ret = {i: trend_words[randint(0, len(trend_words)-1)]['name'] for i in range(3)}

        return web.json_response(ret)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    routes = web.RouteTableDef()
    api = ApiProxy()

    app = web.Application()
    app.add_routes([
        web.get('/weather', api.get_weather),
        web.get('/spotify', api.get_spotify),
        web.get('/twitter', api.get_twitter)
    ])

    runner = web.AppRunner(app, handle_signals=True)
    loop.run_until_complete(runner.setup())

    loop.run_until_complete(web.TCPSite(runner, "localhost", 80).start())

    loop.run_forever()
