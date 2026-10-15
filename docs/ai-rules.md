# Правила для ИИ

Инструкция для нейронки, которая генерирует скрипты Nursultan с доступом в интернет. Публикуется по этой же ссылке, модель должна следовать правилам без исключений.

## Порядок работы

1. Скрипт Nursultan собирать по [оригинальной документации](https://docs.nursultan.fun/) — она единственный источник правды по API клиента.
2. Для сети применять правила и блок `internet-core` с этой страницы и из файла `templates/net-core.kts` кита.
3. Готовый `.kts` — один файл, кладётся в `%APPDATA%\Nursultan\scripts`.

## Жёсткие запреты

| Запрет | Причина |
| --- | --- |
| `java.net`, `java.io`, `java.nio` в скрипте | песочница, загрузка упадёт с `references blocked symbol` |
| `Thread`, `java.util.concurrent`, рефлексия | там же |
| свои jar, пакеты, классы вне `nursultan`/`kotlin`/`java` из whitelist | там же |
| JSON парсить в скрипте | нет парсера; разбор — директива `jsonpath` |
| блокирующее ожидание внутри обработчика | бюджет 250 мс |
| API-ключи литералом в `.kts` | ключ утечёт при передаче файла; только `keyref` |
| несколько запросов одновременно | один слот `net.req` |
| отправка запроса каждый тик без события | расход квот стороннего API |

## Обязательные элементы

| Элемент | Требование |
| --- | --- |
| `requireApi(2)` | первой строкой, скрипт использует assets и настройки |
| блок `internet-core` | целиком, между маркерами, без правок |
| `netTick()` | в каждом `on<ClientTickEvent>` |
| сброс `netReady` | сразу после чтения ответа |
| `netBusy()` перед отправкой | защита от потери запроса |
| `netJsonEscape` | для каждого пользовательского текста в теле JSON |
| `timeoutSec` | 10–15 для обычных API, 60 для моделей, 20 для Telegram |
| проверка `netCode in 200..299` | ветка `else` с `log.warn` обязательна |

## Шаблон обработчика

```kotlin
on<ClientTickEvent> {
    netTick()

    if (netReady) {
        netReady = false
        if (netCode in 200..299) chat.print(netBody.trim())
        else log.warn("net $netCode: $netBody")
    }

    if (!netBusy() && запускается_событие) {
        netGet("https://api.example.com/data", jsonpath = "value")
    }
}
```

## Секреты

```json
{ "secrets": { "mykey": "..." } }
```

В скрипте только имя:

```kotlin
val keyref by input("Ключ", "mykey", "имя из bridge.json")
netGet("https://api.example.com/data?key={{KEY}}", keyref = keyref)
```

Если ключа нет в `secrets`, ответ придёт с `code 0` и текстом ошибки — сообщай пользователю, что нужно заполнить bridge.json.

## Типовые рецепты

| Задача | Форма |
| --- | --- |
| прочитать поле из JSON | `jsonpath: a.0.b` |
| прочитать текстовый ответ | без `jsonpath` |
| POST с JSON | `netPost(url, """{"k":"${netJsonEscape(v)}"}""")` |
| заголовок авторизации | `headers = listOf("Authorization: Bearer {{KEY}}")`, `keyref` |
| повтор опроса | счётчик тиков, период ≥ 5 с |
| получить ответ позже | ждать `netReady` в тиках, не выходить за 250 мс |

Полные формы запросов — [Рецепты API](recipes.md).

## Латентность и ожидания

Ответ приходит не раньше чем через 1,5 с, модели — до 15 с. В описании скрипта укажи ожидаемое время ответа. Никогда не обещай мгновенный результат и не пиши циклы ожидания.

## Проверка перед выдачей

1. `requireApi(2)` есть.
2. Блок `internet-core` полный, маркеры на месте.
3. `netTick()` вызывается каждый тик.
4. `netReady` сбрасывается.
5. Тексты экранированы.
6. Ключей нет, только `keyref`.
7. Таймауты проставлены.
8. Скрипт не запрашивает чаще, чем нужно.

## Страницы оригинального API для ссылок

| Тема | Ссылка |
| --- | --- |
| песочница | https://docs.nursultan.fun/scripting/extras/limits |
| настройки | https://docs.nursultan.fun/scripting/settings/types |
| сохранение данных | https://docs.nursultan.fun/scripting/settings/storage |
| assets | https://docs.nursultan.fun/scripting/extras/assets |
| события | https://docs.nursultan.fun/scripting/events/reference |
| MCP клиента | https://docs.nursultan.fun/scripting/extras/mcp |

[PreviousПримеры](examples.md) [NextРешение проблем](troubleshooting.md)
