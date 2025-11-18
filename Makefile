.PHONY: help build up down restart logs clean

help:
	@echo "Доступные команды:"
	@echo "  make build    - Собрать все Docker образы"
	@echo "  make up       - Запустить все сервисы"
	@echo "  make down     - Остановить все сервисы"
	@echo "  make restart  - Перезапустить все сервисы"
	@echo "  make logs     - Показать логи всех сервисов"
	@echo "  make clean     - Удалить все контейнеры и образы"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	docker system prune -f

