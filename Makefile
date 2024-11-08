
.PHONY: up dev stop remove

up:
	docker builder prune -f && docker compose up

dev: 
	docker builder prune -f && docker compose up -d

down:
	docker ps -a --filter "label=com.docker.compose.project=$(TAG)" -q | xargs -r docker stop

stop: 
	docker ps -a -q | xargs -r docker stop
	
reset:
	docker ps -a -q | xargs -r docker stop
	docker ps -a -q | xargs -r docker rm
	docker images -q | xargs -r docker rmi -f


