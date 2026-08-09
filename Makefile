EXAMPLE_INTERLINKS=quartodoc/tests/example_interlinks

# These 2 rules are used to generate the example_interlinks folder,
# which contains a full example for the interlinks filter to be tested

$(EXAMPLE_INTERLINKS): scripts/filter-spec/generate_files.py
	uv run python $<

$(EXAMPLE_INTERLINKS)/test.qmd: scripts/filter-spec/generate_test_qmd.py
	uv run python $<

$(EXAMPLE_INTERLINKS)/test.md: $(EXAMPLE_INTERLINKS)/test.qmd _extensions/interlinks/interlinks.lua
	cd $(EXAMPLE_INTERLINKS) && quarto render test.qmd --to gfm



docs-build: export PLUM_SIMPLE_DOC=1
docs-build:
	cd docs && uv run quartodoc build --verbose
	cd docs && uv run quartodoc interlinks
	cd docs && quarto add --no-prompt ..
	uv run quarto render docs

test-overview-template:
	uv run python scripts/build_tmp_starter.py

test-interlinks: quartodoc/tests/example_interlinks/test.md
