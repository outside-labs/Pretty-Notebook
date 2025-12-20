import re

import requests
from bs4 import BeautifulSoup

h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"}

"""
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
		sr = pr.text
		sr = sr.split('<!-- Footer Content -->')[0]
		sr = sr.split('<!-- Page Content -->')[1]

		soup = BeautifulSoup(sr, 'lxml')
		# print(sr.find_all('href'))
		for a in soup.find_all('a', href=True):
			for symb in ('.', ':'):
				if not symb in a['href']:
					print("Found rough local URL:", a['href'])
		# print(sr)
		

		# print(sr.get_text())
"""

r = requests.get("http://127.0.0.1:8000/blog-settings", headers=h)
sr = r.text.split('<!-- Footer Content -->')[0]
sr = sr.split('<!-- Page Content -->')[1]

print(sr)




