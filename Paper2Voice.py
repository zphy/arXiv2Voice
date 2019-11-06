#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct 13 09:02:35 2019

@author: hyzhou

Convert papers into audio with format cleanup

Requires installation of packages: latex2rtf, striprtf

Usage example: "python Paper2Voice.py main.tex"
"""

'''
# PDF version
import PyPDF2

fn = 'arXiv2019_ElseDumitrescu_QuasiPeriodicHeating.pdf'
pdfFileObj = open(fn,'rb')
pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
num_pages = pdfReader.numPages
count = 0
text = ""
while count < num_pages:
    pageObj = pdfReader.getPage(count)
    count +=1
    text += pageObj.extractText()
if text != "":
   text = text
print(text)
'''
import re, os, sys
from striprtf.striprtf import rtf_to_text

# latex2rtf, then remove \n, \t, \xa0, then find first noop
# latex version
#fn = 'Zhuang_displacement_hypothesis_theory_ZZ'
fn = str(sys.argv[1][:-4])#'Zhuang_displacement_hypothesis_theory_ZZ'
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
aiffmake='say -v Alex -r 200 -o '+fn+'.aiff -f'+fn+'.txt'
mp3make='/usr/local/bin/lame -h '+fn+'.aiff '+fn+'.mp3'
os.system(aiffmake)
os.system(mp3make)
os.remove(fn+'.aiff')
os.remove(fn+'.txt')
#print(re.match(r'\[.*\]','[151vs]'))
