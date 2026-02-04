import glob
import os
from collections import defaultdict

# --- НАСТРОЙКА ---
# Укажите путь к директории, где находятся файлы с IP-адресами.
# Пример: INPUT_DIRECTORY = r"C:\path\to\your\ip_files"
# Для текущей директории можно указать "." или ""
INPUT_DIRECTORY = "IPсhecked"
# -----------------

# Проверяем, существует ли указанная директория
if not os.path.isdir(INPUT_DIRECTORY):
    print(f"Ошибка: Указанная директория не существует: {INPUT_DIRECTORY}")
    exit(1)

# Формируем путь к файлам с IP-адресами
file_pattern = os.path.join(INPUT_DIRECTORY, "available_ips_from_*.txt")

# Словарь для отслеживания IP и файлов, в которых они встречаются
ip_file_map = defaultdict(set)

# Словарь для отслеживания дубликатов внутри одного файла
duplicates_in_file = defaultdict(lambda: defaultdict(int))

print(f"Ищем файлы по шаблону: {file_pattern}")
ip_files = glob.glob(file_pattern)

if not ip_files:
    print(f"Файлы по шаблону {file_pattern} не найдены в директории {INPUT_DIRECTORY}.")
    exit(1)

print(f"Найдены файлы: {ip_files}\n")

# Проход по каждому найденному файлу
for filename in ip_files:
    print(f"Обработка файла: {filename}")
    seen_in_current_file = set()
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                # Удаляем пробелы и символы новой строки
                ip = line.strip()
                if not ip:
                    continue  # Пропускаем пустые строки

                # Проверка дубликатов внутри текущего файла
                if ip in seen_in_current_file:
                    duplicates_in_file[filename][ip] += 1
                else:
                    seen_in_current_file.add(ip)

                # Добавляем файл в общий список для этого IP
                ip_file_map[ip].add(os.path.basename(filename)) # Сохраняем только имя файла
    except Exception as e:
        print(f"Ошибка при чтении файла {filename}: {e}")
        continue # Пропускаем файл с ошибкой
    print(f"Файл {filename} обработан.\n")

# Подготовка отчета
report_filename = os.path.join(INPUT_DIRECTORY, "duplicate_report.txt")
print(f"Создание отчета в файле: {report_filename}")

with open(report_filename, 'w', encoding='utf-8') as report_file:
    report_file.write("Отчет о дубликатах IP-адресов\n")
    report_file.write("="*40 + "\n\n")

    # Сначала записываем дубликаты внутри одного файла
    has_duplicates_in_file = False
    for filename, ip_counts in duplicates_in_file.items():
        for ip, extra_count in ip_counts.items():
            report_file.write(f"ПРЕДУПРЕЖДЕНИЕ: IP '{ip}' дублируется {extra_count} раз(а) ВНУТРИ файла '{os.path.basename(filename)}'.\n")
            report_file.write(f"  -> Общий файл, содержащий IP: {os.path.basename(filename)}\n\n")
            has_duplicates_in_file = True

    if not has_duplicates_in_file:
        report_file.write("Дубликаты IP-адресов ВНУТРИ одного файла НЕ НАЙДЕНЫ.\n\n")

    # Затем записываем дубликаты между файлами
    has_duplicates_between_files = False
    for ip, files in ip_file_map.items():
        if len(files) > 1:
            report_file.write(f"ДУБЛИКАТ: IP '{ip}' найден в {len(files)} файле(ах):\n")
            for file_with_ip in sorted(list(files)):
                report_file.write(f"  -> {file_with_ip}\n")
            report_file.write("\n")
            has_duplicates_between_files = True

    if not has_duplicates_between_files:
        report_file.write("Дубликаты IP-адресов МЕЖДУ файлами НЕ НАЙДЕНЫ.\n\n")

    report_file.write("="*40 + "\n")
    report_file.write("Анализ завершен.\n")

print(f"Анализ завершен. Результаты записаны в {report_filename}")

# Вывод краткой сводки в консоль
print("\n--- Краткая сводка ---")
if duplicates_in_file:
    print("Найдены дубликаты внутри отдельных файлов.")
else:
    print("Дубликаты внутри отдельных файлов НЕ НАЙДЕНЫ.")

if any(len(files) > 1 for files in ip_file_map.values()):
    print("Найдены дубликаты IP-адресов между разными файлами.")
else:
    print("Дубликаты IP-адресов между разными файлами НЕ НАЙДЕНЫ.")
