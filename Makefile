ASCIIDOCTOR ?= asciidoctor
OUTDIR      := _site
DOCDIR      := documentation

CONTAINER_ENGINE ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)
IMAGE_NAME       := forklift-docs-builder

ATTRS_UPSTREAM   := -a upstream -a build=upstream -a docinfodir=$(CURDIR)/$(DOCDIR) -a docinfo=shared
ATTRS_DOWNSTREAM := -a build=downstream -a docinfodir=$(CURDIR)/$(DOCDIR) -a docinfo=shared

GUIDES := $(DOCDIR)/doc-Planning_your_migration/master.adoc \
          $(DOCDIR)/doc-Migrating_your_virtual_machines/master.adoc \
          $(DOCDIR)/doc-Release_notes/master.adoc

.DEFAULT_GOAL := help
.PHONY: help build serve build-local serve-local image clean

## help: Show this help message
help:
	@printf '\nUsage: make \033[36m<target>\033[0m\n\n'
	@awk '/^## /{desc=$$0; sub(/^## [a-zA-Z_-]+: /,"",desc)} /^[a-zA-Z_-]+:/{if(desc){printf "  \033[36m%-15s\033[0m %s\n",$$1,desc; desc=""}}' $(MAKEFILE_LIST)
	@echo

# --- Container targets (recommended) ---

## image: Build the container image
image:
	$(CONTAINER_ENGINE) build -t $(IMAGE_NAME) .

## build: Build docs in a container (recommended)
build: image
	$(CONTAINER_ENGINE) run --rm -v $(CURDIR):/docs:Z $(IMAGE_NAME) make build-local

## serve: Build and serve docs in a container at localhost:8000
serve: image
	$(CONTAINER_ENGINE) run --rm -v $(CURDIR):/docs:Z -p 8000:8000 $(IMAGE_NAME) make serve-local

# --- Local targets (require Ruby, Asciidoctor, Node.js, Python 3) ---

## build-local: Build docs locally (requires Ruby, Asciidoctor, Node.js)
# Builds both upstream (Forklift) and downstream (MTV) into _site/upstream/ and
# _site/downstream/, with a root switcher page at _site/index.html.
build-local:
# --- upstream (Forklift) ---
	@mkdir -p $(OUTDIR)/upstream/$(DOCDIR)
	@for guide in $(GUIDES); do \
		outfile=$(OUTDIR)/upstream/$$(echo $$guide | sed 's/\.adoc$$/.html/'); \
		mkdir -p $$(dirname $$outfile); \
		$(ASCIIDOCTOR) -b html5 -d book --safe-mode unsafe $(ATTRS_UPSTREAM) \
			-o $(CURDIR)/$$outfile $$guide; \
	done
	cp $(DOCDIR)/index.html $(OUTDIR)/upstream/$(DOCDIR)/index.html
	@mkdir -p $(OUTDIR)/upstream/assets/img
	cp -r assets/img/* $(OUTDIR)/upstream/assets/img/ 2>/dev/null || true
	@echo '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0;url=documentation/index.html"></head></html>' > $(OUTDIR)/upstream/index.html
	npx -y pagefind --site $(OUTDIR)/upstream --root-selector "#content" --output-subdir _pagefind
# --- downstream (MTV) ---
	@mkdir -p $(OUTDIR)/downstream/$(DOCDIR)
	@for guide in $(GUIDES); do \
		outfile=$(OUTDIR)/downstream/$$(echo $$guide | sed 's/\.adoc$$/.html/'); \
		mkdir -p $$(dirname $$outfile); \
		$(ASCIIDOCTOR) -b html5 -d book --safe-mode unsafe $(ATTRS_DOWNSTREAM) \
			-o $(CURDIR)/$$outfile $$guide; \
	done
	cp $(DOCDIR)/index-downstream.html $(OUTDIR)/downstream/$(DOCDIR)/index.html
	@mkdir -p $(OUTDIR)/downstream/assets/img
	cp -r assets/img/* $(OUTDIR)/downstream/assets/img/ 2>/dev/null || true
	@echo '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0;url=documentation/index.html"></head></html>' > $(OUTDIR)/downstream/index.html
	npx -y pagefind --site $(OUTDIR)/downstream --root-selector "#content" --output-subdir _pagefind
# --- root switcher page ---
	cp $(DOCDIR)/index-both.html $(OUTDIR)/index.html

## serve-local: Build and serve docs locally at localhost:8000
serve-local: build-local
	@echo "Serving at http://localhost:8000"
	@cd $(OUTDIR) && python3 -m http.server 8000

## clean: Remove the build output directory
clean:
	rm -rf $(OUTDIR)
