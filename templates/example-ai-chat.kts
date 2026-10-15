requireApi(2)
name("AI вопрос")
description("Задаёт вопрос модели Gemini и печатает ответ в чат")

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

val prompt by input("Промпт", "Ответь одним коротким предложением: что такое выживание в Minecraft?", "")
val keyref by input("Ключ", "gemini", "имя ключа из bridge.json")
val ask by checkBox("Задать вопрос", false)
var wasOn = false

on<ClientTickEvent> {
    netTick()

    if (netReady) {
        netReady = false
        if (netCode in 200..299) chat.print("AI: ${netBody.trim()}")
    }

    val pressed = ask
    if (pressed && !wasOn) {
        ask = false
        if (!netBusy()) {
            val json =
                """{"contents":[{"parts":[{"text":"${netJsonEscape(prompt)}"}]}]}"""
            netPost(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={{KEY}}",
                json,
                jsonpath = "candidates.0.content.parts.0.text",
                keyref = keyref,
                timeoutSec = 60
            )
        }
    }
    wasOn = pressed
}
