record := none

install:
	poetry install
check:
	poetry run black --preview --check pyeodh tests
	poetry run flake8 pyeodh tests
	poetry run isort --check --diff pyeodh tests
	poetry run pyright
test:
	poetry run pytest -v --cov=./ --record-mode=$(record)
html:
	cd docs && \
	poetry run make html SPHINXOPTS="-W"