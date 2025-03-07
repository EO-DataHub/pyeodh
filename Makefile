record := none

.PHONY: install
install:
	ln -s $(PWD)/.pre-commit .git/hooks/pre-commit
	poetry install --all-extras

.PHONY: sync
sync:
	poetry sync

.PHONY: check
check:
	poetry run black --preview --check pyeodh tests
	poetry run flake8 pyeodh tests
	poetry run isort --check --diff pyeodh tests
	poetry run pyright

.PHONY: test
test:
	poetry run pytest -v --cov=./ --cov-report=xml --record-mode=$(record)

.PHONY: html
html:
	cd docs && \
	poetry run make html SPHINXOPTS="-W"

.PHONY: format
format:
	poetry run black pyeodh tests
	poetry run isort pyeodh tests
