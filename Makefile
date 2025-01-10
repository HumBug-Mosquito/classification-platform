
.PHONY: up dev stop remove

up:
	docker builder prune -f && docker compose up -d

dev: 
	EVENT_DETECTOR_MODEL_PATH=lib/med/model_presentation_draft_2022_04_07_11_52_08.pth SPECIES_CLASSIFIER_MODEL_PATH=lib/msc/model_e186_2022_10_11_11_18_50.pth CLASSIFICATION_OUTPUT_DIR=./output uvicorn services.live.live-service:app --host 0.0.0.0 --port 8002

down:
	docker ps -a --filter "label=com.docker.compose.project=$(TAG)" -q | xargs -r docker stop

stop: 
	docker ps -a -q | xargs -r docker stop
	
reset:
	docker ps -a -q | xargs -r docker stop
	docker ps -a -q | xargs -r docker rm
	docker images -q | xargs -r docker rmi -f


