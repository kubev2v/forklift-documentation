ASCIIDOCTOR ?= asciidoctor
OUTDIR      := _site
DOCDIR      := documentation

CONTAINER_ENGINE ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)
IMAGE_NAME       := forklift-docs-builder

ATTRS := -a upstream -a build=upstream -a docinfodir=$(CURDIR)/$(DOCDIR) -a docinfo=shared

GUIDES := $(DOCDIR)/doc-Planning_your_migration/master.adoc \
          $(DOCDIR)/doc-Migrating_your_virtual_machines/master.adoc \
          $(DOCDIR)/doc-Release_notes/master.adoc

HTML_OUT := $(patsubst $(DOCDIR)/%.adoc,$(OUTDIR)/$(DOCDIR)/%.html,$(GUIDES))

.PHONY: build serve build-local serve-local image clean search copy-assets

# --- Container targets (recommended) ---

image:
	$(CONTAINER_ENGINE) build -t $(IMAGE_NAME) .

build: image
	$(CONTAINER_ENGINE) run --rm -v $(CURDIR):/docs:Z $(IMAGE_NAME) make build-local

serve: image
	$(CONTAINER_ENGINE) run --rm -v $(CURDIR):/docs:Z -p 8000:8000 $(IMAGE_NAME) make serve-local

# --- Local targets (require Ruby, Asciidoctor, Node.js, Python 3) ---

build-local: $(HTML_OUT) copy-assets search

$(OUTDIR)/$(DOCDIR)/%.html: $(DOCDIR)/%.adoc
	@mkdir -p $(dir $@)
	$(ASCIIDOCTOR) -b html5 -d book --safe-mode unsafe $(ATTRS) -o $(CURDIR)/$@ $<

copy-assets:
	@mkdir -p $(OUTDIR)/$(DOCDIR)
	cp $(DOCDIR)/index.html $(OUTDIR)/$(DOCDIR)/index.html
	@mkdir -p $(OUTDIR)/assets/img
	cp -r assets/img/* $(OUTDIR)/assets/img/ 2>/dev/null || true
	@echo '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0;url=documentation/index.html"></head></html>' > $(OUTDIR)/index.html

search:
	npx -y pagefind --site $(OUTDIR) --root-selector "#content" --output-subdir _pagefind

serve-local: build-local
	@echo "Serving at http://localhost:8000"
	@cd $(OUTDIR) && python3 -m http.server 8000

clean:
	rm -rf $(OUTDIR)
