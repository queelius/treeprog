# Makefile

# Variables
TEX_FILE=$(basename $(INPUT)).tex
PDF_FILE=$(basename $(INPUT)).pdf

# Default target
all: $(PDF_FILE)

# Convert .ipynb to .tex
$(TEX_FILE): $(INPUT)
	jupyter nbconvert --to latex $(INPUT)

# Modify the .tex file to include fontspec and DejaVu Sans Mono
modify-tex: $(TEX_FILE)
	sed -i '/\\documentclass/a\\usepackage{fontspec}\\n\\setmonofont{DejaVu Sans Mono}' $(TEX_FILE)

# Compile .tex to .pdf using xelatex
$(PDF_FILE): modify-tex
	xelatex $(TEX_FILE)

# Clean up intermediate files
clean:
	rm -f *.aux *.log *.out *.tex

# Remove all generated files
distclean: clean
	rm -f $(PDF_FILE)

.PHONY: all clean distclean
