
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
	docker-compose run --rm public-api-dev pytest

.PHONY: publish-ecr
publish-ecr: export INSTALL_PYTHON_VERSION=3.9
publish-ecr: export AWS_ACCOUNT=442249827373
publish-ecr: export AWS_REGION=eu-west-1
publish-ecr:
	docker build --build-arg INSTALL_PYTHON_VERSION --target production -t quail-public_api .
	docker tag quail-public_api:latest ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/quail-public_api:latest
	aws ecr get-login-password --region ${AWS_REGION} | \
        docker login --username AWS --password-stdin ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com
	docker push ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/quail-public_api:latest

.PHONY: ecs-shell
ecs-shell: export AWS_REGION=eu-west-1
ecs-shell: export AWS_ECS_CLUSTER=quail-Cluster
ecs-shell: export AWS_ECS_TASK_ID=7f58aeac68584a05a339583825c197e0
ecs-shell: export AWS_ECS_CONTAINER=quail-app
ecs-shell:
	aws ecs execute-command  \
		--region ${AWS_REGION} \
		--cluster ${AWS_ECS_CLUSTER} \
		--task ${AWS_ECS_TASK_ID} \
		--container ${AWS_ECS_CONTAINER} \
		--command "/bin/bash" \
		--interactive
