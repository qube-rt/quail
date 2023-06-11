help:
	@echo "dev-server - start the frontend dev server"

dev-server:
	cd modules/frontend/frontend && npm run start

clean:
	rm -rf modules/frontend/frontend/build

fmt:
	cd modules/backend && terraform fmt
	cd modules/okta-app && terraform fmt
	cd modules/okta-data && terraform fmt
	cd modules/frontend && terraform fmt
	cd modules/frontend-ecs-hosting && terraform fmt
	cd modules/utilities-global && terraform fmt
	cd modules/utilities-regional && terraform fmt

backend-lint:
	cd modules/backend/lambda-src/ && black .
	cd modules/backend/lambda-src/ && flake8 .
