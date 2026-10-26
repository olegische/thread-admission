# Tool admission — рабочий каталог статьи

- [Собранный драфт v01 (EN)](tool_admission_v01.md)
- `parts/` — по файлу на раздел, `00-`…`09-`, в порядке сборки
- `build.py` — сборка; `--check` проверяет, что собранный файл актуален

```sh
python3 build.py
python3 build.py --check
```

## Статус v01 (2026-10-26)

Полный драфт: добавлены «зачем» для принимающей стороны (§0), таблица прецедентов класса источника и Temporal (§1), `source_class` вместо `epistemic_class`, потребитель класса и типизация через `vct` с таблицей claims (§3), контрпример 2 под разные акторы (§5), три разведения (§8), standing / authority и lineage между агентами (§9). Написан от проблемы, не от кода: эксперимент (§7) специфицирован и помечен в тексте как не запущенный; результаты не заявлены. Схема tool-статемента и две функции на Python в §3–§4 — предложенный профиль, референсная реализация не опубликована, и текст это говорит.

Digest'ы в §4–§5 настоящие: посчитаны `rfc8785` + SHA-256 по фикстурам thread-admission (`fixtures/api-call.json`) и по варианту результата с exit code 1.

## Редакторские нормы

Тон по отношению к сообществу MCP — признание сделанного, без счёта провалов. Статусы и даты предложений приводятся нейтрально в таблице слоёв §1. Основание правок — заявления принципала.

## Что сверить до публикации (CHECK)

1. Цитаты участников MCP по первичным страницам: «the refusal record is inert», «unaccounted» в двух смыслах (XuebinMa, 2026-09-13); «later stages must not silently inherit trust from earlier metadata» (ozereray, 2026-09-15); «defaults are unknown, not clean», «a gate that ran and allowed from one that never ran» (damoclais, 2026-09-14 / 09-28); «recompute immediately before execution» (XuebinMa, 2817); «proves the request, not the outcome» (текст SEP-2787); «explicitly not authorization evidence» (текст SEP-2817). Формулировка бага про host-reported / runtime-witnessed в §0 и §2 дана пересказом; найти оригинал и либо процитировать, либо оставить пересказ с атрибуцией.
2. Даты и статусы: #2704 2026-05-09; SEP-2787 2026-05-25 → 2026-09-22; SEP-2817 2026-05-29, open; SEP-2828 2026-05-31 → 2026-07-18; draft-sirkkavaara-vaara-receipt-14 2026-10-15; #2789 закрыт 2026-06-30.
3. Имена полей по спецификациям: SLSA Provenance v1 (`runDetails.builder`, `buildDefinition.externalParameters` / `internalParameters` / `resolvedDependencies`), VSA (`verifier.id`, `timeVerified`, `policy`, `inputAttestations`, `verificationResult`, `slsaVersion`), in-toto `ResourceDescriptor`, EAT `profile`, XACML decisions. Ссылки в §1 ведут на slsa.dev и OASIS; сверить версии.
4. `draft-gilda-wimse-agent-audit-record`: подтвердить, что использует in-toto Statement + DSSE + JCS (взято из диалога `chatgpt-01.txt`, не из первоисточника).
5. Исторические примеры в §2 (DMARC и требования Gmail/Yahoo 2024, CT в Chrome 2018, PSD2, Let's Encrypt, SLSA в CI, MDN RFC 3798, HTTP Message Signatures в ActivityPub) — даты и формулировки по первоисточникам, если останутся в тексте с датами.
6. §7: перед публикацией либо заменить «specified and not yet run» на результаты с версиями, либо оставить как есть и так и опубликовать. Второе честно, но слабее статьи про треды.

## Что сознательно не вошло

Правила OpenAI для посредников; policy и routing evidence; wallet как продукт; XACML и RATS как предмет; SCITT-профили агентных receipts; эпистемическая запись; внутренние вызовы составного исполнителя к бэкендам.
