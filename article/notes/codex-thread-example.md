# Проверка примера Codex для части 01

Редакторская записка, не часть публикуемой статьи.

Проверено 17 октября 2026 по локальному checkout `/Users/olegromanchuk/Projects/_amnezia/repos/amcode`, HEAD `431f5aa78fd007ec45d591452cfb37ad12c61c15`. Файлы репозитория amcode не изменялись.

## Выбор представления

Пример показывает сокращённый массив `items` одного хода в **App Server**: запрос пользователя, результат команды, ответ ассистента. Это не полный ответ чтения треда, не файл rollout и не массив Responses API. Названия и поля взяты из определения `ThreadItem`. Сценарий `python export.py`, имена и вывод иллюстративны: это не захваченная сессия и не результат выполнения команды во время редакторской работы.

Функция примера — показать различие между типом записи, её происхождением и тем, что она устанавливает. Approval RPC и журнал аудита среды находятся вне переносимого транскрипта в постановке статьи. Разрешения новых действий определяет принимающая среда. Часть 04 развивает пример через результат инспекции CSV, привязанный к вызову инструмента и дайджесту прочитанных байтов.

## Основания

- `codex-rs/app-server-protocol/src/protocol/v2/item.rs`: `ThreadItem`, сериализация `camelCase`; варианты `UserMessage`, `CommandExecution`, `AgentMessage`; определения `CommandExecutionRequestApprovalParams` и `CommandExecutionRequestApprovalResponse`.
- `codex-rs/app-server-protocol/schema/typescript/v2/ThreadItem.ts`, `UserInput.ts`, `CommandAction.ts`, `CommandExecutionStatus.ts`: проверка имён и форм полей.
- `codex-rs/app-server-protocol/schema/json/v2/ThreadReadResponse.json`: схема `definitions.ThreadItem`; пример проверяется как массив этих объектов, а не как полный `ThreadReadResponse`. Опущенные поля допускаются JSON-схемой и Rust-десериализацией; это сокращение представления, а не полный вывод сериализатора.
- `codex-rs/app-server-protocol/src/protocol/common.rs`: RPC `item/commandExecution/requestApproval` связывает параметры запроса и ответ с решением.
- `codex-rs/app-server-protocol/schema/json/CommandExecutionRequestApprovalParams.json`, `CommandExecutionRequestApprovalResponse.json`, `JSONRPCResponse.json`: обязательные поля запроса, значение `accept`, транспортная оболочка ответа `{id, result}`.
- `codex-rs/app-server/tests/suite/v2/config_requirements_exec_tests.rs`: интеграционный пример получения approval-запроса, проверки связи `itemId` с вызовом и отправки `CommandExecutionApprovalDecision::Accept`.
- `codex-rs/app-server/tests/common/test_app_server.rs`: `send_response` оборачивает результат в `JSONRPCResponse { id, result }`. Это транспортная форма, отличная от внутренней формы `ServerResponse` с полями `method` и `response`.
- `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`: `ThreadReadParams`, `ThreadReadResponse`; для пагинированной истории исходник рекомендует `thread/turns/list` и `thread/items/list` вместо полной загрузки через `includeTurns`.
- `codex-rs/app-server-protocol/src/protocol/thread_history_projection.rs`: преобразование сохранённых `ItemCompleted(TurnItem)` в `ThreadItem` для новой пагинированной истории.
- `codex-rs/rollout/src/policy.rs`, `persisted_event_msg`: `ExecApprovalRequest` и `ApplyPatchApprovalRequest` входят в группу `Transient, non-durable events`, для которой возвращается `None`. Это прямое основание отделять живой запрос от сохранённой истории.
- `codex-rs/app-server/src/outgoing_message.rs`, `notify_client_response`: ответ извлекает ожидающий callback, может передаваться в `track_server_response` и отправляется ожидающему обработчику. `codex-rs/analytics/src/client.rs` определяет отдельные факты `ServerRequest` и `ServerResponse`; наличие этого пути не означает наличие approval в API истории треда.
- `codex-rs/protocol/src/models.rs`: отдельный модельный слой `ResponseItem`, варианты `FunctionCall` и `FunctionCallOutput`; JSON-аргументы вызова сериализуются строкой, результат — строкой или массивом content items.

## Границы вывода

`commandExecution` — запись команды и результата, а не переносимое криптографическое свидетельство сама по себе. Даже достоверно записанный exit code и stdout не удостоверяют содержимое файла, которое процесс описал. Это основной вывод примера.

В проверенной версии approval-запрос исключён из долговременного rollout, отдельного `ThreadItem` с решением нет. Completed command item не устанавливает факт явного пользовательского одобрения. Это само по себе не дефект переноса: обычное продолжение не требует восстановления старого разрешения на запуск команды. Для аудита прежнего разрешения понадобится отдельный захват или доступная запись. Доступность отдельной аналитики не переносится на интерфейс истории; утверждение «никаких записей approval нигде не существует» не делается.

В части 04 `tool_result.v1` — предлагаемый формат свидетельства об инструментальном наблюдении, а не встроенный тип Codex. Он фиксирует вызов, входные байты, параметры и результат инспекции. В части 07 проверяются привязки результатов и применение текущей политики выполнения после возобновления. Перенос бизнес-согласований и событий аудита не входит в рассматриваемую задачу. Свойства произвольных других версий Codex этим просмотром не устанавливаются.

Публикуемый текст не содержит локальных путей, внутренних ADR или сведений о частном продукте. Привязка к checkout оставлена здесь для повторной редакторской проверки.
