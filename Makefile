.PHONY: check test validate-fixtures validate-data manifest build-db site-coverage-data site-data serve

PYTHON ?= python3
PYTHONPATH := src

check: test validate-fixtures validate-data

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

validate-fixtures:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m systems_phd_explorer.cli validate \
		--root tests/fixtures/shards --profile release

validate-data:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m systems_phd_explorer.cli validate \
		--root data/shards --profile draft

manifest:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m systems_phd_explorer.cli build-manifest \
		--root data/shards --output data/venue-year-manifest.generated.json

build-db:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m systems_phd_explorer.cli build-db \
		--root data/shards --output data/database.sqlite

site-coverage-data:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m systems_phd_explorer.cli build-manifest \
		--root data/shards --output site/data/venue-years.json

site-data: site-coverage-data
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m systems_phd_explorer.cli build-site-data \
		--root data/shards --output site/data/papers.json

serve:
	$(PYTHON) -m http.server 8000 --directory site
