# Annotation Service

Сервис для добавления аннотаций (bbox) на изображения.

## Функциональность

- Скачивание изображений из files-service
- Рисование прямоугольников (bbox) на изображениях
- Сохранение аннотированных изображений обратно в files-service

## API

### POST /annotations/annotate

Добавить аннотации на изображение.

**Request Body:**
```json
{
  "file_id": "string",
  "bboxes": [
    {
      "x": 100,
      "y": 100,
      "width": 200,
      "height": 150
    }
  ],
  "project_id": "string",
  "file_type": "result_image"
}
```

**Response:**
```json
{
  "success": true,
  "file_id": "new_file_id",
  "filename": "annotated_image.jpg",
  "message": "Image annotated successfully"
}
```

## Переменные окружения

- `FILES_SERVICE_URL` - URL сервиса файлов (по умолчанию: `http://files-service:8000`)


