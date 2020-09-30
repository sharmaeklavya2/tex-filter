#!/usr/bin/env python
"""Remove unneeded info from TeX's stdout."""

import sys
import re
import subprocess
import argparse
from collections import namedtuple


FILE_FORMATS = "sty|tex|cfg|def|clo|fd|mkii|pfb|enc|map|cls"
UNPREFIXED_PATH_PATTERN = r'/texmf-(dist|var)/[a-zA-Z0-9\-\/\.]+\.(' + FILE_FORMATS + ')'
PATH_STUB = '#'
PATH_STUB_PATTERN = r'\(#[\(#\) ]*\)'

BAD_STRS = tuple("""
 Excluding comment 'comment'
Excluding 'comment' comment.
 ABD: EveryShipout initializing macros
""".strip('\n').split('\n'))

BAD_LINES = tuple("""
This is pdfTeX, Version
 restricted \\write18 enabled.
LaTeX2e <
entering extended mode
L3 programming layer
Document Class:
For additional information on amsmath, use the `?' option.
Document Style algorithmicx 1.2 - a greatly improved `algorithmic' style
Document Style - pseudocode environments for use with the `algorithmicx' style
*geometry* driver: auto-detecting
*geometry* detected driver: pdftex
[Loading MPS to PDF converter
(see the transcript file for additional information)
Transcript written on
""".strip('\n').split('\n'))

CITEREF_PATTERN = (r"LaTeX Warning: (Citation|Reference|Hyper reference) `[^']+'"
    r" on page \d+ undefined on input line \d+.\n")

FILTERS = {
    'paths': (True, 'replace paths of pre-installed fonts, packages, etc. by a stub'),
    'path_stubs': (True, 'remove path stubs'),
    'bad_lines': (True, 'remove lines whose prefix belongs to a blacklist'),
    'full_hbox_details': (True, 'remove details about overfull/underfull \\hbox warnings'),
    'full_hbox': (False, 'remove overfull/underfull \\hbox warnings'),
    'bad_strs': (True, 'remove blacklisted substrings'),
    'page_numbers': (True, 'remove page-numbers'),
    'empty_lines': (True, 'remove empty lines'),
    'citeref': (False, 'remove warnings about missing citations/references'),
}


def get_prefix():
    """
    Finds the directory containing TeX fonts, classes, packages, etc.
    It should look something like '/usr/local/texlive/2020' or '/usr/share/texlive'.
    """
    suffix = '/texmf-dist/fonts/type1/public/amsfonts/cm/cmr10.pfb'
    path = subprocess.check_output(['kpsewhich', 'cmr10.pfb'], universal_newlines=True).strip()
    if not path.endswith(suffix):
        raise ValueError("cmr10.pfb's path is non-standard")
    return path[:-len(suffix)]


LineState = namedtuple('LineState', ['full_hbox'])


def clean_file(ifp, ofp, path_prefix, filters):
    errcode = 0
    path_pattern = path_prefix + UNPREFIXED_PATH_PATTERN
    prev_state = LineState(False)
    for line in ifp:
        if line.startswith('! '):
            errcode = 1
        state = LineState(line.startswith('Overfull \\hbox')
            or line.startswith('Underfull \\hbox'))  # noqa
        discard = ((filters['full_hbox_details'] and prev_state.full_hbox)
            or (filters['full_hbox'] and state.full_hbox)  # noqa
            or (filters['citeref'] and re.match(CITEREF_PATTERN, line))  # noqa
            or (filters['bad_lines'] and line.startswith(BAD_LINES)))  # noqa
        if not discard:
            if filters['bad_strs']:
                for s in BAD_STRS:
                    line = line.replace(s, '')
            if filters['paths']:
                line = re.sub(path_pattern, PATH_STUB, line)
                if filters['path_stubs']:
                    line = re.sub(PATH_STUB_PATTERN, '', line)
                    line = line.replace('<' + PATH_STUB + '>', '')
                    line = line.replace('{' + PATH_STUB + '}', '')
            if filters['page_numbers']:
                line = re.sub(r'\s*\[[0-9]+\]', '', line)
            line = line.strip() + '\n'
            if not(filters['empty_lines'] and line == '\n'):
                ofp.write(line)
                ofp.flush()
        prev_state = state
    return errcode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name, (defval, help) in FILTERS.items():
        parser.add_argument('--' + name.replace('_', '-'), type=int, choices=(0, 1),
            default=defval, help=help + ' (default: {})'.format(int(defval)))
    parser.add_argument('--detect-error', type=int, choices=(0, 1), default=True,
        help='detect error messages and change exit status accordingly (default: 1)')
    args = parser.parse_args()

    prefix = get_prefix()
    filters = {name: bool(value) for name, value in vars(args).items()}
    errcode = clean_file(sys.stdin, sys.stdout, prefix, filters)
    if args.detect_error:
        sys.exit(errcode)


if __name__ == '__main__':
    main()
