build:
	terraform apply --target=module.backend.null_resource.jinja_layer_install --target=module.backend.null_resource.marshmallow_layer_install --target=module.frontend.null_resource.frontend_build --target=module.frontend.null_resource.nginx_docker_build

taint-layers:
	terraform taint module.backend.null_resource.jinja_layer_install
	terraform taint module.backend.null_resource.marshmallow_layer_install 
	
build-layers:
	terraform apply --target=module.backend.null_resource.jinja_layer_install --target=module.backend.null_resource.marshmallow_layer_install
