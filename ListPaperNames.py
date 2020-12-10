'''
Check paper titles of listed arXiv numbers
hyzhou, 09/16/2020
'''

from bs4 import BeautifulSoup
import urllib.request as request
import os

file_names = sorted(os.listdir('output/'))

for file_name in file_names:
  if file_name[-4:] == '.mp3':
    print(file_name[:-4])
    with request.urlopen('https://arxiv.org/abs/'+file_name[:-4]) as response:
      html = response.read()
    soup = BeautifulSoup(html)
    title_html = str(soup.findAll("h1", {"class": "title mathjax"})[0])
    ind = title_html.find('</span')
    print(title_html[ind+7:-5])

