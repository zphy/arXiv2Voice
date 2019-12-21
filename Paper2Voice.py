#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct 13 09:02:35 2019

@author: hyzhou

Convert papers into audio with format cleanup

Requires installation of packages: latex2rtf, striprtf

Usage example: "python Paper2Voice.py main.tex"
"""


### PDF version
#import PyPDF2
#
#fn = 'arXiv2019_ElseDumitrescu_QuasiPeriodicHeating.pdf'
#pdfFileObj = open(fn,'rb')
#pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
#num_pages = pdfReader.numPages
#count = 0
#text = ""
#while count < num_pages:
#    pageObj = pdfReader.getPage(count)
#    count +=1
#    text += pageObj.extractText()
#if text != "":
#   text = text
#print(text)

import re, os, sys, tarfile, shutil
from striprtf.striprtf import rtf_to_text
import urllib.request as request

# latex version
arxiv_id = str(sys.argv[1]) # zeroth argument is the current filename
#fn = str(sys.argv[1][:-4])

# download files
print('Loading files from arXiv:'+arxiv_id)
url = 'https://arxiv.org/e-print/'+arxiv_id
print(os.getcwd()+'/'+arxiv_id+'.tar.gz')
request.urlretrieve(url, os.getcwd()+'/'+arxiv_id+'.tar.gz')

# extract files
tar = tarfile.open(arxiv_id+'.tar.gz')
tar.extractall(arxiv_id)
tar.close()

# extract .tex file
fn_list = [f for f in os.listdir(arxiv_id+'/') if f[-4:]=='.tex']
fn_list.sort()
print(fn_list)
#if len(fn_list)>1:
#    fn0 = [f for f in fn_list if f=='main.tex' or f=='paper.tex' or f=='maintext.tex'][0][:-4]
#else:
#    fn0 = fn_list[0][:-4]
fn0 = fn_list[0][:-4] # arxiv processes smallest file first
fn = arxiv_id+'/'+fn0  
# convert file to text, strip formating and delete reference section
print('Processing file: '+fn)
os.system('latex2rtf '+fn+'.tex')
with open(fn+'.rtf','r') as f:
    text = f.readlines()
    text = rtf_to_text(''.join(text))
    text.replace('\n','').replace('\t','').replace('\xa0','')
    text = re.sub(r'\[.*\]','',text)
    ind = text.find('noop')
    text = text[0:ind]
    ind = text.find('ostop')
    text = text[0:ind]
    with open(fn+'.txt','w') as f2:
        f2.write(text)
        
# convert into audio
aiffmake='say -v Alex -r 200 -o '+fn+'.aiff -f'+fn+'.txt'
mp3make='/usr/local/bin/lame -h '+fn+'.aiff '+fn+'.mp3'
os.system(aiffmake)
os.system(mp3make)
os.rename(fn+'.mp3','output/'+arxiv_id+'.mp3')
os.remove(arxiv_id+'.tar.gz')
shutil.rmtree(arxiv_id+'/')

