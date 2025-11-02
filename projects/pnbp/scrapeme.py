import re

import requests

from bs4 import BeautifulSoup

# from models import ObsidianNotebook
# nb = ObsidianNotebook()

h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"}
r = requests.get("http://127.0.0.1:8000/all-public", headers=h)
# print(r)
# print(r.text)

s = BeautifulSoup(r.text, 'lxml')
ls = [p.get('href') for p in s.find_all('a')]

for l in ls:
	if not l in ('', '#', '/') and not re.match(r'^https?:', l):
		pr = requests.get(f"http://127.0.0.1:8000{l}", headers=h)
		# print(l)
		# print(pr.text)
		sr = BeautifulSoup(pr.text, 'lxml')
		print(sr.get_text())



