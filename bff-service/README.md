# BFF Service (Backend for Frontend)

API Gateway для мониторинга ЛЭП. Проксирует запросы от фронтенда к YOLOv8 Model Service.

## Описание

BFF (Backend for Frontend) сервис предоставляет единую точку входа для фронтенда и управляет взаимодействием с микросервисами.

## API

- `GET /` - информация о сервисе
- `GET /health` - проверка здоровья сервиса и зависимостей
- `GET /api/model/info` - информация о модели (метрики, классы, требования) - проксирует в YOLOv8 Model Service
- `POST /api/predict` - детекция объектов (проксирует в YOLOv8 Model Service)

## Запуск

### Docker

```bash
docker-compose up bff-service
```

### Локально

```bash
pip install -r requirements.txt
export YOLOV8_SERVICE_URL=http://localhost:8001
python main.py
```

## Переменные окружения

- `YOLOV8_SERVICE_URL` - URL YOLOv8 Model Service (по умолчанию: `http://yolov8-model-service:8000`)
- `PORT` - порт сервиса (по умолчанию: `8000`)

