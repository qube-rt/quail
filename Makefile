help:
	@echo "dev-server - start the frontend dev server"

dev-server:
	cd modules/frontend/frontend && npm run start

clean:
	rm -rf modules/backend/build
	rm -rf modules/backend/lambda-layers/jinja
	rm -rf modules/backend/lambda-layers/marshmallow
	rm -rf modules/frontend/frontend/build

fmt:
	cd modules/backend && terraform fmt
	cd modules/frontend && terraform fmt
	cd modules/frontend-ecs-hosting && terraform fmt
	cd modules/utilities-global && terraform fmt
	cd modules/utilities-regional && terraform fmt

backend-setup:
	pip install -r modules/backend/lambda-layers/jinja-requirements.txt \
		-r modules/backend/lambda-layers/marshmallow-requirements.txt \
		-r modules/backend/lambda-src/tests/requirements.txt

backend-lint:
	cd modules/backend/lambda-src/ && black .
	cd modules/backend/lambda-src/ && flake8 .
