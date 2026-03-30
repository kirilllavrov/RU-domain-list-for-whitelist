#!/usr/bin/env python3
import asyncio
import aiohttp
import csv
import sys
import os
import time
import socket
import argparse
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Set
from pathlib import Path

# ✅ Полная тишина в логах
logging.getLogger('aiohttp').setLevel(logging.CRITICAL)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logging.getLogger('aiodns').setLevel(logging.CRITICAL)

# === КОНФИГУРАЦИЯ ===
CONFIG = {
    "timeout_connect": 40,
    "timeout_total": 40,
    "timeout_dns": 30,
    "concurrency": 5,
    "headers": {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Linux"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
    },
    "dns_servers": ["77.88.8.8", "77.88.8.1"],
}

ICONS = {"OK": "✅", "RST": "❌", "TIMEOUT": "⏱", "SSL_ERR": "🔐", "HTTP_ERR": "⚠", "DNS_ERR": "🌐", "UNKNOWN": "❓"}
FAILED_STATUSES = {"DNS_ERR", "RST", "SSL_ERR", "TIMEOUT", "UNREACH"}
DEFAULT_EXCLUDES = {"whitelist-ru", "private", "category-ru"}

def classify_error(error: Exception) -> Tuple[str, str]:
    err_str = str(error).lower()
    
    if isinstance(error, aiohttp.ClientResponseError):
        return "HTTP_ERR", f"Response error {error.status}"
    if isinstance(error, socket.gaierror):
        return "DNS_ERR", "Domain not resolved"
    if isinstance(error, OSError) and "timeout" in err_str:
        return "DNS_ERR", "DNS timeout"
    if "no address" in err_str or "name or service not known" in err_str:
        return "DNS_ERR", "Domain not resolved"
    if "timeout" in err_str or "errno 110" in err_str:
        return "TIMEOUT", "Connection timed out"
    if "refused" in err_str or "errno 111" in err_str:
        return "RST", "Connection refused"
    if "ssl" in err_str or "certificate" in err_str or "handshake" in err_str:
        return "SSL_ERR", "SSL handshake failed"
    if "reset" in err_str or "errno 104" in err_str:
        return "RST", "Connection reset by peer"
    if "unreachable" in err_str or "no route" in err_str:
        return "UNREACH", "Host unreachable"
    return "UNKNOWN", f"{type(error).__name__}"

def extract_domain(line: str) -> str:
    line = line.strip()
    if not line:
        return ""
    if line.startswith('#'):
        line = line[1:].strip()
    if not line:
        return ""
    domain = line.replace('https://', '').replace('http://', '').split('/')[0].split('?')[0].split('#')[0].strip()
    return domain

def is_domain_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    content = stripped.lstrip('#').strip()
    if not content:
        return False
    if '.' in content.split('#')[0]:
        return True
    return False

def get_files_to_process(directory: str, excludes: Set[str]) -> List[Path]:
    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"❌ Директория '{directory}' не найдена")
        sys.exit(1)
    
    files = []
    for f in dir_path.iterdir():
        if f.is_file():
            name_without_ext = f.stem
            if name_without_ext not in excludes:
                files.append(f)
    
    return sorted(files)

def preprocess_file(filepath: Path) -> List[Dict]:
    """Раскомментирует все домены в файле"""
    lines_data = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            original = line
            stripped = line.rstrip('\n\r')
            
            if is_domain_line(stripped):
                domain = extract_domain(stripped)
                was_commented = stripped.strip().startswith('#')
                lines_data.append({
                    'line_num': line_num,
                    'original': original,
                    'domain': domain,
                    'was_commented': was_commented,
                    'is_domain': True,
                    'status': None,
                })
            else:
                lines_data.append({
                    'line_num': line_num,
                    'original': original,
                    'domain': None,
                    'was_commented': False,
                    'is_domain': False,
                    'status': None,
                })
    
    # ✅ ИСПРАВЛЕНО: lines_data + двоеточие
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in lines_data:  # ← Было: lines_ (ошибка)
            if item['is_domain']:
                f.write(item['domain'] + '\n')
            else:
                f.write(item['original'])
    
    return lines_data

def postprocess_all_files(domain_all_occurrences: Dict[str, List[Tuple[Path, int]]], results: Dict[str, dict]):
    """Закомментировать неудачные домены во всех файлах"""
    file_domains: Dict[Path, Set[str]] = {}
    for domain, occurrences in domain_all_occurrences.items():
        result = results.get(domain, {})
        status = result.get('status', 'UNKNOWN')
        if status in FAILED_STATUSES:
            for filepath, _ in occurrences:
                if filepath not in file_domains:
                    file_domains[filepath] = set()
                file_domains[filepath].add(domain)
    
    for filepath, domains_to_comment in file_domains.items():
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for line in lines:
                domain = extract_domain(line)
                if domain in domains_to_comment:
                    f.write(f"#{domain}\n")
                else:
                    f.write(line)

async def check_domain(session: aiohttp.ClientSession, domain: str, sem: asyncio.Semaphore) -> dict:
    """Проверка домена через GET с браузерными заголовками"""
    async with sem:
        res = {"domain": domain, "status": "", "code": 0, "method": "GET", "rtt_ms": 0, "details": ""}
        
        url = f"https://{domain}"
        start = time.time()
        
        try:
            async with session.get(
                url,
                allow_redirects=True,
                ssl=False,
                timeout=aiohttp.ClientTimeout(connect=CONFIG["timeout_connect"], total=CONFIG["timeout_total"]),
                headers=CONFIG["headers"]
            ) as resp:
                rtt = (time.time() - start) * 1000
                res["rtt_ms"] = round(rtt, 1)
                res["code"] = resp.status
                
                if 200 <= resp.status < 400:
                    res["status"] = "OK"
                    res["details"] = f"{resp.reason}"
                else:
                    res["status"] = "HTTP_ERR"
                    res["details"] = f"{resp.status} {resp.reason}"
                    
        except Exception as e:
            res["status"], res["details"] = classify_error(e)
        
        return res

async def run_checker(domains: List[str], connector: aiohttp.TCPConnector, verbose: bool = True) -> Dict[str, dict]:
    """Основная функция проверки"""
    results = {}
    
    print(f"🔍 Этап 1/2: DNS-резолв ({len(domains)} доменов)...")
    
    dns_sem = asyncio.Semaphore(CONFIG["concurrency"] * 2)
    
    async def resolve_with_connector(d: str):
        async with dns_sem:
            try:
                await asyncio.wait_for(
                    connector._resolve_host(d, 443, traces=[]),
                    timeout=CONFIG["timeout_dns"]
                )
                return (d, True)
            except Exception:
                return (d, False)
    
    dns_tasks = [resolve_with_connector(d) for d in domains]
    dns_results = {}
    
    completed = 0
    for coro in asyncio.as_completed(dns_tasks):
        domain, resolved = await coro
        dns_results[domain] = resolved
        completed += 1
        if verbose and completed % 200 == 0:
            print(f"  → DNS: {completed}/{len(domains)}")
    
    dns_ok = sum(1 for v in dns_results.values() if v)
    print(f"  ✅ Резолвятся: {dns_ok} | ❌ Не резолвятся: {len(domains) - dns_ok}")
    
    for domain, resolved in dns_results.items():
        if not resolved:
            results[domain] = {"domain": domain, "status": "DNS_ERR", "code": 0, "method": "-", "rtt_ms": 0, "details": "Domain not resolved"}
    
    http_domains = [d for d, r in dns_results.items() if r]
    if http_domains:
        print(f"\n🔍 Этап 2/2: HTTP-проверка ({len(http_domains)} доменов)...")
        print(f"   🌐 Режим: Browser emulation (GET + Cookies + Keep-Alive)")
        
        cookie_jar = aiohttp.CookieJar()
        async with aiohttp.ClientSession(connector=connector, cookie_jar=cookie_jar) as session:
            http_sem = asyncio.Semaphore(CONFIG["concurrency"])
            http_tasks = [check_domain(session, d, http_sem) for d in http_domains]
            
            completed = 0
            start_time = time.time()
            
            for coro in asyncio.as_completed(http_tasks):
                res = await coro
                results[res['domain']] = res
                completed += 1
                
                if verbose:
                    icon = ICONS.get(res['status'], "❓")
                    print(f"[{completed}/{len(http_domains)}] {icon} {res['domain']:<45} {res['status']:<10} {res['method']:<4} {res['details']}")
                
                if completed % 100 == 0:
                    elapsed = time.time() - start_time
                    speed = completed / elapsed if elapsed > 0 else 0
                    print(f"  → HTTP: {completed}/{len(http_domains)} ({speed:.1f} доменов/сек)")
    
    return results

def load_domains_from_files(files: List[Path]) -> Tuple[List[str], Dict[str, Path], Dict[str, List[Tuple[Path, int]]]]:
    """Загрузить домены из всех файлов с сохранением всех вхождений"""
    domains = []
    domain_to_file = {}
    domain_all_occurrences = {}
    
    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                domain = extract_domain(line)
                if domain:
                    if domain not in domain_all_occurrences:
                        domain_all_occurrences[domain] = []
                    domain_all_occurrences[domain].append((filepath, line_num))
                    
                    if domain not in domain_to_file:
                        domains.append(domain)
                        domain_to_file[domain] = filepath
    
    return domains, domain_to_file, domain_all_occurrences

def save_results_per_file(domain_all_occurrences: Dict[str, List[Tuple[Path, int]]], results: Dict[str, dict], output_dir: str):
    """Сохранить CSV отчёты для каждого файла"""
    os.makedirs(output_dir, exist_ok=True)
    
    file_results: Dict[str, List[dict]] = {}
    for domain, occurrences in domain_all_occurrences.items():
        if domain in results:
            for filepath, _ in occurrences:
                key = filepath.name
                if key not in file_results:
                    file_results[key] = []
                file_results[key].append(results[domain])
    
    for filename, res_list in file_results.items():
        csv_path = os.path.join(output_dir, f"report_{filename}.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'domain', 'status', 'code', 'method', 'rtt_ms', 'details'])
            for r in res_list:
                writer.writerow([
                    datetime.now().strftime("%H:%M:%S"),
                    r['domain'], r['status'], r['code'],
                    r['method'], r['rtt_ms'], r['details']
                ])
    
    all_csv = os.path.join(output_dir, "report_all.csv")
    with open(all_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'domain', 'status', 'code', 'method', 'rtt_ms', 'details', 'source_file'])
        for domain, occurrences in domain_all_occurrences.items():
            if domain in results:
                r = results[domain]
                for filepath, _ in occurrences:
                    writer.writerow([
                        datetime.now().strftime("%H:%M:%S"),
                        r['domain'], r['status'], r['code'],
                        r['method'], r['rtt_ms'], r['details'], filepath.name
                    ])

async def main():
    parser = argparse.ArgumentParser(description='DPI Checker v14 (валидация переменных)')
    parser.add_argument('directory', nargs='?', default='domains/ru', help='Директория со списками')
    parser.add_argument('-o', '--output', default='reports', help='Директория отчётов')
    parser.add_argument('-c', '--concurrency', type=int, default=CONFIG["concurrency"], help='Параллельных запросов')
    parser.add_argument('-q', '--quiet', action='store_true', help='Тихий режим')
    parser.add_argument('--no-modify', action='store_true', help='Не модифицировать файлы')
    parser.add_argument('-e', '--exclude', nargs='+', default=[], help='Исключения')
    parser.add_argument('--dns', nargs='+', default=None, help='DNS-серверы (переопределение)')
    parser.add_argument('--system-dns', action='store_true', help='✅ Использовать системный DNS')
    args = parser.parse_args()
    
    # Переопределение DNS
    if args.dns:
        CONFIG["dns_servers"] = args.dns
    
    directory = args.directory
    excludes = DEFAULT_EXCLUDES.union(set(args.exclude))
    
    print("⚙️  Конфигурация:")
    print(f"   timeout_connect: {CONFIG['timeout_connect']}s")
    print(f"   timeout_total:   {CONFIG['timeout_total']}s")
    print(f"   timeout_dns:     {CONFIG['timeout_dns']}s")
    print(f"   concurrency:     {CONFIG['concurrency']}")
    if args.system_dns:
        print(f"   dns:             SYSTEM (из /etc/resolv.conf) ✅")
    else:
        print(f"   dns_servers:     {', '.join(CONFIG['dns_servers'])}")
    print(f"   mode:            Browser GET (Cookies + Keep-Alive)")
    print("-" * 85)
    
    print(f"📂 Директория: {directory}")
    print(f"🚫 Исключения: {', '.join(excludes)}")
    print("-" * 85)
    
    files = get_files_to_process(directory, excludes)
    if not files:
        print("❌ Нет файлов для обработки")
        sys.exit(1)
    
    print(f"📁 Файлов для проверки: {len(files)}")
    for f in files:
        print(f"   - {f.name}")
    print("-" * 85)
    
    if not args.no_modify:
        print("⚙️  Пре-процессинг: раскомментирование доменов...")
        for filepath in files:
            preprocess_file(filepath)
        print("  ✅ Готово")
    else:
        print("⚠️  Пропуск модификации файлов (--no-modify)")
    
    print("-" * 85)
    
    domains, domain_to_file, domain_all_occurrences = load_domains_from_files(files)
    print(f"📋 Доменов: {len(domains)} | 🚀 Потоков: {CONFIG['concurrency']}")
    print("-" * 85)
    
    # ✅ Создание connector: системный DNS или кастомный
    try:
        if args.system_dns:
            connector = aiohttp.TCPConnector(
                limit=CONFIG["concurrency"],
                ttl_dns_cache=300,
                use_dns_cache=True,
                enable_cleanup_closed=True,
            )
            print("🌐 DNS: Системный резолвер (/etc/resolv.conf)")
        else:
            resolver = aiohttp.AsyncResolver(nameservers=CONFIG["dns_servers"])
            connector = aiohttp.TCPConnector(
                limit=CONFIG["concurrency"],
                ttl_dns_cache=300,
                use_dns_cache=True,
                resolver=resolver,
                enable_cleanup_closed=True,
            )
            print(f"🌐 DNS: Кастомный ({', '.join(CONFIG['dns_servers'])})")
    except Exception as e:
        print(f"❌ Ошибка создания connector: {e}")
        print("💡 Попробуйте --system-dns или --dns 77.88.8.8 77.88.8.1")
        sys.exit(1)
    
    start = time.time()
    results = await run_checker(domains, connector, verbose=not args.quiet)
    
    elapsed = time.time() - start
    print("-" * 85)
    print(f"✅ Готово за {elapsed:.1f} сек. ({len(domains)/elapsed:.1f} доменов/сек)")
    
    print(f"\n💾 Сохранение отчётов в {args.output}/...")
    save_results_per_file(domain_all_occurrences, results, args.output)
    print("  ✅ Отчёты сохранены")
    
    if not args.no_modify:
        print("\n⚙️  Пост-процессинг: комментирование неудачных доменов...")
        postprocess_all_files(domain_all_occurrences, results)
        
        failed_count = sum(1 for r in results.values() if r['status'] in FAILED_STATUSES)
        print(f"  ✅ Закомментировано: {failed_count} доменов")
    
    print("\n📊 Общая статистика:")
    status_counts = {}
    for r in results.values():
        status = r['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        icon = ICONS.get(status, "❓")
        print(f"  {icon} {status}: {count}")
    
    http_err_count = status_counts.get("HTTP_ERR", 0)
    if http_err_count > 0:
        print(f"\n⚠️  HTTP_ERR ({http_err_count}) — сервер ответил, это НЕ блокировка")
        print(f"   Эти домены НЕ будут закомментированы")
    
    await connector.close()

if __name__ == "__main__":
    asyncio.run(main())
