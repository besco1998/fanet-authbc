# Rebuild the running results summary. Invoked by `make summary` from the repo root.
results_summary.pdf: results_summary.tex
	pdflatex -interaction=nonstopmode results_summary.tex >/dev/null
	pdflatex -interaction=nonstopmode results_summary.tex >/dev/null
	@echo "summary/results_summary.pdf rebuilt"
clean:
	rm -f *.aux *.log *.out *.toc b*.log
