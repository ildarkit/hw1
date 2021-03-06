# Log Analyzer

## Основная функциональность:
- Скрипт обрабатывает при запуске последний лог в LOG_DIR. То есть скрипт читает лог, парсит нужные поля,
считает необходимую статистику по url'ам и рендерит шаблон report.html.
- Если удачно обработал, то работу не переделывает при повторном запуске. Готовые отчеты лежат в REPORT_DIR.
В отчет попадает REPORT_SIZE URL'ов с наибольшим суммарным временем обработки (time_sum).
- В переменной config находится конфиг по умолчанию. Скрипт считывает конфиг из некоего файла
(например /usr/local/etc/log_nalyzer.conf по умолчанию), где дефолтные опции можно переопределить.
Через параметр --config можно указать конфиг из другого файла.

## Мониторинг:
- Скрипт пишет логи через библиотеку logging в формате '[%(asctime)s] %(levelname).1s %(message)s' c датой в виде
'%Y.%m.%d %H:%M:%S' с уровнями info, error и exception. Путь до логфайла указывается в конфиге, если не указан, лог пишется в stdout.
- По окончнию (успешному) работы, скрипт создает (обновляет) ts-файл по пути, заданному в конфиге
(например /var/tmp/log_nalyzer.ts по умолчанию). Внутри файлика находится timestamp времени окончания работы,
mtime файлика должен быть равен этому таймстемпу.

### Логи:
- Шаблон названия gzip лога nginx-access-ui.log-%Y%m%d.gz
- логи могут быть и plain и gzip
- лог ротируется раз в день
- логи интерфейса лежат в папке с логами других сервисов

### В отчет входит:
- count - сколько раз встречается URL, абсолютное значение
- count_perc - сколько раз встречается URL, в процентнах относительно общего числа запросов
- time_sum - суммарный $request_time для данного URL'а, абсолютное значение
- time_perc - суммарный $request_time для данного URL'а, в процентах относительно общего $request_time всех запросов
- time_avg - средний $request_time для данного URL'а
- time_max - максимальный $request_time для данного URL'а
- time_med - медиана $request_time для данного URL'а

