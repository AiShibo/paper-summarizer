.PHONY: check test validate-fixtures validate-data java-test manifest build-db site-coverage-data site-data abstracts war serve

PYTHON ?= python3
PYTHONPATH := src

check: test validate-fixtures validate-data java-test

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

validate-fixtures:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m systems_phd_explorer.cli validate \
		--root tests/fixtures/shards --profile release

validate-data:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m systems_phd_explorer.cli validate \
		--root data/shards --profile draft

# JUnit tests for the Java/JSP explorer. ./mvnw bootstraps a JDK and Maven
# into .tools/ when they are not installed.
java-test:
	./mvnw -B -q test

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

# Fetches published abstracts into data/shards/**/metadata.json. Resumable;
# papers that already have an abstract are skipped. Set MAILTO for the APIs'
# polite pools.
abstracts:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m systems_phd_explorer.cli collect-abstracts \
		--root data/shards $(if $(MAILTO),--mailto $(MAILTO),)

# Packages target/systems-phd-explorer.war with the freshly generated export.
war: site-data
	./mvnw -B -q package

# Generates the export, builds the WAR, and serves it at http://localhost:8080.
serve: war
	scripts/run-tomcat.sh
