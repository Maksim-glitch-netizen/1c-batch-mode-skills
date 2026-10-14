# Проверенные рабочие сценарии

## 1. Получить основную конфигурацию и обновить базу

Открой: `01-common-cli.md`, `04-repository-read-bind.md`, `06-update-db-cfg.md`, `08-results-errors.md`.

```text
/ConfigurationRepositoryF "<путь-хранилища>"
/ConfigurationRepositoryN "<пользователь>"
/ConfigurationRepositoryP "<пароль>"
/ConfigurationRepositoryUpdateCfg -force
/UpdateDBCfg -Dynamic+
```

Пароль хранилища не указывай, если он не требуется. `/UpdateDBCfg` документирован как допустимая следующая команда после `ConfigurationRepositoryUpdateCfg`.

## 2. Получить расширение и обновить его базовую конфигурацию

```text
/ConfigurationRepositoryF "<путь-хранилища-расширения>"
/ConfigurationRepositoryN "<пользователь>"
/ConfigurationRepositoryP "<пароль>"
/ConfigurationRepositoryUpdateCfg -force -Extension "<имя>"
/UpdateDBCfg -Dynamic+ -Extension "<имя>"
```

`-Extension` указывается отдельно у каждой операции.

## 3. Первая и последующая XML-выгрузка

Первая:

```text
/DumpConfigToFiles "<каталог>" -Format Hierarchical
```

Последующая при подтвержденном `ConfigDumpInfo.xml`:

```text
/DumpConfigToFiles "<тот-же-каталог>" -update -getChanges "<файл-изменений>"
```

## 4. Загрузить известные XML-файлы и обновить базу

```text
/LoadConfigFromFiles "<каталог-xml>" -listFile "<utf8-файл-списка-путей>" -Format Hierarchical
/UpdateDBCfg -Dynamic+
```

Добавляй `-partial` только при загрузке отдельной части объекта.

## 5. Изменение объектов расширения, подключенного к хранилищу

1. Получить актуальное расширение: `ConfigurationRepositoryUpdateCfg -Extension`.
2. Захватить объекты: `ConfigurationRepositoryLock -Objects ... -Extension`.
3. Частично загрузить XML: `LoadConfigFromFiles -files/-listFile -Format ... -Extension`.
4. Проверить расширение.
5. Обновить базу: `UpdateDBCfg -Extension`.
6. Выполнить функциональное тестирование.
7. Поместить объекты: `ConfigurationRepositoryCommit -Objects ... -comment ... -Extension`.

Файл `-Objects` и список XML-файлов являются разными форматами.

## 6. Зарегистрировать новый корневой объект через donor.cf

Открой: `01-common-cli.md`, `02-xml-dump.md`, `03-xml-load.md`, `08-results-errors.md` и
`11-merge-cfg.md`.

1. Подтвердить отсутствие явно заданного `<Тип>.<Имя>` в свежем baseline основной конфигурации.
2. Создать отдельную файловую ИБ с минимальной donor-конфигурацией и только самодостаточным каркасом
   нового объекта.
3. Полностью загрузить donor XML в рабочую конфигурацию файловой ИБ; `UpdateDBCfg` не выполнять.
4. Выгрузить рабочую donor-конфигурацию через `DumpCfg`.
5. Сформировать настройки: `Configuration=DoNotMerge`, целевой объект=
   `GetFromSecondConfiguration`, все остальные объекты donor=`DoNotMerge`.
6. Выполнить один `MergeCfg` в основной конфигурации без опасных параметров по умолчанию.
7. Сразу повторно выгрузить XML основной рабочей конфигурации и подтвердить единственное добавление.
8. Продолжить разработку уже зарегистрированного объекта обычной частичной XML-загрузкой.

Не обновлять конфигурацию БД между регистрацией каркаса и его контрольной XML-выгрузкой.

## Правило остановки

При ненулевом результате, отсутствующем `/DumpResult`, ошибке в `/Out` или отсутствии ожидаемого фактического результата не переходи к следующему шагу.
