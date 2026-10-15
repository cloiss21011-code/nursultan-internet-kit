# Примеры

Все примеры — законченные скрипты с блоком `internet-core` внутри. Файл кладётся в `%APPDATA%\Nursultan\scripts`, включается в Scripts-табе.

| Файл | Что делает |
| --- | --- |
| `templates/example-get.kts` | погода из wttr.in в чате по таймеру |
| `templates/example-post.kts` | POST с JSON, печатает поле из ответа |
| `templates/example-ai-chat.kts` | вопрос модели Gemini, ответ в чате |
| `templates/example-telegram.kts` | отправка сообщения в Telegram |

## Погода — GET по таймеру

Настройки: `Город`, `Период (с)`. Скрипт раз в период отправляет `GET https://wttr.in/<город>?format=1` и печатает однострочный прогноз.

Ключевые места:

```kotlin
if (!netBusy()) {
    val query = city.replace(" ", "%20")
    netGet("https://wttr.in/$query?format=1", timeoutSec = 15)
}
```

Ответ — обычный текст, `jsonpath` не нужен. Проверка `netBusy()` не даёт отправить второй запрос, пока первый в полёте.

## POST с JSON — `example-post.kts`

Настройка `Значение` попадает в тело через `netJsonEscape`:

```kotlin
netPost(
    "https://httpbin.org/anything",
    """{"foo":"${netJsonEscape(payload)}"}""",
    jsonpath = "json.foo"
)
```

Сервер возвращает то, что получил, мост вырезает `json.foo`, скрипт печатает результат. Схема «отправил произвольный JSON → получил поле» работает с любым REST API.

## Gemini — `example-ai-chat.kts`

Настройки: `Промпт`, `Ключ` (имя из `secrets`). Отправка по чекбоксу `Задать вопрос`:

```kotlin
val json = """{"contents":[{"parts":[{"text":"${netJsonEscape(prompt)}"}]}]}"""
netPost(
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={{KEY}}",
    json,
    jsonpath = "candidates.0.content.parts.0.text",
    keyref = keyref,
    timeoutSec = 60
)
```

Требуется `"secrets": { "gemini": "..." }` в bridge.json. Для DeepSeek меняется URL на `https://api.deepseek.com/chat/completions`, заголовок `Authorization: Bearer {{KEY}}` и тело в формат `messages`, `jsonpath: choices.0.message.content`.

Латентность модели 1–15 с: скрипт не блокируется, ответ приходит в чат, когда будет готов.

## Telegram — `example-telegram.kts`

Настройки: `Chat id`, `Сообщение`. Ключ бота — в `secrets.telegram` целиком, в URL подставляется `{{KEY}}`:

```
POST https://api.telegram.org/bot{{KEY}}/sendMessage
```

Проверка успеха — не статус, а тело: Telegram возвращает HTTP 200 и `"ok": false` при ошибке, поэтому скрипт сравнивает `netBody == "true"`.

Входящие сообщения (`getUpdates`) доступны тем же способом: `GET https://api.telegram.org/bot{{KEY}}/getUpdates?timeout=0&offset=<N>` с `jsonpath` на нужное сообщение; офсет хранится в `storage`. Вебхуки невозможны — мост принимает только исходящие соединения.

## Discord-вебхук

```kotlin
netPost(
    "https://discord.com/api/webhooks/ID/TOKEN",
    """{"content":"${netJsonEscape(text)}"}"""
)
```

Без `jsonpath`: успешный вебхук возвращает пустое тело, достаточно `netCode in 200..299`.

## Регулярный опрос своего API

```kotlin
if (!netBusy() && waitTicks >= (period * 20).toInt()) {
    waitTicks = 0
    netGet("https://api.example.com/v1/status", jsonpath = "status")
}
```

Период — в тиках, 20 тиков = 1 с. Чем меньше период, тем больше нагрузка на API: уважайте лимиты сторонних сервисов.

## allowlist для скрипта

Запрос к хосту вне `allowlist` получит `netCode = 0` и текст `bridge error: хост ... не входит в allowlist`. Лечится либо добавлением хоста в bridge.json, либо пустым allowlist.

[PreviousAPI скрипта](api.md) [NextПравила для ИИ](ai-rules.md)
