#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct 13 09:02:35 2019

@author: hyzhou

Convert papers into audio with format cleanup

Requires installation of packages: latex2rtf, striprtf

Usage example: "python Paper2Voice.py main.tex"
"""

import re, os, sys, tarfile, shutil, getopt
from striprtf.striprtf import rtf_to_text
import urllib.request as request
import gzip

def main():
    # latex version
    arxiv_id = str(sys.argv[1]) # zeroth argument is the current filename
    #fn = str(sys.argv[1][:-4])

    # add folder for outputs
    if not os.path.isdir('output'):
        os.mkdir('output')

    # default options
    rate = '200'
    include_si = False

    # get options
    try:
        opts, args = getopt.getopt(sys.argv[2:],"hr:",["rate=","si"])
    except getopt.GetoptError:
        print('python Paper2Voice.py <arXivID> -r <speech rate>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('Usage: python Paper2Voice.py <arXivID> -r <speech rate>')
            print('-r: a reasonable speech rate is 160, default is 200.')
            sys.exit()
        elif opt in ("-r", "--rate"):
            rate = arg
        elif opt in ("--si"):
            include_si = True

    # download files
    print('Loading files from arXiv:'+arxiv_id)
    url = 'https://arxiv.org/e-print/'+arxiv_id
    arxiv_id = arxiv_id.split('/')[-1] # only include last number
    print(os.getcwd()+'/'+arxiv_id+'.tar.gz')
    request.urlretrieve(url, os.getcwd()+'/'+arxiv_id+'.tar.gz')

    # extract files
    filetype = 0
    try:
        tar = tarfile.open(arxiv_id+'.tar.gz')
        tar.extractall(arxiv_id)
        tar.close()
    except: # not tar.gz format, likely due to it being a single file, try .gz
        try:
            filetype = 1
            os.rename(arxiv_id+'.tar.gz',arxiv_id+'.gz')
            f = gzip.open(arxiv_id+'.gz', 'rb')
            file_content = f.read().decode("cp437")
            file_content = file_content[file_content.find('documentclass')-1:]
            f.close()
            os.mkdir(arxiv_id)
            with open(arxiv_id+'/main.tex','w') as f:
                f.write(file_content)
        except:
            raise TypeError('File type from arXiv not supported! Likely direct pdf submission!')
        
    # extract main .tex file
    fn_list = [f for f in os.listdir(arxiv_id+'/') if f[-4:]=='.tex']
    fn_list.sort()
    print(fn_list)
    if len(fn_list)>1:
        fn0l = [f for f in fn_list if ('main' in f) or f=='paper.tex' or f=='maintext.tex' or f=='iclr2018_conference.tex' or f=='ms.tex' or f=='emnlp15.tex' or f=='tutorial.tex' or f=='errorcorrection.tex']
        if fn0l:
            fn0l = fn0l[0]
        else:
            fn0l = fn_list[0]
            for ii in range(len(fn_list)):
                with open(arxiv_id+'/'+fn_list[ii],'r',encoding="cp437") as f1:
                    text = f1.readlines()
                    text = ' '.join(text)
                    inputs = re.findall("begin\{document\}",text)
                    if not inputs:
                        continue
                    fn0l = fn_list[ii]
                    break
        print(fn0l)
        fn0 = fn0l[:-4]
    else:
        fn0 = fn_list[0][:-4]
    #fn0 = fn_list[0][:-4] # arxiv processes smallest file first
    fn = arxiv_id+'/'+fn0  
    # convert file to text, strip formating and delete reference section
    print('Processing file: '+fn)
    # replace \input lines with actual file
    with open(fn+'.tex','r+',encoding="cp437") as f:
        text = f.readlines()
        text = ' '.join(text)
        text = re.sub(r"%\\","%",text) # temporarily solution for commented \input lines
        text = re.sub(r"% \\","%",text) # commented input lines with a space
        #print(text)
    #    inputs = re.findall("\\\\subfile\{.+\}",text)
    #    #print(inputs)
    #    for i in range(len(inputs)):
    #        if not (re.search('bbl',inputs[i]) or re.search('tex',inputs[i])):  # make format uniform
    #            fninput = arxiv_id+'/'+inputs[i][9:-1]+'.tex'
    #        else:
    #            fninput = arxiv_id+'/'+inputs[i][9:-1]
    #        with open(fninput,'r') as f1:
    #            text1 = ''.join(f1.readlines())
    #            text = text.replace(inputs[i],text1)

        figure_blocks = re.findall("\\\\begin\{figure\}([\S\s]*?)\\\\end\{figure\}", text)#re.findall("\\\\begin\{figure\}.+\\\\end\{figure\}", text)

        for cFig in range(len(figure_blocks)):
            text = text.replace(figure_blocks[cFig], '')
        print(len(figure_blocks))
        figure_blocks = re.findall("\\\\begin\{figure\*\}([\S\s]*?)\\\\end\{figure\*\}", text)
        for cFig in range(len(figure_blocks)):
            text = text.replace(figure_blocks[cFig], '')

        inputs = re.findall("\\\\input\{.+\}",text)
        #print(inputs)
        for i in range(len(inputs)):
            if re.search('tikz',inputs[i]):
                continue
            if not (re.search('bbl',inputs[i]) or re.search('tex',inputs[i])):  # make format uniform
                fninput = arxiv_id+'/'+inputs[i][7:-1]+'.tex'
            else:
                fninput = arxiv_id+'/'+inputs[i][7:-1]
            with open(fninput,'r') as f1:
                text1 = ''.join(f1.readlines())
                text = text.replace(inputs[i],text1)
        # filter include commands
        inputs = re.findall("\\\\include\{.+\}",text)
        for i in range(len(inputs)):
            if not (re.search('bbl',inputs[i]) or re.search('tex',inputs[i])):  # make format uniform
                fninput = arxiv_id+'/'+inputs[i][9:-1]+'.tex'
            else:
                fninput = arxiv_id+'/'+inputs[i][9:-1]
            with open(fninput,'r') as f1:
                text1 = ''.join(f1.readlines())
                text = text.replace(inputs[i],text1)
        # sometimes inputs contain inputs...
        inputs = re.findall("\\\\input\{.+\}",text)
        #print(inputs)
        for i in range(len(inputs)):
            if re.search('tikz',inputs[i]):
                continue
            if not (re.search('bbl',inputs[i]) or re.search('tex',inputs[i])):  # make format uniform
                fninput = arxiv_id+'/'+inputs[i][7:-1]+'.tex'
            else:
                fninput = arxiv_id+'/'+inputs[i][7:-1]
            with open(fninput,'r') as f1:
                text1 = ''.join(f1.readlines())
                text = text.replace(inputs[i],text1)
        text = re.sub(r"\\citet\{.+?\}","",text)
        text = re.sub(r"\\citep\{.+?\}","",text)
        text = re.sub(r"\\cite\{.+?\}","",text)
        # replace all figures by just their captions
        #figblock = re.findall("\\begin\{figure\}.+\\end\{figure\}",text)
        # couldn't find a systematic fix for this easily
        text = text.replace("\\newcommand\\AND{\n    \\end{tabular}\\hfil\\linebreak[4]\\hfil\n    \\begin{tabular}[t]{c}\\ignorespaces\n}","")
    with open(fn+'.tex','w') as f:
        f.writelines(text)
    os.system('latex2rtf '+fn+'.tex')
    with open(fn+'.rtf','r') as f:
        text = f.readlines()
        text = rtf_to_text(' '.join(text))
        #print(text)
        text.replace('\n','').replace('\t','').replace('\xa0','')
        #text = re.sub(r'\[.*\]','',text)    
        # these are typically citations, but we have removed all citations now
        # this removes citations and SI
        if not include_si:
            ind = text.find('noop')
            text = text[0:ind]
            ind = text.find('ostop')
            text = text[0:ind]
        with open(fn+'.txt','w') as f2:
            f2.write(text)
            
    # convert into audio
    aiffmake='say -v Alex -r '+rate+' -o '+fn+'.aiff -f'+fn+'.txt'
    mp3make='/usr/local/bin/lame -h '+fn+'.aiff '+fn+'.mp3'
    os.system(aiffmake)
    os.system(mp3make)
    os.rename(fn+'.mp3','output/'+arxiv_id+'.mp3')
    if filetype:
        os.remove(arxiv_id+'.gz')
    else:
        os.remove(arxiv_id+'.tar.gz')
    shutil.rmtree(arxiv_id+'/')

if __name__ == "__main__":
    main()