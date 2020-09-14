# TeX-filter

Tired of `pdftex` (or `pdflatex`) choking your stdout with what is apparently garbage?
Finding it difficult to spot errors/warnings among screenfuls of log messages by `pdftex`?
TeX-filter is here to help!

Just replace

    pdftex file.tex

with

    pdftex -halt-on-error -cnf-line "max_print_line = 100000" file.tex | ./tex-filter.py

TeX-filter works by applying many filters to the input.
You can control the set of filters to apply using command-line options.
See `./tex-filter.py --help` for details.

If you hate running long commands, add this to your `bashrc`/`bash_profile`:

    alias mypdflatex='pdflatex -cnf-line "max_print_line = 10000" -halt-on-error'

Then you can simply run `mypdflatex file.tex | ./tex-filter.py`.

You can also use `-interaction=nonstopmode` instead of `-halt-on-error`.

TeX-filter requires python 2 or 3.
