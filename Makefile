# Define the environment variables
DATABASE_URL := localhost
LOGS_DIR := /Users/joshuaeverett/desktop/classification-service/logs/ 
CLASSIFICATION_OUTPUT_DIR=/Users/joshuaeverett/desktop/classification-service/results/
DASHBOARD_WORKERS := 1
DASHBOARD_PORT := 8000
SPECIES_CLASSIFIER_MODEL_PATH := lib/msc/model_e186_2022_10_11_11_18_50.pth
EVENT_DETECTOR_MODEL_PATH := lib/med/model_presentation_draft_2022_04_07_11_52_08.pth

ADMIN_PORT := 8001
ADMIN_WORKERS := 1

# Define the Docker image name and tag
DOCKER_IMAGE := classification-service
DOCKER_TAG := latest

.PHONY: dashboard admin

dashboard: 
	DATABASE_URL=$(DATABASE_URL) \
	LOGS_DIR=$(LOGS_DIR) \
	CLASSIFICATION_OUTPUT_DIR=$(CLASSIFICATION_OUTPUT_DIR) \
	EVENT_DETECTOR_MODEL_PATH=$(EVENT_DETECTOR_MODEL_PATH) \
	SPECIES_CLASSIFIER_MODEL_PATH=$(SPECIES_CLASSIFIER_MODEL_PATH) \
	uvicorn services.dashboard.dashboard-service:app --host 0.0.0.0 --port $(DASHBOARD_PORT) --workers $(DASHBOARD_WORKERS) --reload

admin:
	uvicorn services.admin.admin:app --host 0.0.0.0 --port $(ADMIN_PORT) --workers $(ADMIN_WORKERS) --reload