import subprocess
import sys
import os
import re
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Функции для обработки CIDR ---

def generate_ips_from_cidr(cidr_str):
    """Генерирует список IP-адресов из CIDR-диапазона."""
    try:
        network = ipaddress.ip_network(cidr_str, strict=False)
        return [str(host) for host in network.hosts()]
    except ValueError:
        print(f"Предупреждение: Невалидный CIDR '{cidr_str}' проигнорирован.")
        return []

def parse_cidrs_from_content(content):
    """Извлекает CIDR-диапазоны из строки содержимого файла."""
    # Ищем паттерны вида x.x.x.x/y (где x, y - числа)
    cidr_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b'
    cidrs = re.findall(cidr_pattern, content)
    valid_cidrs = []
    for cidr_str in cidrs:
        try:
            ipaddress.ip_network(cidr_str, strict=False)
            valid_cidrs.append(cidr_str)
        except ValueError:
            continue # Пропускаем невалидные
    return valid_cidrs

def process_cidr_file(input_filename, num_threads, results_dir):
    """Обрабатывает файл, содержащий CIDR-диапазоны."""
    print(f"--- Обнаружен формат CIDR в файле: {input_filename} ---")
    try:
        with open(input_filename, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Ошибка: Файл '{input_filename}' не найден.")
        return
    except Exception as e:
        print(f"Ошибка при чтении файла '{input_filename}': {e}")
        return

    cidr_ranges = parse_cidrs_from_content(content)
    if not cidr_ranges:
        print(f"В файле '{input_filename}' не найдено валидных CIDR-диапазонов.")
        return

    print(f"Найдено {len(cidr_ranges)} валидных CIDR-диапазонов в '{input_filename}'.")

    all_ips = []
    for cidr_str in cidr_ranges:
        ips = generate_ips_from_cidr(cidr_str)
        all_ips.extend(ips)

    print(f"Сгенерировано {len(all_ips)} IP-адресов для проверки из '{input_filename}'.")
    if len(all_ips) > 100000: # Предупреждение для очень больших списков (реально это может убить комп)
        print(f"ВНИМАНИЕ: Список IP-адресов из '{input_filename}' очень большой ({len(all_ips)}). Проверка может занять значительное время или убить ваш комп.")

    ping_ip_list(all_ips, input_filename, num_threads, results_dir)


# --- Функции для обработки списка отдельных IP-адресов ---

def parse_ips_from_list_content(content):
    """Извлекает отдельные IP-адреса из строки содержимого файла (по одному на строку)."""
    # Разбиваем содержимое по строкам
    lines = content.splitlines()
    ips = []
    for line in lines:
        # Убираем лишние пробелы и символы новой строки
        ip_candidate = line.strip()
        # Проверяем, является ли строка валидным IP-адресом
        try:
            ipaddress.ip_address(ip_candidate)
            ips.append(ip_candidate)
        except ValueError:
            # Игнорируем строки, которые не являются валидными IP-адресами
            continue
    return ips

def process_ip_list_file(input_filename, num_threads, results_dir):
    """Обрабатывает файл, содержащий список отдельных IP-адресов."""
    print(f"--- Обнаружен формат списка IP-адресов в файле: {input_filename} ---")
    try:
        with open(input_filename, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Ошибка: Файл '{input_filename}' не найден.")
        return
    except Exception as e:
        print(f"Ошибка при чтении файла '{input_filename}': {e}")
        return

    all_ips = parse_ips_from_list_content(content)
    if not all_ips:
        print(f"В файле '{input_filename}' не найдено валидных IP-адресов.")
        return

    print(f"Найдено {len(all_ips)} валидных IP-адресов в '{input_filename}'.")

    # Проверяем, есть ли вообще IP-адреса для пинга, ну а вдруг
    if not all_ips:
        print(f"В файле '{input_filename}' не осталось валидных IP-адресов после фильтрации.")
        return

    ping_ip_list(all_ips, input_filename, num_threads, results_dir)


# --- Общая функция для пинга списка IP ---

def ping_ip(ip):
    """Проверяет доступность IP-адреса."""
    if sys.platform.startswith("win"):
        command = ["ping", "-n", "1", "-w", "3000", ip]  # Тут можно подшаманить Ping для Windows
    else:
        command = ["ping", "-c", "1", "-W", "3", ip]  # А тут можно подшаманить Ping для Linux

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3
        )
        return ip, result.returncode == 0
    except subprocess.TimeoutExpired:
        return ip, False
    except Exception:
        return ip, False

def ping_ip_list(all_ips, original_filename, num_threads, results_dir):
    """Выполняет пинг списка IP-адресов и записывает результаты."""
    available_ips = []

    print(f"Используется {num_threads} потоков для проверки из '{original_filename}'...")
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_ip = {executor.submit(ping_ip, ip): ip for ip in all_ips}
        for future in as_completed(future_to_ip):
            ip, is_reachable = future.result()
            if is_reachable:
                available_ips.append(ip)
                print(f"✅ PING OK: {ip} (из {original_filename})")

    available_filename = f"available_ips_from_{os.path.basename(original_filename)}"  # Ну если уж прям очень хочется, то тут можно поменять маску названия файлов с итогами проверки
    result_filepath = os.path.join(results_dir, available_filename)

    try:
        with open(result_filepath, 'w') as f:
            # Сортируем как IP-адреса IPv4. Чет впадлу заморачиваться с IPv6...
            for ip in sorted(available_ips, key=ipaddress.IPv4Address):
                f.write(ip + '\n')
        print(f"Доступные IP-адреса из '{original_filename}' записаны в '{result_filepath}' ({len(available_ips)} шт.).")
    except Exception as e:
        print(f"Ошибка при записи в файл '{result_filepath}': {e}")

    print(f"--- Обработка файла '{original_filename}' завершена. ---\n")


# --- Определение типа файла и вызов соответствующей функции ---

def determine_file_type(filename):
    """Определяет тип файла на основе его содержимого."""
    try:
        with open(filename, 'r') as f:
            sample_content = f.read(1024) # Читаем первые 1024 байта для определения типа
    except Exception:
        return "unknown"

    # Проверяем на CIDR (например, наличие '/20', '/24' и т.д.)
    if re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b', sample_content):
        return "cidr"

    # Проверяем на список отдельных IP-адресов
    # Читаем весь файл для проверки IP-адресов построчно
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
        ip_count = 0
        for line in lines:
            ip_candidate = line.strip()
            if ip_candidate:
                try:
                    ipaddress.ip_address(ip_candidate)
                    ip_count += 1
                    # Если нашли хотя бы несколько валидных IP в строках, вероятно, это список
                    if ip_count >= 2: # Порог можно изменить
                        return "ip_list"
                except ValueError:
                    continue
        # Если нашли хотя бы один IP, но меньше порога, всё равно считаем списком
        if ip_count >= 1:
            return "ip_list"
    except Exception:
        # Если возникла ошибка при чтении всего файла для этой проверки, возвращаем 'unknown'
        # или можно повторно использовать sample_content, но это менее точно для списка
        pass

    return "unknown"


def main():

    # --- Основные настройки скрипта ---

    # --- Директория для поиска файлов с IP-адресами ---
    INPUT_DIRECTORY = "IPs"  # "." означает текущую директорию.
    # ---------------------------------------------

    # --- Ручное управление количеством потоков ---
    NUM_THREADS = 300  # Лучше начинать со 100
    # ---------------------------------------------

    # --- Директория для сохранения успешно проверенных IP-адресов ---
    RESULTS_DIR = "IPchecked"
    # ---------------------------------------------
    
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print(f"Проверяем/создаём директорию для результатов: {RESULTS_DIR}")
    print(f"Поиск файлов .txt в директории: {INPUT_DIRECTORY}")

    txt_files = [f for f in os.listdir(INPUT_DIRECTORY) if f.lower().endswith('.txt')]
    if not txt_files:
        print(f"В директории '{INPUT_DIRECTORY}' не найдено файлов с расширением .txt")
        return

    print(f"Найдены следующие файлы для обработки: {txt_files}\n")

    for filename in txt_files:
        full_path = os.path.join(INPUT_DIRECTORY, filename)
        file_type = determine_file_type(full_path)
        print(f"Анализ файла '{full_path}': тип - {file_type}")

        if file_type == "cidr":
            process_cidr_file(full_path, NUM_THREADS, RESULTS_DIR)
        elif file_type == "ip_list":
            process_ip_list_file(full_path, NUM_THREADS, RESULTS_DIR)
        else:
            print(f"Тип файла '{full_path}' не распознан. Пропускаю.\n")


if __name__ == "__main__":
    main()
