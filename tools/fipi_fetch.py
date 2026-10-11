"""Выгрузка условий из открытого банка ФИПИ.

    python3 tools/fipi_fetch.py --pages 3
    python3 tools/fipi_fetch.py --subject math_base --pages 5 --delay 3

Кладёт сырые страницы в `content/_raw/fipi/<subject>/page_NNN.html` и картинки
рядом, в `img/`. Ничего не разбирает — разбор в `fipi_parse.py`, чтобы можно было
переразобрать уже скачанное, не дёргая сайт заново.

Как устроен банк (проверено на живом сайте 25.08.2026):
  * страница `bank/index.php` — только оболочка, задачи грузятся в iframe;
  * iframe шлёт POST на `bank/questions.php` с полями фильтра, ответ — HTML
    в кодировке windows-1251, по `pagesize` задач на страницу;
  * листание — тем же POST с полем `page`;
  * каждая задача лежит в `div.qblock` и содержит скрытое поле `guid` —
    это её постоянный идентификатор в банке;
  * **ответов в выдаче нет**: форма отправляет ответ на сервер, а ключ
    остаётся у ФИПИ. Ответы берём не отсюда (см. docs/CONTENT.md).

Скачивание намеренно медленное: это чужой публичный сайт, а не наш API.
"""

from __future__ import annotations

import argparse
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import certifi
except ImportError:  # на голой системе сертификаты берём системные
    certifi = None

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "content" / "_raw" / "fipi"

HOST = "https://ege.fipi.ru"
QUESTIONS = f"{HOST}/bank/questions.php"

# GUID проекта = предмет в банке. Свериться можно на bank/index.php:
# у каждого предмета в onclick лежит selectProject("<GUID>").
PROJECTS = {
    "math_prof": "AC437B34557F88EA4115D2F374B0A07B",
    "math_base": "E040A72A1A3DABA14C90C97E0B6EE7DC",
    "rus": "AF0ED3F2557F8FFC4C06F80B6803FD26",
    "inf": "B9ACA5BBB2E19E434CD6BEC25284C67F",
}

# Ровно те поля, что шлёт сама страница. Пустые оставляем пустыми: без них
# выдача приходит пустой.
BASE_FORM = {
    "search": "1",
    "pagesize": "10",
    "theme": "",
    "qlevel": "",
    "qkind": "",
    "qsstruct": "",
    "qpos": "",
    "qid": "",
    "zid": "",
    "solved": "",
    "favorite": "",
    "blind": "",
}

# Заголовки ходят в latin-1, поэтому подпись латиницей.
UA = "Botalka/0.1 (educational project; collecting task statements)"


# ege.fipi.ru отдаёт только свой сертификат, без промежуточного GlobalSign.
# Браузер и curl дотягивают недостающее звено сами (по ссылке AIA внутри
# сертификата), а питон так не умеет — поэтому подкладываем звено руками.
INTERMEDIATE_URL = "http://secure.globalsign.com/cacert/gsgccr3dvtlsca2020.crt"
CERT_CACHE = ROOT / "tools" / "_certs" / "gsgccr3dvtlsca2020.pem"

_CACHED_CTX: ssl.SSLContext | None = None


def _intermediate() -> Path:
    """Скачивает промежуточный сертификат один раз и кладёт рядом с инструментом."""
    if CERT_CACHE.exists():
        return CERT_CACHE

    CERT_CACHE.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(INTERMEDIATE_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=30) as resp:  # http, проверять нечего
        der = resp.read()

    pem = ssl.DER_cert_to_PEM_cert(der)
    CERT_CACHE.write_text(pem, encoding="ascii")
    return CERT_CACHE


def _ctx() -> ssl.SSLContext:
    global _CACHED_CTX
    if _CACHED_CTX is None:
        context = ssl.create_default_context(cafile=certifi.where() if certifi else None)
        context.load_verify_locations(cafile=str(_intermediate()))
        _CACHED_CTX = context
    return _CACHED_CTX


# Сайт периодически отваливается по таймауту рукопожатия — не повод терять
# всю выгрузку, поэтому повторяем с нарастающей паузой.
RETRIES = 4


def _retry(action, what: str):
    for attempt in range(1, RETRIES + 1):
        try:
            return action()
        except Exception as error:
            if attempt == RETRIES:
                raise
            pause = 5 * attempt
            print(f"  {what}: {type(error).__name__}, повтор через {pause} с "
                  f"({attempt} из {RETRIES - 1})")
            time.sleep(pause)
    return None


def _post(url: str, form: dict[str, str], timeout: int = 40) -> str:
    data = urllib.parse.urlencode(form, encoding="windows-1251").encode()

    def once() -> str:
        req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as resp:
            return resp.read().decode("windows-1251", errors="replace")

    return _retry(once, "страница")


def _get(url: str, timeout: int = 40) -> bytes:
    def once() -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as resp:
            return resp.read()

    return _retry(once, "картинка")


def total_count(html: str) -> int | None:
    """Сколько всего задач по текущему фильтру — банк пишет это в шапке."""
    match = re.search(r"Кол-во заданий:\s*(?:<[^>]+>\s*)*(\d+)", html)
    return int(match.group(1)) if match else None


def image_urls(html: str, project: str) -> list[str]:
    """Картинки условия. В HTML они вставляются джаваскриптом, поэтому
    выдёргиваем по пути, а не по тегу img."""
    # В путях встречается «(copy1)», поэтому скобки из класса символов исключать
    # нельзя — иначе путь обрезается и картинка не находится.
    found = re.findall(r"(docs/[A-F0-9]+/questions/[^'\"]+?\.(?:png|jpg|gif))", html, re.I)
    return sorted({f"{HOST}/{urllib.parse.quote(path, safe='/()')}" for path in found})


def fetch_images(subject: str, delay: float) -> None:
    """Докачивает картинки по уже сохранённым страницам.

    Нужен отдельным проходом, потому что выгрузка пропускает скачанные страницы
    целиком — а вместе с ними пропускала бы и их картинки."""
    out = RAW / subject
    (out / "img").mkdir(parents=True, exist_ok=True)
    project = PROJECTS[subject]

    wanted: dict[str, str] = {}
    for page in sorted(out.glob("page_*.html")):
        for url in image_urls(page.read_text(encoding="utf-8"), project):
            wanted[url.rsplit("/", 1)[-1]] = url

    missing = {name: url for name, url in wanted.items() if not (out / "img" / name).exists()}
    print(f"картинок в условиях: {len(wanted)}, не хватает: {len(missing)}")

    for index, (name, url) in enumerate(sorted(missing.items()), 1):
        try:
            (out / "img" / name).write_bytes(_get(url))
        except Exception as error:
            print(f"  {name}: не далась ({type(error).__name__})")
        if index % 25 == 0:
            print(f"  скачано {index} из {len(missing)}")
        time.sleep(delay)

    print("картинки готовы")


def fetch(subject: str, pages: int, delay: float, start: int) -> None:
    project = PROJECTS.get(subject)
    if project is None:
        sys.exit(f"неизвестный предмет: {subject}. Есть: {', '.join(PROJECTS)}")

    out = RAW / subject
    (out / "img").mkdir(parents=True, exist_ok=True)

    seen_images: set[str] = set()
    for page in range(start, start + pages):
        target = out / f"page_{page:03d}.html"
        if target.exists() and target.stat().st_size > 1000:
            print(f"страница {page}: уже скачана, пропускаю")
            continue

        form = dict(BASE_FORM, proj=project, page=str(page))
        try:
            html = _post(QUESTIONS, form)
        except Exception as error:  # одна страница не должна ронять всю выгрузку
            print(f"страница {page}: не далась ({type(error).__name__}), иду дальше")
            continue

        blocks = html.count('class="qblock"')
        target.write_text(html, encoding="utf-8")

        if page == start:
            print(f"всего в банке по фильтру: {total_count(html)}")
        print(f"страница {page}: задач {blocks}, {len(html)} символов → {target.name}")

        if blocks == 0:
            print("пустая страница — дальше листать нечего")
            break

        for url in image_urls(html, project):
            if url in seen_images:
                continue
            seen_images.add(url)
            name = url.rsplit("/", 1)[-1]
            path = out / "img" / name
            if path.exists():
                continue
            try:
                path.write_bytes(_get(url))
            except Exception as error:  # картинка не должна ронять выгрузку
                print(f"  картинка не скачалась: {name} ({type(error).__name__})")
            time.sleep(delay / 2)

        time.sleep(delay)

    print(f"готово: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="math_prof", choices=sorted(PROJECTS))
    parser.add_argument("--pages", type=int, default=3, help="сколько страниц по 10 задач")
    parser.add_argument("--start", type=int, default=1, help="с какой страницы начать")
    parser.add_argument(
        "--delay", type=float, default=2.0, help="пауза между запросами, секунды"
    )
    parser.add_argument(
        "--images-only", action="store_true",
        help="не листать банк, только докачать картинки к сохранённым страницам",
    )
    args = parser.parse_args()

    if args.delay < 1:
        sys.exit("пауза меньше секунды — это уже долбёжка чужого сайта, так не делаем")

    if args.images_only:
        fetch_images(args.subject, args.delay)
    else:
        fetch(args.subject, args.pages, args.delay, args.start)


if __name__ == "__main__":
    main()
