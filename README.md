# Белые списки доменов и IP-адресов в зоне .ru

[![Last Updated](https://img.shields.io/badge/last_updated-dynamic-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

Проект собирает, проверяет и поддерживает актуальные белые списки доменов и IP-адресов зоны .ru для мобильных операторов России. Данные используются для настройки маршрутизации в Xray, V2Ray и совместимых прокси-ядрах.

## 📋 Оглавление

- [Цель проекта](#-цель-проекта)
- [Структура проекта](#-структура-проекта)
- [Скрипты автоматизации](#-скрипты-автоматизации)
- [Актуальные данные](#-актуальные-данные)
- [Готовые файлы для скачивания](#-готовые-файлы-для-скачивания)
- [Категории для маршрутизации](#-категории-для-маршрутизации)
- [Пример конфигурации](#-пример-конфигурации)
- [Самостоятельная сборка](#-самостоятельная-сборка)
- [Вклад в проект](#-вклад-в-проект)

## 🎯 Цель проекта

Сбор, верификация и поддержка актуальных списков доменов и IP-адресов, которые российские мобильные операторы включают в «Белые списки» при частичном ограничении доступа в интернет. 

**Основные задачи:**
- Автоматическая проверка доступности доменов и IP-адресов
- Фильтрация неработающих ресурсов
- Формирование готовых баз для geosite.dat и geoip.dat
- Предоставление актуальных данных для настройки маршрутизации

## 📁 Структура проекта

```
/workspace
├── domains/                    # Списки доменов
│   ├── ru/                     # Домены зоны .ru по категориям
│   │   ├── category-ru         # Агрегированный список всех российских доменов
│   │   ├── yandex.txt          # Домены Яндекса
│   │   ├── vk.txt              # Домены ВКонтакте
│   │   └── ...                 # Другие категории (31 файл)
│   └── ads/                    # Рекламные домены
│       ├── category-ads-all    # Агрегированный список рекламы
│       ├── AdguardFilterDNS    # Список от AdGuard
│       ├── PeterLoweFilter     # Список от Peter Lowe
│       └── ...                 # Другие источники рекламы
│
├── IPs/                        # Исходные списки подсетей (CIDR)
│   ├── yandex.txt              # Подсети Яндекса
│   ├── vk.txt                  # Подсети ВКонтакте
│   └── ...                     # Другие категории (31 файл)
│
├── IPchecked/                  # Проверенные отдельные IP-адреса
│   ├── available_ips_from_yandex.txt
│   ├── available_ips_from_vk.txt
│   └── ...                     # Результаты проверки ping
│
├── reports/                    # Отчёты проверки доменов
│   ├── report_all.csv          # Сводный отчёт по всем доменам
│   ├── report_yandex.csv       # Отчёт по категории Yandex
│   └── ...                     # Отчёты по каждой категории
│
├── check-domains.py            # Скрипт проверки доменов
├── check_ips_cidr.py           # Скрипт проверки IP из CIDR
├── check_ip_duplicates.py      # Поиск дубликатов IP
├── JSON_example/               # Примеры конфигураций
├── ROUTING_HAPP                # Конфигурация для HAPP
└── README.md                   # Документация
```

## 🛠 Скрипты автоматизации

### 1. `check-domains.py` — Проверка доступности доменов

**Назначение:** Асинхронная проверка HTTP/HTTPS доступности доменов с браузерной эмуляцией.

**Возможности:**
- Параллельная проверка с настраиваемой конкурентностью
- DNS-резолвинг через Яндекс.DNS (77.88.8.8, 77.88.8.1) или системный DNS
- Эмуляция браузера (User-Agent, заголовки, cookies)
- Автоматическое комментирование неработающих доменов
- Генерация CSV-отчётов с детализацией статусов

**Статусы доменов:**
| Статус | Описание | Действие |
|--------|----------|----------|
| ✅ OK | Домен доступен (200-399) | Остаётся активным |
| ❌ RST | Connection refused | Комментируется |
| ⏱ TIMEOUT | Превышено время ожидания | Комментируется |
| 🔐 SSL_ERR | Ошибка SSL handshake | Комментируется |
| 🌐 DNS_ERR | Домен не резолвится | Комментируется |
| ⚠ HTTP_ERR | HTTP ошибка (4xx, 5xx) | **Не комментируется** |

**Использование:**
```bash
# Проверка доменов в директории domains/ru
python3 check-domains.py domains/ru -o reports -c 5

# Тихий режим без модификации файлов
python3 check-domains.py domains/ru --quiet --no-modify

# Использование системного DNS
python3 check-domains.py domains/ru --system-dns

# Исключение категорий
python3 check-domains.py domains/ru -e whitelist-ru private
```

**Параметры:**
- `directory` — директория со списками доменов (по умолчанию: `domains/ru`)
- `-o, --output` — директория для отчётов (по умолчанию: `reports`)
- `-c, --concurrency` — количество параллельных потоков (по умолчанию: 5)
- `-q, --quiet` — тихий режим
- `--no-modify` — не модифицировать исходные файлы
- `-e, --exclude` — исключить категории из проверки
- `--dns` — кастомные DNS-серверы
- `--system-dns` — использовать системный DNS

---

### 2. `check_ips_cidr.py` — Проверка IP-адресов из CIDR

**Назначение:** Преобразование CIDR-диапазонов в отдельные IP и проверка их доступности через ping.

**Возможности:**
- Автоматическое определение формата (CIDR или список IP)
- Многопоточная проверка (до 300 потоков)
- Генерация списков доступных IP-адресов
- Сортировка результатов по IPv4

**Использование:**
```bash
# Запуск проверки всех файлов в директории IPs/
python3 check_ips_cidr.py
```

**Конфигурация (внутри скрипта):**
```python
INPUT_DIRECTORY = "IPs"      # Директория с исходными CIDR
NUM_THREADS = 300            # Количество потоков
RESULTS_DIR = "IPchecked"    # Директория результатов
```

**Результат:** Файлы вида `available_ips_from_<category>.txt` в директории `IPchecked/`

---

### 3. `check_ip_duplicates.py` — Поиск дубликатов IP

**Назначение:** Обнаружение дублирующихся IP-адресов между файлами и внутри одного файла.

**Использование:**
```bash
# Проверка директории IPchecked/
python3 check_ip_duplicates.py
```

**Результат:** Отчёт `duplicate_report.txt` с информацией о дубликатах.

## ✅ Актуальные данные

### Проверенные домены
- **Основной список:** [`domains/ru/category-ru`](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/blob/main/domains/ru/category-ru)
- **Рекламные домены:** [`domains/ads/category-ads-all`](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/blob/main/domains/ads/category-ads-all)

### Проверенные IP-адреса
- **Все проверенные IP:** [`IPchecked/`](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/blob/main/IPchecked)

### Отчёты проверки
- **Сводный отчёт:** [`reports/report_all.csv`](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/blob/main/reports/report_all.csv)
- **Отчёты по категориям:** `reports/report_<category>.csv`

## 📥 Готовые файлы для скачивания

Автоматически обновляемые файлы для Xray/V2Ray:

| Файл | Описание | Ссылка |
|------|----------|--------|
| **dlc.dat** | Geosite базы доменов | [Скачать](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/dlc.dat) |
| **geoip.dat** | GeoIP базы IP-адресов | [Скачать](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/geoip.dat) |

## 🗂 Категории для маршрутизации

### В `geosite.dat`:

| Категория | Описание | Пример использования |
|-----------|----------|---------------------|
| `geosite:category-ru` | Российские домены из белого списка | Прямое подключение |
| `geosite:private` | Приватные домены (.local, .lan) | Прямое подключение |
| `geosite:category-ads-all` | Рекламные домены | Блокировка |

### В `geoip.dat`:

| Категория | Описание | Пример использования |
|-----------|----------|---------------------|
| `geoip:whitelist` | Проверенные IP белого списка | Прямое подключение |

## ⚙️ Пример конфигурации

### Для Xray/V2Ray (JSON)

```json
{
  "routing": {
    "domainStrategy": "IPIfNonMatch",
    "rules": [
      {
        "type": "field",
        "outboundTag": "direct",
        "domain": ["geosite:private", "geosite:category-ru"]
      },
      {
        "type": "field",
        "outboundTag": "direct",
        "ip": ["geoip:whitelist"]
      },
      {
        "type": "field",
        "outboundTag": "block",
        "domain": ["geosite:category-ads-all"]
      }
    ]
  }
}
```

### Для HAPP (Base64)

Готовая конфигурация доступна в файле [`ROUTING_HAPP`](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/blob/main/ROUTING_HAPP).

**Расшифрованная конфигурация:**
```json
{
  "Name": "LTE-БС",
  "GlobalProxy": "true",
  "RouteOrder": "block-direct-proxy",
  "DirectSites": ["geosite:private", "geosite:category-ru"],
  "DirectIp": ["geoip:whitelist"],
  "BlockSites": ["geosite:category-ads-all"],
  "DomainStrategy": "IPIfNonMatch",
  "RemoteDNSType": "DoH",
  "RemoteDNSDomain": "https://cloudflare-dns.com/dns-query",
  "DomesticDNSType": "DoH",
  "DomesticDNSDomain": "https://common.dot.dns.yandex.net/dns-query"
}
```

📄 **Дополнительные примеры:** [`JSON_example/`](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/blob/main/JSON_example)

## 🔧 Самостоятельная сборка

### Сборка geosite.dat

1. Клонируйте репозиторий [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)
2. Добавьте файлы доменов из `domains/ru/` и `domains/ads/`
3. Запустите компилятор:
```bash
go run ./generator --outputdir=output
```

### Сборка geoip.dat

1. Клонируйте репозиторий [v2fly/geoip](https://github.com/v2fly/geoip)
2. Преобразуйте проверенные IP из `IPchecked/` в формат MMDB
3. Запустите компилятор:
```bash
go run main.go -inputdir=IPchecked -outputdir=output
```

### Инструменты сборки

- **geosite.dat:** [https://github.com/v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)
- **geoip.dat:** [https://github.com/v2fly/geoip](https://github.com/v2fly/geoip)

## 🤝 Вклад в проект

### Как добавить новый домен/IP

1. Добавьте домен в соответствующий файл в `domains/ru/<category>`
2. Добавьте CIDR-диапазон в `IPs/<category>.txt`
3. Запустите проверку:
   ```bash
   python3 check-domains.py domains/ru
   python3 check_ips_cidr.py
   ```
4. Создайте Pull Request с результатами проверки

### Требования к данным

- **Домены:** Только рабочие HTTPS-ресурсы
- **IP-адреса:** Только подтверждённые CIDR-диапазоны организаций
- **Категории:** Логическая группировка по принадлежности

## 📊 Статистика проекта

| Тип данных | Количество | Расположение |
|------------|------------|--------------|
| Категорий доменов | 31+ | `domains/ru/` |
| Рекламных фильтров | 3+ | `domains/ads/` |
| CIDR-диапазонов | 31+ | `IPs/` |
| Проверенных IP | Варьируется | `IPchecked/` |

## ⚠️ Важные замечания

1. **HTTP_ERR не является блокировкой** — домены со статусом HTTP_ERR (4xx, 5xx) остаются активными, так как сервер отвечает
2. **Автоматическое обновление** — рекомендуется регулярно запускать скрипты проверки
3. **DNS-серверы** — по умолчанию используются Яндекс.DNS (77.88.8.8, 77.88.8.1)
4. **SSL проверки** — скрипт использует `ssl=False` для обхода проблем с сертификатами

## 📄 Лицензия

MIT License — свободное использование с указанием авторства.

## 🔗 Ссылки

- **Репозиторий проекта:** [GitHub](https://github.com/kirilllavrov/RU-domain-list-for-whitelist)
- **V2Fly Domain List:** [github.com/v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)
- **V2Fly GeoIP:** [github.com/v2fly/geoip](https://github.com/v2fly/geoip)
- **Xray Core:** [github.com/XTLS/Xray-core](https://github.com/XTLS/Xray-core)

---

*Проект поддерживается сообществом. Актуальность данных зависит от регулярности проверок.*