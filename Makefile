docker-up:
	docker compose up --build -d

version:
	docker compose run --rm webserver weschatbot version

docker-build:
	docker build -t weschatbot:0.0.1 .

docker-down:
	docker compose down
