# API скрипта

Блок `internet-core` (`templates/net-core.kts`) вставляется в скрипт целиком, между маркерами. Требует `requireApi(2)`.

## Объекты состояния

| Объект | Тип | Назначение |
| --- | --- | --- |
| `netReq` | `String` | слот запроса, скрыт в меню; ядро пишет в него сам |
| `netReady` | `Boolean` | `true`, когда ответ получен; после обработки сбросить в `false` |
| `netCode` | `Int` | HTTP-статус; `0` — ошибка моста или таймаут; `-1` — ответа ещё нет |
| `netBody` | `String` | текст ответа или текст ошибки |

## Функции

| Функция | Описание |
| --- | --- |
| `netSend(url, method, headers, body, timeoutSec, jsonpath, keyref): Int` | отправить запрос, вернёт номер или `-1`, если предыдущий ещё в полёте |
| `netGet(url, jsonpath, keyref, headers, timeoutSec): Int` | GET |
| `netPost(url, body, contentType, jsonpath, keyref, timeoutSec): Int` | POST с телом |
| `netBusy(): Boolean` | запрос в полёте |
| `netTick()` | вызывать каждый тик: читает ответ, обрабатывает таймаут |
| `netJsonEscape(value): String` | экранирование строки для тела JSON |

## Шаблон обработчика

```kotlin
on<ClientTickEvent> {
    netTick()

    if (netReady) {
        netReady = false
        if (netCode in 200..299) chat.print(netBody)
        else log.warn("net $netCode: $netBody")
    }

    if (!netBusy() && /* условие */) {
        netGet("https://api.example.com/data", jsonpath = "value")
    }
}
```

## Правила

| Правило | Зачем |
| --- | --- |
| `netTick()` вызывается в каждом тике | без него ответ не будет прочитан |
| `netReady` сбрасывается вручную | одно срабатывание на один ответ |
| один запрос в полёте | `netSend` вернёт `-1`, если слот занят |
| ожидание только в тиках | обработчик ограничен 250 мс, спать и ждать нельзя |
| повторная отправка — после `netBusy() == false` | иначе запрос потеряется |
| JSON не парсится | для вырезания полей нужна директива `jsonpath` |
| тексты через `netJsonEscape` | тело JSON должно быть валидным |

## Таймауты

| Ситуация | Поведение |
| --- | --- |
| ответ не пришёл за `timeoutSec` | `netCode = 0`, `netBody = "timeout after Ns"`, `netReady = true` |
| мост не запущен | тот же таймаут, затем ошибка |
| ответ пришёл раньше | файл читается на ближайшем опросе, раз в 5 тиков |

Рекомендуемые значения: обычные API — 10–15 с, языковые модели — 60 с, Telegram — 20 с.

## Файлы assets

| Параметр | Лимит |
| --- | --- |
| размер ответа | 8 МиБ (`maxBodyBytes`), больше — ошибка моста |
| папка ответов | `_net/resp/<scriptId>/`, ответы других скриптов не пересекаются |
| чтение | `assets.text` возвращает `null`, пока файла нет — это норма |

## Состояние после перезагрузки скрипта

Перезагрузка файла `.kts` обнуляет счётчики: слот пуст, ожидание сброшено, недочитанный ответ удаляется мостом по возрасту. Отправлять запрос заново — обычным `netSend`.

## Исходник блока internet-core

Полный исходник `templates/net-core.kts`. Вставляется в скрипт целиком, между маркерами, без правок:

```kotlin
// ===== internet-core v1 (proto 1) — вставляй целиком, не изменяй =====
var netReq by input("net.req", "", "").visibleWhen { false }
var netSeq = 0
var netWaitId = 0
var netWaitNonce = ""
var netWaitTicks = 0
var netTimeoutTicks = 1200
var netReady = false
var netCode = -1
var netBody = ""

fun netSend(
    url: String,
    method: String = "GET",
    headers: List<String> = emptyList(),
    body: String? = null,
    timeoutSec: Int = 60,
    jsonpath: String? = null,
    keyref: String? = null
): Int {
    if (netWaitId != 0) return -1
    val id = ++netSeq
    val nonce = "${client.millis()}-${Random.nextInt(100000, 999999)}"
    val out = StringBuilder()
    out.append("NETREQ ").append(id).append('\n')
    out.append(method.uppercase()).append(' ').append(url).append('\n')
    out.append("nonce: ").append(nonce).append('\n')
    if (timeoutSec != 60) out.append("timeout: ").append(timeoutSec).append('\n')
    if (jsonpath != null) out.append("jsonpath: ").append(jsonpath).append('\n')
    if (keyref != null) out.append("keyref: ").append(keyref).append('\n')
    for (line in headers) out.append("header: ").append(line.replace('\n', ' ')).append('\n')
    out.append('\n')
    if (body != null) out.append(body)
    netWaitId = id
    netWaitNonce = nonce
    netWaitTicks = 0
    netTimeoutTicks = timeoutSec * 20
    netReady = false
    netCode = -1
    netBody = ""
    netReq = out.toString()
    return id
}

fun netGet(
    url: String,
    jsonpath: String? = null,
    keyref: String? = null,
    headers: List<String> = emptyList(),
    timeoutSec: Int = 60
): Int = netSend(url, "GET", headers, null, timeoutSec, jsonpath, keyref)

fun netPost(
    url: String,
    body: String,
    contentType: String = "application/json",
    jsonpath: String? = null,
    keyref: String? = null,
    timeoutSec: Int = 60
): Int = netSend(url, "POST", listOf("Content-Type: $contentType"), body, timeoutSec, jsonpath, keyref)

fun netBusy(): Boolean = netWaitId != 0

fun netTick() {
    if (netWaitId == 0) return
    netWaitTicks++
    if (netWaitTicks % 5 != 0) return
    if (netWaitTicks >= netTimeoutTicks) {
        netCode = 0
        netBody = "timeout after ${netTimeoutTicks / 20}s"
        netWaitId = 0
        netReady = true
        log.warn("net: $netBody")
        return
    }
    val raw = assets.text("_net/resp/$id/net-$netWaitId-$netWaitNonce.env") ?: return
    val p1 = raw.indexOf('\n')
    val p2 = if (p1 >= 0) raw.indexOf('\n', p1 + 1) else -1
    val p3 = if (p2 >= 0) raw.indexOf('\n', p2 + 1) else -1
    if (p1 < 0 || p2 < 0 || p3 < 0 || !raw.startsWith("NETRESP ")) {
        netCode = 0
        netBody = "bad response envelope"
        netWaitId = 0
        netReady = true
        return
    }
    val declared = raw.substring(p2 + 1, p3).removePrefix("body: ").toIntOrNull() ?: -1
    val body = raw.substring(p3 + 1)
    if (declared != body.length) {
        netCode = 0
        netBody = "truncated response"
        netWaitId = 0
        netReady = true
        return
    }
    netCode = raw.substring(p1 + 1, p2).toIntOrNull() ?: 0
    netBody = body
    netWaitId = 0
    netReady = true
    if (netCode == 0 || netCode !in 200..299) log.warn("net $netCode: $netBody")
}

fun netJsonEscape(value: String): String = buildString {
    for (ch in value) when (ch) {
        '\\' -> append("\\\\")
        '"' -> append("\\\"")
        '\n' -> append("\\n")
        '\r' -> append("\\r")
        '\t' -> append("\\t")
        else -> if (ch < ' ') append("\\u").append(ch.code.toString(16).padStart(4, '0')) else append(ch)
    }
}
// ===== конец internet-core =====
```

Этот же файл лежит в репозитории: [`templates/net-core.kts`](https://raw.githubusercontent.com/cloiss21011-code/nursultan-internet-kit/main/templates/net-core.kts).

[PreviousПротокол](protocol.md) [NextПримеры](examples.md)
