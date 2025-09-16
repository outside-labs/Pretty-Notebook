import fastapi
import uvicorn

import json
from pathlib import Path
import asyncio

from starlette.staticfiles import StaticFiles

from api import publish_api
from views import home
# from services import openweather_service, report_service
# from models.location import Location

api = fastapi.FastAPI()


def configure():
	configure_routing()
	# configure_api_keys()
	# configure_fake_data()


# def configure_api_keys():
# 	f = Path('settings.json').absolute()
# 	if not f.exists():
# 		print(f"WARNING: {file} file not found, you cannot continue, please see settings_template.json")
# 		raise Exception("settings.json file not found, you cannot continue, lease see settings_template.json")
# 	with open('settings.json') as fin:
# 		settings = json.load(fin)
# 		openweather_service.api_key = settings.get('api_key')


def configure_routing():
	api.mount('/static', StaticFiles(directory='static'), name='static') #mounting routes
	api.include_router(home.router)
	api.include_router(publish_api.router)


# def configure_fake_data():
# 	loc = Location(city="Portland", state="Oregon", country="US")
# 	asyncio.run(report_service.add_report("It's misty today", loc))
# 	asyncio.run(report_service.add_report("Heavy clouds downtown", loc))


if __name__ == '__main__':
	configure()
	uvicorn.run(api, port=8000, host='127.0.0.1')
else:
	configure() # <- a production necessary thing
	# uvicorn main:api <- run server