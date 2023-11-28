help:
	@echo "dev-server - start the frontend dev server"

dev-server:
	cd modules/frontend-ecr/frontend && npm run start

fmt:
	cd modules/backend-ecr && terraform fmt
	cd modules/backend && terraform fmt
	cd modules/okta-app && terraform fmt
	cd modules/okta-data && terraform fmt
	cd modules/frontend-ecr && terraform fmt
	cd modules/frontend-ecs-hosting && terraform fmt
	cd modules/utilities-account && terraform fmt
	cd modules/utilities-regional && terraform fmt
	cd example-app/infrastructure && terraform fmt
	cd example-app/backend-image && terraform fmt
	cd example-app/frontend-image && terraform fmt

backend-lint:
	cd modules/backend-ecr/quail-api/ && black .
	cd modules/backend-ecr/quail-api/ && flake8 .
