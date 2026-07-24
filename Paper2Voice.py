#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct 13 09:02:35 2019

@author: hyzhou

Convert papers into audio with format cleanup

Requires installation of packages: latex2rtf, striprtf

Usage example: "python Paper2Voice.py main.tex"
"""

import re, os, sys, tarfile, shutil, getopt, zipfile
from striprtf.striprtf import rtf_to_text
import urllib.request as request
import gzip

# arXiv sources are almost always UTF-8; a minority of older submissions are
# latin-1. Decoding either of those as cp437 (as this script used to do) never
# raises but silently turns every non-ASCII byte into a different character,
# so an en-dash becomes 'ΓÇô' and 'Gehér' becomes 'Geh├⌐r'. latex2rtf carries
# the damage through to the .txt, and `say` then pronounces the Unicode name
# of each junk glyph — garbling the text and bloating the audio.
_TEX_ENCODINGS = ('utf-8', 'latin-1')

def read_tex(path):
    """Read a LaTeX source file, trying UTF-8 first then latin-1.

    latin-1 cannot fail, so this always returns a string without ever
    substituting replacement characters.
    """
    for enc in _TEX_ENCODINGS:
        try:
            with open(path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    # unreachable: latin-1 decodes any byte sequence
    raise UnicodeDecodeError('tex', b'', 0, 1, 'undecodable: '+path)

def write_tex(path, text):
    """Write LaTeX source back out as UTF-8, matching what latex2rtf expects."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

def main():
    # latex version
    arxiv_id = str(sys.argv[1]) # zeroth argument is the current filename
    #fn = str(sys.argv[1][:-4])

    # add folder for outputs
    if not os.path.isdir('output'):
        os.mkdir('output')

    # default options
    rate = '180'
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

    # If the input ends in .zip, treat it as a local source archive rather
    # than an arXiv ID — extract in place and reuse the rest of the pipeline.
    is_local_zip = arxiv_id.lower().endswith('.zip') and os.path.isfile(arxiv_id)
    filetype = 0
    if is_local_zip:
        local_zip_path = arxiv_id
        arxiv_id = os.path.splitext(os.path.basename(local_zip_path))[0]
        print('Extracting local archive: '+local_zip_path+' -> '+arxiv_id+'/')
        with zipfile.ZipFile(local_zip_path, 'r') as zf:
            zf.extractall(arxiv_id)
    else:
        # download files
        print('Loading files from arXiv:'+arxiv_id)
        url = 'https://arxiv.org/e-print/'+arxiv_id
        arxiv_id = arxiv_id.split('/')[-1] # only include last number
        print(os.getcwd()+'/'+arxiv_id+'.tar.gz')
        request.urlretrieve(url, os.getcwd()+'/'+arxiv_id+'.tar.gz')

        # extract files
        try:
            tar = tarfile.open(arxiv_id+'.tar.gz')
            tar.extractall(arxiv_id)
            tar.close()
        except: # not tar.gz format, likely due to it being a single file, try .gz
            try:
                filetype = 1
                os.rename(arxiv_id+'.tar.gz',arxiv_id+'.gz')
                f = gzip.open(arxiv_id+'.gz', 'rb')
                raw = f.read()
                f.close()
                for _enc in _TEX_ENCODINGS:
                    try:
                        file_content = raw.decode(_enc)
                        break
                    except UnicodeDecodeError:
                        continue
                file_content = file_content[file_content.find('documentclass')-1:]
                os.mkdir(arxiv_id)
                write_tex(arxiv_id+'/main.tex', file_content)
            except:
                raise TypeError('File type from arXiv not supported! Likely direct pdf submission!')
        
    # extract main .tex file - walk recursively so nested arXiv layouts work
    fn_list = []
    for root, _, files in os.walk(arxiv_id):
        for f in files:
            if f.endswith('.tex'):
                fn_list.append(os.path.relpath(os.path.join(root, f), arxiv_id))
    fn_list.sort()
    print(fn_list)
    if len(fn_list)>1:
        _main_names = ('paper.tex','maintext.tex','iclr2018_conference.tex','ms.tex','emnlp15.tex','tutorial.tex','errorcorrection.tex')
        fn0l = [f for f in fn_list if ('main' in os.path.basename(f)) or os.path.basename(f) in _main_names]
        if fn0l:
            fn0l = fn0l[0]
        else:
            fn0l = fn_list[0]
            for ii in range(len(fn_list)):
                text = read_tex(arxiv_id+'/'+fn_list[ii])
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
    text = read_tex(fn+'.tex')
    # Strip the backslash that follows a real comment '%' so subsequent
    # \input{} resolution skips commented-out includes. Use a negative
    # lookbehind so we don't touch an escaped percent (\%) — otherwise a
    # math-mode literal like \(95\%\) loses its closing backslash and
    # produces unbalanced \( … \), which makes latex2rtf give up partway
    # through the document and silently truncates the audio.
    text = re.sub(r"(?<!\\)%\\","%",text)
    text = re.sub(r"(?<!\\)% \\","%",text)
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
        if not (re.search('\.bbl',inputs[i]) or re.search('\.tex',inputs[i])):  # make format uniform
            fninput = arxiv_id+'/'+inputs[i][7:-1]+'.tex'
        else:
            fninput = arxiv_id+'/'+inputs[i][7:-1]
        text1 = read_tex(fninput)
        text = text.replace(inputs[i],text1)
    # filter include commands
    inputs = re.findall("\\\\include\{.+\}",text)
    for i in range(len(inputs)):
        if not (re.search('bbl',inputs[i]) or re.search('tex',inputs[i])):  # make format uniform
            fninput = arxiv_id+'/'+inputs[i][9:-1]+'.tex'
        else:
            fninput = arxiv_id+'/'+inputs[i][9:-1]
        text1 = read_tex(fninput)
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
        text1 = read_tex(fninput)
        text = text.replace(inputs[i],text1)
    # Re-strip figure blocks after \include/\input resolution, since
    # included sub-files (e.g. nested arXiv layouts) may contribute their
    # own \begin{figure}...\end{figure} blocks that the initial pass missed.
    for env in (r"figure", r"figure\*"):
        for block in re.findall(r"\\begin\{"+env+r"\}[\S\s]*?\\end\{"+env+r"\}", text):
            text = text.replace(block, '')
    text = re.sub(r"\\citet\{.+?\}","",text)
    text = re.sub(r"\\citep\{.+?\}","",text)
    text = re.sub(r"\\cite\{.+?\}","",text)
    # replace all figures by just their captions
    #figblock = re.findall("\\begin\{figure\}.+\\end\{figure\}",text)
    # couldn't find a systematic fix for this easily
    text = text.replace("\\newcommand\\AND{\n    \\end{tabular}\\hfil\\linebreak[4]\\hfil\n    \\begin{tabular}[t]{c}\\ignorespaces\n}","")

    # Strip the bibliography (and, when --si is off, the appendix/SI) from
    # the LaTeX source itself BEFORE handing it to latex2rtf. Doing this
    # at the source level is far more reliable than the old approach of
    # searching the RTF-converted text for the substrings 'noop'/'ostop',
    # which happened to appear in latex2rtf output for some old papers
    # but also falsely matches any paper whose body text contains those
    # substrings (e.g. quantum-computing papers that discuss the 'noop'
    # identity gate, or any author named 'Anoop').
    if not include_si:
        # remove \appendix ... \end{document} (keep the \end{document})
        text = re.sub(r"\\appendix[\s\S]*?(?=\\end\{document\})",
                      "", text)
    # always remove the bibliography itself
    text = re.sub(r"\\begin\{thebibliography\}[\s\S]*?\\end\{thebibliography\}",
                  "", text)
    text = re.sub(r"\\bibliography\{[^}]*\}", "", text)
    text = re.sub(r"\\bibliographystyle\{[^}]*\}", "", text)
    text = re.sub(r"\\addbibresource\{[^}]*\}", "", text)
    text = re.sub(r"\\printbibliography", "", text)
    write_tex(fn+'.tex', text)
    os.system('latex2rtf '+fn+'.tex')
    # latex2rtf emits UTF-8 when fed UTF-8; fall back for older sources.
    with open(fn+'.rtf','r',encoding='utf-8',errors='replace') as f:
        text = f.readlines()
        text = rtf_to_text(' '.join(text))
        #print(text)
        text = text.replace('\n',' ').replace('\t',' ').replace('\xa0',' ')
        #text = re.sub(r'\[.*\]','',text)
        # these are typically citations, but we have removed all citations now
        # Legacy belt-and-suspenders trim for latex2rtf artifacts that sometimes
        # appear AFTER the body when a bibliography slipped through. We only
        # honor these markers if they show up well past the start of the
        # document (i.e. somewhere plausibly near the end), so they can't
        # truncate a paper just because its body happens to contain 'noop'
        # or 'ostop' as a substring.
        if not include_si:
            min_marker_pos = max(2000, int(0.5 * len(text)))
            for marker in ('noopsort', '\\noopsort'):
                ind = text.find(marker, min_marker_pos)
                if ind != -1:
                    text = text[0:ind]
                    break
        # `say` reads UTF-8 correctly; writing it explicitly keeps the audio
        # free of the spoken glyph names that mangled text produces.
        with open(fn+'.txt','w',encoding='utf-8') as f2:
            f2.write(text)
            
    # convert into audio
    aiffmake='say -v Alex -r '+rate+' -o '+fn+'.aiff -f'+fn+'.txt'
    mp3make='/usr/local/bin/lame -h '+fn+'.aiff '+fn+'.mp3'
    os.system(aiffmake)
    os.system(mp3make)
    os.rename(fn+'.mp3','output/'+arxiv_id+'.mp3')
    if not is_local_zip:
        if filetype:
            os.remove(arxiv_id+'.gz')
        else:
            os.remove(arxiv_id+'.tar.gz')
    shutil.rmtree(arxiv_id+'/')

if __name__ == "__main__":
    main()