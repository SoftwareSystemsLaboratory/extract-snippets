#!/usr/bin/env python

import argparse
import os
import os.path
import sys
from collections import namedtuple
from itertools import takewhile, dropwhile

def get_argparser():
    parser = argparse.ArgumentParser(
            description="extract subset of lines from source file")

    # Global Parsing options (for all subcommands)

    parser.add_argument("--dir", type=str, help="base dir", default=".")
    parser.add_argument("--path", type=str, help="path relative to base dir", required=True)
    parser.add_argument("--latex-env", type=str, help="emit as latex with surrounding env")
    parser.add_argument("--dedent", type=int, help="number of characters to chop", default=0)
    parser.add_argument("--snip-prefix", type=str, help="prefix of output filename", default="snip")
    parser.add_argument("--snip-extension", type=str, help="prefix of output filename", default="tex")

    subparsers = parser.add_subparsers(help='available subcommands', dest='command')
    delimiters = subparsers.add_parser('delimiters', help='extract by simple start/end delimiter (literalinclude style)')
    delimiters.add_argument("--after-string", type=str, required=True, help="start after line containing string")
    delimiters.add_argument("--before-string", type=str, required=True, help="end before line containing string")

    # These are only processed if neither of the above are set.

    lines = subparsers.add_parser('lines', help='extract range of line numbers')
    lines.add_argument("--start-line", type=int, required=True, help="start after line containing string")
    lines.add_argument("--end-line", type=int, required=True, help="end before line containing string")


    # Controls stdout vs. filename

    parser.add_argument("--stdout", help="prefix of output filename", default=False, action="store_true")

    # snip name is required and should be a valid identifier

    parser.add_argument("--name", help="name for snippet (should be unique if generating many snippets)", type=str)

    return parser


def main():
    arg_parser = get_argparser()
    args = arg_parser.parse_args()

    commands = { 
        'delimiters' : extract_delimiters_simple,
        'lines' : extract_line_range
    }

    extract = commands.get(args.command, None)
    if not extract:
        print("No subcommand specified. No processing done.")
        return

    full_path = os.path.join(args.dir, args.path)
    snip_filename = get_filename(args, extract)

    with open(full_path, "r") as infile:
       extracted = extract(args, infile)
       if args.stdout:
          render(args, extracted, sys.stdout)
       else:
          with open(snip_filename, "w") as outfile:
             render(args, extracted, outfile)

def get_filename(args, extract_method):
    path_components = [args.snip_prefix] + args.path.split("/")
    if args.name:
       path_components.append(args.name)
    base_filename = "-".join(path_components)

    # TODO: Temporary strategy for LaTeX \input
    # Generalize to translate only to proper alphanumeric id's.

    base_filename = base_filename.replace("_","-")
    base_filename = base_filename.replace(".","-")
    base_filename = base_filename.replace(":","-")

    if not args.name:
       return ".".join([base_filename, args.snip_extension])
    else:
       return ".".join([base_filename, args.snip_extension])

    
def render(args, extracted, outfile):
    outfile.write(get_header(args) + "\n")
    for line in extracted:
        outfile.write(line[args.dedent:] + '\n')
    outfile.write(render_footer(args) + "\n")

def get_header(args):
    if args.latex_env:
        return r"\begin{%s}" % args.latex_env

def render_footer(args):
    if args.latex_env:
        return r"\end{%s}" % args.latex_env

def find_wrapper(text, ss):
    pos = text.find(ss)
    return pos

def extract_delimiters_simple(args, infile):
    # remove trailing whitespace
    data = map(lambda line : line.rstrip(), infile)
    # drop everything up to start string
    rest = dropwhile(lambda text : text.find(args.after_string) < 0, data)
    next(rest)

    # take everything up to string
    extracted = takewhile(lambda text : find_wrapper(text, args.before_string) < 0, rest)
    return extracted

# Create a tuple-like record class

LineInfo = namedtuple("LineInfo", "number text")

def numbered_reader(infile):
    line_no=1
    for line in infile:
        yield LineInfo(number=line_no, text=line.rstrip())
        line_no += 1

def extract_line_range(args, infile):
    reader = numbered_reader(infile)
    # drop everything up to start string
    rest = dropwhile(lambda line_info : line_info.number < args.start_line, reader)
    # take everything up to string
    extracted = takewhile(lambda line_info : line_info.number < args.end_line, rest)
    
    remove_line_numbers = map(lambda line_info : line_info.text, extracted)
    return remove_line_numbers

if __name__ == '__main__':
    main()
