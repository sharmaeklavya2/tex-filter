#!/usr/bin/env python
"""Remove unneeded info from TeX's stdout."""

import sys
import re
import subprocess
import argparse
from collections import namedtuple


FILE_FORMATS = "sty|tex|cfg|def|clo|fd|mkii|pfb|enc|map|cls|otf|ldf|tikz|aux|out|bbl|ltx|sto|ttf|dict"
UNPREFIXED_STD_PATH_PATTERN = r'/texmf-(dist|var)/[a-zA-Z0-9\-_\/\.]+\.(' + FILE_FORMATS + ')'
LOCAL_PATH_PATTERN = r'./[a-zA-Z0-9\-_\/\.]+\.(' + FILE_FORMATS + ')'
PATH_STUB = '#'
PATH_STUB_PATTERN = r'\(#[\(#\) ]*\)'
PATH_STUB_PATTERN_2 = r'[\(#\) ]+'
VBOX_SUFFIX = r'has occurred while \\output is active'

BAD_STRS = tuple("""
 ABD: EveryShipout initializing macros
""".strip('\n').split('\n'))

BAD_PATTERNS = r"""
pdfTeX warning \(dest\): name{[^}]*} has been referenced but does not exist, replaced by a fixed one
warning  \(pdf backend\): unreferenced destination with name '[^']*'
 ?Excluding comment '[^']*'\.?
 ?Excluding '[^']*' comment\.?
\([A-Za-z0-9\-_/]+\.aux\)
\([A-Za-z0-9\-_/]+\.out\)
Library \(tcolorbox\): 'tcb[A-Za-z0-9]+\.code\.tex' version '[0-9\.]+'
""".strip('\n').split('\n')  # noqa

BAD_LINES = tuple("""
This is pdfTeX, Version
This is LuaHBTeX, Version
This is XeTeX, Version
restricted \\write18 enabled.
restricted system commands enabled.
LaTeX2e <
entering extended mode
L3 programming layer
Document Class:
For additional information on amsmath, use the `?' option.
Document Style algorithmicx 1.2 - a greatly improved `algorithmic' style
Document Style - pseudocode environments for use with the `algorithmicx' style
*geometry* driver: auto-detecting
*geometry* detected driver:
[Loading MPS to PDF converter
(see the transcript file for additional information)
Transcript written on
avail lists:
AED: lastpage setting LastPage
Package: textpos
Grid set
TextBlockOrigin set to
socg-lipics-v2019: fix
socg-lipics-v2019: subcaption
Package tocbibind Note: Using chapter style headings, unless overridden.
(natbib)                Rerun to get citations correct.
(rerunfilecheck)                Rerun to get outlines right
(rerunfilecheck)                or use package `bookmark'.
(rerunfilecheck)                Rerun to get bibliographical references right.
""".strip('\n').split('\n'))

CITEREF_PATTERN = (r"(LaTeX|Package natbib) Warning: (Citation|Reference|Hyper reference) `[^']+'"
    r"( on page \w+)? undefined on input line \d+.")
LATEX_FONT_WARN_1 = r"LaTeX Font Warning: Font shape `[\w\/]+' (undefined|in size <[0-9\.]+> not available)"  # noqa
LATEX_FONT_WARN_2 = r"\(Font\)\s+(size <[0-9\.]+> substituted|using `[\w\/]+' instead) on input line \d+."  # noqa

FILTERS = {
    'local_paths': (False, 'replace all local paths by a stub'),
    'std_paths': (True, 'replace paths of pre-installed fonts, packages, etc. by a stub'),
    'path_stubs': (True, 'remove path stubs'),
    'bad_lines': (True, 'remove lines whose prefix belongs to a blacklist'),
    'full_hbox_details': (True, 'remove details about overfull/underfull \\hbox warnings'),
    'ofull_hbox': (False, 'remove overfull \\hbox warnings'),
    'ufull_hbox': (False, 'remove underfull \\hbox warnings'),
    'ofull_vbox': (False, 'remove overfull \\vbox warnings'),
    'ufull_vbox': (False, 'remove underfull \\vbox warnings'),
    'bad_strs': (True, 'remove blacklisted substrings'),
    'page_numbers': (True, 'remove page-numbers'),
    'empty_lines': (True, 'remove empty lines'),
    'citeref': (False, 'remove warnings about missing citations/references'),
    'words_of_mem': (True, 'remove info about words of node memory still in use'),
    'font': (False, 'remove missing font warnings'),
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


LineState = namedtuple('LineState', ['full_hbox', 'words_of_mem'])


def fullmatch(pattern, string, flags=0):
    m = re.match(pattern, string, flags=flags)
    if m and m.end() == len(string):
        return m


def clean_file(ifp, ofp, std_path_prefix, filters):
    errcode = 0
    std_path_pattern = std_path_prefix + UNPREFIXED_STD_PATH_PATTERN
    prev_state = LineState(False, False)
    prev_is_empty = True
    for line in ifp:
        if line.startswith('! '):
            errcode = 1
        line = line.strip()
        has_ofull_hbox = line.startswith('Overfull \\hbox')
        has_ufull_hbox = line.startswith('Underfull \\hbox')
        words_of_mem = 'words of node memory still in use' in line
        state = LineState(has_ofull_hbox or has_ufull_hbox, words_of_mem)
        discard = ((filters['full_hbox_details'] and prev_state.full_hbox)
            or (filters['ofull_hbox'] and has_ofull_hbox)  # noqa
            or (filters['ufull_hbox'] and has_ufull_hbox)  # noqa
            or (filters['font'] and (fullmatch(LATEX_FONT_WARN_1, line)  # noqa
                or fullmatch(LATEX_FONT_WARN_2, line)))  # noqa
            or (filters['citeref'] and re.match(CITEREF_PATTERN, line))  # noqa
            or (filters['bad_lines'] and line.startswith(BAD_LINES))  # noqa
            or (filters['words_of_mem'] and (state.words_of_mem or prev_state.words_of_mem))  # noqa
            )
        if not discard:
            if filters['bad_strs']:
                for s in BAD_STRS:
                    line = line.replace(s, '')
                for s in BAD_PATTERNS:
                    line = re.sub(s, '', line)
            if filters['ofull_vbox']:
                line = re.sub(r'Overfull \\vbox \([0-9\.]+pt too high\) ' + VBOX_SUFFIX, '', line)
            if filters['ufull_vbox']:
                line = re.sub(r'Underfull \\vbox \(badness \d+\) ' + VBOX_SUFFIX, '', line)
            if filters['std_paths']:
                line = re.sub(std_path_pattern, PATH_STUB, line)
            if filters['local_paths']:
                line = re.sub(LOCAL_PATH_PATTERN, PATH_STUB, line)
            if filters['path_stubs']:
                line = re.sub(PATH_STUB_PATTERN, '', line)
                if fullmatch(PATH_STUB_PATTERN_2, line):
                    line = ''
                line = line.replace('<' + PATH_STUB + '>', '')
                line = line.replace('{' + PATH_STUB + '}', '')
            if filters['page_numbers']:
                line = re.sub(r'\s*\[[0-9\.]+\]', '', line)
            if filters['path_stubs']:
                if fullmatch(PATH_STUB_PATTERN_2, line):
                    line = ''
            if fullmatch(r'[\(\) ]+', line):
                line = ''
            line = line.strip()
            if not(line == '' and (filters['empty_lines'] or prev_is_empty)):
                ofp.write(line + '\n')
                ofp.flush()
            prev_is_empty = line == ''
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
