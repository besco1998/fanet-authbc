#!/usr/bin/env bash
# Builds both versions of the model report: report_supervisor.pdf and report_full.pdf.
# pdflatex, bibtex, pdflatex twice, per version (latexmk is not installed).
set -euo pipefail
cd "$(dirname "$0")"
build() {   # $1 jobname, $2 preamble definition
    pdflatex -interaction=nonstopmode -halt-on-error -jobname="$1" "$2\\input{report}" >/dev/null
    bibtex "$1" >/dev/null
    pdflatex -interaction=nonstopmode -halt-on-error -jobname="$1" "$2\\input{report}" >/dev/null
    pdflatex -interaction=nonstopmode -halt-on-error -jobname="$1" "$2\\input{report}" >/dev/null
    grep -E "undefined|Rerun to get|multiply defined" "$1.log" && return 1 || true
    grep -o "Output written on .* pages" "$1.log"   # pdfinfo is not installed
}
build report_supervisor ""
build report_full "\\def\\FULL{1}"
