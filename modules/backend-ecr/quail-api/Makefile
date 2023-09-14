
.PHONY: clean
clean:
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' | xargs rm -rf
	@find . -type d -name '*.ropeproject' | xargs rm -rf
	@find . -type d -name 'build' | xargs rm -rf
	@rm -rf dist/
	@rm -f src/*.egg
	@rm -f src/*.eggs
	@rm -rf src/*.egg-info/
	@rm -f MANIFEST
	@rm -rf docs/build/
	@rm -rf htmlcov/
	@rm -f .coverage
	@rm -f .coverage.*
	@rm -rf .cache/
	@rm -f coverage.xml
	@rm -f *.cover
	@rm -rf .pytest_cache/

.PHONY: setup-precommit
setup-precommit:
	pip install pre-commit && pre-commit install

.PHONY: shell
shell:
	docker-compose run --rm public-api-dev bash

.PHONY: shell-root
shell-root:
	docker-compose run --rm -user root public-api-dev bash

.PHONY: test
test:
	docker-compose -f docker-compose.test.yml build test-api-dev
	docker-compose -f docker-compose.test.yml run --rm test-api-dev pytest -s
