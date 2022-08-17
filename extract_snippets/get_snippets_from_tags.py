#!/usr/bin/env python3
# coding: utf-8

import argparse
import os
import os.path
import sys
from collections import namedtuple
from itertools import groupby, takewhile, dropwhile
import re
import json

TAG_REGEX = r"""{{
(?P<book>\w+):
(?P<tag>[\w'-]+):
(?P<marker>(begin|end))
}}""".replace("\n","")

def get_argparser():
   parser = argparse.ArgumentParser(description="find tags for snippets for our book")
   parser.add_argument("--dir", type=str, help="base dir", default=".")
   parser.add_argument("--outdir", type=str, help="output dir for snippets json info", default=".")
   parser.add_argument("--extensions", type=str, help="filename extensions (comma sep) to consider [c,h,cc,hh,cpp,py]", default="c,h,cc,hh,cpp,py")
   parser.add_argument("--literalinclude", action="store_true", help="emit literalinclude fragments for .rst usage", default=False)
   parser.add_argument("--minted", action="store_true", help="emit minted fragments for .tex usage", default=False)
   parser.add_argument("--json",  action="store_true", help="emit JSON fragments for arbitrary post-processing/debugging", default=False)
   return parser

def get_snip_regex():
   return re.compile(TAG_REGEX)


def depathify(path):
    # remove any relative paths from output name
    s = path.replace("../","")
    s = s.replace("./","")
    # remove underscore
    s = s.replace("_","-")
    # replace slashes with hyphens
    s = s.replace("/","-")
    return s

def write_json(outdir, root, basename, data):
    unique_basename = depathify(os.path.join(root,basename))
    json_filename = unique_basename + '.json'
    print(f"Writing output to {json_filename}")
    path = os.path.join(outdir, json_filename)
    with open(path, "w") as outfile:
        outfile.write(json.dumps(data, indent=2))

LineInfo = namedtuple("LineInfo", "number text")

def line_reader(file):
    line_no = 1
    for line in file:
        yield LineInfo(number=line_no, text=line)
        line_no += 1

def process_dir(args):
   basedir = args.dir
   extensions = set(["."+extension for extension in args.extensions.split(",")])
   outdir = args.outdir
   snip_regex = get_snip_regex()
   if not os.path.exists(outdir):
      print(f"Outdir {outdir} must exist (exiting)")
      return

   for root, dirs, files in os.walk(basedir, topdown=False):
      for name in files:
         (nameonly,extension) = os.path.splitext(name)
         if extension in extensions:
            snips = process_file(root, name, extension, snip_regex)
            if args.json and len(snips) > 0:
               write_json(outdir, root, name, snips)
            if args.minted:
               write_minted_snippets(args, snips)

      #for name in dirs:
      #   print(os.path.join(root, name))

def process_file(root, name, extension, snip_regex):
    path = os.path.join(root, name)
    results = []
    with open(path, "r") as file:
        reader = line_reader(file)
        for line_info in reader:
            result = snip_regex.search(line_info.text)
            if result:
                re_dict = result.groupdict()
                doc = { 'path' : path,
                        'root' : root,
                        'name' : name,
                        'language' : extension[1:],
                        'line' : line_info.number+1,
                        'text' : line_info.text,
                        'match_text' : line_info.text[result.start():result.end()],
                        'match_start' : result.start(),
                        'match_end' : result.end(),
                        'fq_tag' : line_info.text[result.start()+2:result.end()-2]
                      }
                doc.update(re_dict)
                results.append(doc)

    groups = {}
    for group in groupby(results, lambda d : d['tag']):
       group_name = group[0]
       group_values = list(group[1])
       group_values.sort(key=lambda d : d['line'])
       markers_found = map(lambda d : d['marker'], group_values)
       markers = set(list(markers_found))
       if len(markers) != 2:
           print("Tag %(group_name)s has mismatched or missing begin/end marker" % vars())
           continue
       groups[group_name] = group_values
    return groups

def find_wrapper(text, ss):
    pos = text.find(ss)
    return pos

def extract_delimiters_simple(infile, after_string, before_string):
    # remove trailing whitespace
    data = map(lambda line : line.rstrip(), infile)

    # remove leading blank lines (as it messes up line numbers)
    data2 = dropwhile(lambda text : len(text) == 0, data)

    # drop everything up to start string
    rest = dropwhile(lambda text : text.find(after_string) < 0, data2)
    next(rest)

    # take everything up to string
    extracted = takewhile(lambda text : find_wrapper(text, before_string) < 0, rest)
    return extracted

def get_minted_env(extension):
    # Generalize this later.
    envs = {
            'c' : 'ccode',
            'cc' : 'cppcode',
            'cpp' : 'cppcode',
            'c++' : 'cppcode',
            'py' : 'pycode',
            'h' : 'ccode',
            'hh' : 'ccode',
            }
    return envs.get(extension, "unknownlanguage") + '*'

def write_minted_snippets(args, groups):
    for group in groups:
        (begin, end) = groups[group][:2]  # begin and end info in a pair of dictionaries
        if begin['marker'] != 'begin' or end['marker'] != 'end':
            print(f"Invalid group {group}")
            continue
        book = begin['book']
        tag = begin['tag']
        tag = tag.replace('_','-')  # underscores not in filename for LaTeX \input
        snip_filename = os.path.join(args.outdir, f"snip-{book}-{tag}.tex")
        with open(begin['path']) as infile:
            extracted = extract_delimiters_simple(infile, begin['match_text'],
                    end['match_text'])
            with open(snip_filename, "w") as outfile:
               minted_env = get_minted_env(begin['language'])
               outfile.write("\\begin{%s}{firstnumber=%d}\n" % (minted_env,
                   begin['line']))
               outfile.write('\n'.join(list(extracted)) + '\n')
               outfile.write("\\end{%s}\n" % minted_env)

def main():
    args = get_argparser().parse_args()
    process_dir(args)

if __name__ == '__main__':
    main()

