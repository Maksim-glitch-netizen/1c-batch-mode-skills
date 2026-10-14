# Варианты ОС

**Фактические тесты выполнены только на Windows. Варианты macOS и Linux подготовлены, но на своих ОС не тестировались.**

Windows использует PowerShell-примеры из `workflow.md`. На macOS/Linux используй Python 3.10+,
прямые слеши и Bash/Zsh. `new_object_workflow.py` работает с путями через pathlib и сам не запускает 1С.
Подготовка этих вариантов не подтверждает работоспособность платформы или внешних зависимостей на них.

```bash
python3 -B '<skill>/scripts/new_object_workflow.py' prepare \
  --type Report --name Demo_Report \
  --baseline-configuration '<main-source>/Configuration.xml' \
  --workspace '<task-root>/new-object-merge'
python3 -B '<skill>/scripts/new_object_workflow.py' finalize \
  --manifest '<task-root>/new-object-merge/manifest.json'
# После успешного MergeCfg и фактической контрольной XML-выгрузки:
python3 -B '<skill>/scripts/new_object_workflow.py' verify-main \
  --manifest '<task-root>/new-object-merge/manifest.json' --current-source '<main-source>'
# После разработки и загрузки реальных полей/зависимостей:
python3 -B '<skill>/scripts/new_object_workflow.py' verify-ready \
  --manifest '<task-root>/new-object-merge/manifest.json' --current-source '<main-source>'
python3 -B '<skill>/scripts/validate-skill.py'
```

Эти команды показывают форму вызовов в разные моменты процесса. Не запускай весь блок подряд:
между prepare, finalize и verify-main выполняются scaffold, валидация, сборка donor и объединение
по `workflow.md`. Самостоятельно выясни реальные пути вместо `<...>`.

Пять внешних skills должны существовать для выбранного клиента и ОС. На macOS/Linux предпочитай
Python-вариант cc-1c-skills либо отдельно проверенный PowerShell 7. Параметры их скриптов могут
отличаться от PowerShell-варианта: прочитай соответствующий SKILL.md; не меняй расширение `.ps1`
на `.py` механически. Внешние зависимости не включены в этот комплект.

Перед командами 1С прочитай [платформенные правила пакетного skill](../../1c-configurator-batch-8-3-27/references/platforms.md).
Выбери реальный Designer 8.3.27, допустимую аутентификацию и свежую выгрузку. Никакие проверки XML
на Windows не являются проверкой MergeCfg на macOS/Linux.
