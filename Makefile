.PHONY: build up down logs restart test clean

# Сборка и запуск
build:
	docker compose up --build -d

up:
	docker compose up -d

down:
	docker compose down

# Логи
logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

# Перезапуск
restart:
	docker compose restart

restart-hard:
	docker compose down && docker compose up --build -d

# Тестирование API
test:
	@echo "=== Health Check ==="
	@curl -s http://localhost:8000/health | python3 -m json.tool || true
	@echo ""
	@echo "=== Validate API ==="
	@curl -s -X POST http://localhost:8000/api/validate \
		-H "Content-Type: application/json" \
		-d '{"goal":"Сократить время обработки заказов на 20% до конца Q3 2025","key_results":["Внедрить автоматизацию","Снизить ошибки до 1%"]}' | python3 -m json.tool || true
	@echo ""
	@echo "=== Decompose API ==="
	@curl -s -X POST http://localhost:8000/api/decompose \
		-H "Content-Type: application/json" \
		-d '{"goal":"Цифровизация процесса учёта сырья"}' | python3 -m json.tool || true

# Очистка
clean:
	docker compose down -v
	docker system prune -f

# Статус
status:
	@docker compose ps
	@echo ""
	@echo "URLs:"
	@echo "  Frontend: http://localhost:8082"
	@echo "  Backend:  http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
