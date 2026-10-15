# Рецепты API

Готовые формы запросов под типовые задачи. Копируется нужная строка, URL и `jsonpath` заменяются на свои.

## Каталог

| Задача | Форма |
| --- | --- |
| прочитать поле из JSON | `jsonpath: data.value` |
| прочитать массив по индексу | `jsonpath: items.0.name` |
| прочитать текстовый ответ | без `jsonpath` |
| GET с параметрами | параметры прямо в URL |
| POST с JSON | `netPost(url, """{"k":"${netJsonEscape(v)}"}""")` |
| авторизация | `headers = listOf("Authorization: Bearer {{KEY}}")` + `keyref` |
| Basic-авторизация | `Authorization: Basic {{KEY}}`, ключ — base64 логин:пароль |
| повтор при ошибке | счётчик тиков после `netCode 0` |
| пауза между запросами | период в тиках, ≥ 100 (5 с) |
| опрос Telegram | `getUpdates?timeout=0&offset=<N>`, офсет в `storage` |
| сохранить ответ | значение из `netBody` в `storage` |
| ошибка API при статусе 200 | проверять текст тела вручную |

## GET с параметрами

```kotlin
val city = netJsonEscape(query.replace(" ", "%20"))
netGet("https://api.open-meteo.com/v1/forecast?city=$city&format=json", jsonpath = "current.temperature_2m")
```

Параметры склеиваются в URL: `?ключ=значение&ключ2=значение2`. Значения — через `URLEncoder`-подобную замену: пробел `%20`, кириллица `%D0%...`, `&` и `=` в значениях экранируются.

## POST с JSON

```kotlin
val json = """{"prompt":"${netJsonEscape(prompt)}","max_tokens":128}"""
netPost("https://api.example.com/v1/generate", json, contentType = "application/json", jsonpath = "result.text")
```

`netJsonEscape` обязателен для каждого пользовательского текста: без него кавычки и переносы строк ломают JSON, и API вернёт 400.

## Bearer-токен

```kotlin
netGet(
    "https://api.example.com/v1/me",
    jsonpath = "login",
    keyref = "myapi",
    headers = listOf("Authorization: Bearer {{KEY}}")
)
```

Значение ключа в `bridge.json`: `"myapi": "ghp_..."`. Токен не появится ни в скрипте, ни в логе.

## Basic-авторизация

```kotlin
netGet(
    "https://api.example.com/v1/data",
    keyref = "basic",
    headers = listOf("Authorization: Basic {{KEY}}")
)
```

`"basic": "dXNlcjpwYXNz"` — base64 от `user:pass`. Скрипт генерирует значение сам: `android.util.Base64` недоступен, поэтому значением становится готовая строка.

## Ответ без JSON

Сервисы вроде wttr.in отдают простой текст:

```kotlin
netGet("https://wttr.in/Moscow?format=1", timeoutSec = 15)
// netBody: "+22° 🌤"
```

Без `jsonpath` в файл уходит тело целиком.

## Массивы и вложенность

```text
jsonpath: candidates.0.content.parts.0.text
jsonpath: items.2.price
jsonpath: data.results.0.urls.raw
```

Число после точки — индекс массива (с нуля), строка — ключ объекта. Порядок фиксированный: объекты и массивы чередуются по мере вложенности.

## Повтор после ошибки

```kotlin
var retries = 0
var nextAttemptTicks = 0L

on<ClientTickEvent> {
    netTick()
    ticks++

    if (netReady) {
        netReady = false
        if (netCode in 200..299) {
            retries = 0
            // успех
        } else {
            retries++                        // счётчик попыток
            nextAttemptTicks = ticks + 100   // пауза 5 с в тиках
        }
    }

    if (!netBusy() && retries < 3 && ticks >= nextAttemptTicks && shouldRun) {
        netGet("https://api.example.com/v1/status", jsonpath = "status")
    }
}
```

Пауза между попытками — 5 с и больше: короткий цикл повторов превращается в флуд и получает 429 от API.

## Rate limit

| Поведение стороннего API | Действие скрипта |
| --- | --- |
| 429 Too Many Requests | увеличить период, не уменьшать |
| код 200 и `"error"` в теле | считать ошибкой, не ретраить слепо |
| лимит в заголовке `X-RateLimit-Remaining` | вырезать `jsonpath` и учитывать |

Простая схема «один запрос — не чаще, чем раз в N секунд»:

```kotlin
val periodSec = 10
if (!netBusy() && ticks >= lastRequestTicks + periodSec * 20) {
    lastRequestTicks = ticks
    netGet(url, jsonpath = "value")
}
```

## Опрашивающий Telegram-бот

```kotlin
var offset = storage.int("offset", 0)

// в тике, после netTick():
if (!netBusy() && ticks >= nextPollTicks) {
    nextPollTicks = ticks + 40               // 2 с
    netGet(
        "https://api.telegram.org/bot{{KEY}}/getUpdates?timeout=0&offset=$offset",
        jsonpath = "result.0.message.text",
        keyref = "telegram",
        timeoutSec = 20
    )
}
```

Пустой ответ `[]` приходит за секунды: `timeout=0` запрещает Telegram держать соединение. Увеличенный офсет `result.0.update_id + 1` сохраняется в `storage` — тогда повторные сообщения не читаются дважды.

## Пустой ответ

Успешный DELETE и Discord-вебхук отдают пустое тело. Проверять нужно только статус:

```kotlin
if (netCode in 200..299) {
    // тело пустое — это норма
}
```

## Ошибка в 200

Часть API возвращает `200` и объект с полем ошибки:

```kotlin
netGet("https://api.example.com/v1/search", jsonpath = "error")
if (netCode == 200 && netBody != "null") {
    log.warn("API: $netBody")
}
```

Безопаснее всего — `jsonpath` на поле успеха: если его нет, мост вернёт `code 0` с `jsonpath: ключ не найден`.

## Большой ответ

Если ответ мегабайтный, а нужно одно поле — сразу указывайте `jsonpath`: мост вырежет поле до записи в файл, и скрипт прочитает килобайты вместо мегабайтов.

[API скрипта](api.md) · [Примеры](examples.md) · [Безопасность](security.md)
