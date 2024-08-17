# Define the environment variables
ENV_VAR_1 := value1
ENV_VAR_2 := value2

# Define the Docker image name and tag
DOCKER_IMAGE := classification-service
DOCKER_TAG := latest

.PHONY: build

build:
	# Build the Docker image with environment variables as arguments
	docker build \
		--build-arg ENV_VAR_1=$(ENV_VAR_1) \
		--build-arg ENV_VAR_2=$(ENV_VAR_2) \
		-t $(DOCKER_IMAGE):$(DOCKER_TAG) .

