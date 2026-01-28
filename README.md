# Белые списки доменов и IP-адресов в зоне .ru

Проект собирает домены и IP-адреса в зоне .ru для создания белых списков мобильных операторов России.

## Цель проекта

Сбор и проверка доменов и IP-адресов, применяемых операторами мобильной связи при частичном ограничении доступа в интернет («Белые списки»). Собранные данные можно использовать для построения правил маршрутизации для ядра Xray.

## Структура проекта

Для удобства работы с данными «Белые списки» разделены на:

- Списки подсетей, разбитые по категориям — `/IPs`
- Списки проверенных IP-адресов — `/IPсhecked`
- Списки доменов, разбитые по категориям — `/domains`

## Актуальные (проверенные) данные

Проверенные на работоспособность у всех операторов категории (домены) смотри в [`/domains/ru/category-ru`](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/blob/main/domains/ru/category-ru)

Проверенные IP-адреса в БС смотри в [`/IPсhecked`](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/blob/main/IPсhecked)

## Самостоятельная сборка файлов `geosite.dat` и `geoip.dat` для маршрутизации

Инструменты и инструкции по сборке:

- **geosite.dat**: [https://github.com/v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)
- **geoip.dat**: [https://github.com/v2fly/geoip](https://github.com/v2fly/geoip)

## Ссылки для скачивания готовых файлов

Готовые рабочие файлы для Xray:

- **geosite.dat**: [https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/dlc.dat](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/dlc.dat)
- **geoip.dat**: [https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/geoip.dat](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/geoip.dat)

## Категории в наших `geosite.dat` и `geoip.dat`

Для удобства настройки маршрутизации используйте следующие категории:

**В `geosite.dat`:**

- **whitelist-ru (category-ru)**: известные домены, включённые в «Белые списки» у всех операторов
- **category-ads-all**: рекламные домены (AdguardFilterDNS, PeterLoweFilter и v2fly/domain-list-community)
- **private**: приватные домены

**В `geoip.dat`:**

- **whitelist**: все известные и проверенные IP-адреса, включённые в «Белые списки» операторов

**Пример использования категорий** при построении правил маршрутизации можно посмотреть тут - [JSON_example](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/blob/main/JSON_example)