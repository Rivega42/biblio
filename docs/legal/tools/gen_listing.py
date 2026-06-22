#!/usr/bin/env python3
"""Генератор листинга исходного кода Biblio для депонирования и госрегистрации ПрЭВМ.

Собирает значимые исходные файлы (бэкенд Python + фронтенд React) в единый
постранично размеченный листинг с нумерацией строк и считает контрольные суммы
(SHA-256) каждого файла и всего листинга. Запускается повторно — листинг
обновляется вслед за изменениями кода (см. .github/workflows/legal-listing.yml).

Запуск из корня репозитория:
    python docs/legal/tools/gen_listing.py

Результат:
    docs/legal/listings/SOURCE_LISTING.md      — постраничный листинг
    docs/legal/listings/MANIFEST.sha256.md     — манифест с хэшами

Для Роспатента (ст. 1262): из полного листинга берут значимые фрагменты в
рекомендованном объёме (ориентировочно первые ~50–70 «страниц» — уточнить по
приказу № 211). Файлы упорядочены так, что ядро системы идёт первым.
"""
from __future__ import annotations

import hashlib
import subprocess
from datetime import date
from pathlib import Path

# Корень репозитория = на два уровня выше docs/legal/tools/.
REPO = Path(__file__).resolve().parents[3]

# Каталоги с исходным кодом (относительно корня репозитория).
INCLUDE_ROOTS = [
    "irbis-web/backend",
    "irbis-web/frontend/app",
    "irbis-web/frontend/components",
    "irbis-web/frontend/src",
]
INCLUDE_EXT = {".py", ".jsx", ".tsx", ".ts", ".css"}
EXCLUDE_DIRS = {"node_modules", "dist", "__pycache__", ".git", "build", ".venv"}
# Сгенерированные декларации типов и карты — шум для листинга.
EXCLUDE_SUFFIX = {".d.ts"}

# Порядок: ядро системы первым (значимые фрагменты — в начале листинга).
PRIORITY = [
    "irbis-web/backend/server.py",
    "irbis-web/backend/core.py",
    "irbis-web/backend/config.py",
    "irbis-web/backend/access/catalog.py",
    "irbis-web/backend/access/circulation.py",
    "irbis-web/backend/access/acquisition.py",
    "irbis-web/backend/access/bookprovision.py",
    "irbis-web/backend/access/flk.py",
    "irbis-web/backend/access/authority.py",
    "irbis-web/backend/access/pft.py",
    "irbis-web/backend/access/gbl.py",
    "irbis-web/backend/access/holds.py",
    "irbis-web/backend/access/notifications.py",
    "irbis-web/backend/access/entitlements.py",
    "irbis-web/backend/access/billing.py",
    "irbis-web/backend/access/provision.py",
    "irbis-web/backend/access/store.py",
    "irbis-web/backend/access/pgstore.py",
    "irbis-web/backend/access/jwt.py",
    "irbis-web/backend/access/crypto.py",
    "irbis-web/frontend/app/live.jsx",
]

LINES_PER_PAGE = 55


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO, capture_output=True, text=True, check=True,
        )
        return out.stdout.strip() or "uncommitted"
    except Exception:
        return "uncommitted"


def collect_files() -> list[Path]:
    found: set[Path] = set()
    for root in INCLUDE_ROOTS:
        base = REPO / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if any(part in EXCLUDE_DIRS for part in p.parts):
                continue
            if any(p.name.endswith(suf) for suf in EXCLUDE_SUFFIX):
                continue
            if p.suffix in INCLUDE_EXT:
                found.add(p)
    rel = sorted(str(p.relative_to(REPO)).replace("\\", "/") for p in found)
    # Приоритетные файлы — вперёд, сохраняя их порядок; остальные — по алфавиту.
    pset = [r for r in PRIORITY if r in rel]
    rest = [r for r in rel if r not in set(PRIORITY)]
    ordered = pset + rest
    return [REPO / r for r in ordered]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    out_dir = REPO / "docs/legal/listings"
    out_dir.mkdir(parents=True, exist_ok=True)
    files = collect_files()
    sha = git_sha()
    today = date.today().isoformat()

    body_lines: list[str] = []
    manifest_rows: list[str] = []
    page = 1
    line_on_page = 0
    total_src_lines = 0
    concat = hashlib.sha256()

    def page_break() -> None:
        nonlocal page, line_on_page
        page += 1
        line_on_page = 0
        body_lines.append("")
        body_lines.append(f"<!-- ─── страница {page} ─── -->")
        body_lines.append("")

    for rel_path in files:
        rel = str(rel_path.relative_to(REPO)).replace("\\", "/")
        raw = rel_path.read_bytes()
        concat.update(rel.encode("utf-8") + b"\0" + raw)
        text = raw.decode("utf-8", errors="replace")
        src_lines = text.splitlines()
        total_src_lines += len(src_lines)
        manifest_rows.append(
            f"| `{rel}` | {len(src_lines)} | `{sha256_bytes(raw)}` |"
        )

        # Заголовок файла (всегда с начала новой логической группы).
        body_lines.append("")
        body_lines.append(f"### Файл: `{rel}`  · строк: {len(src_lines)}")
        body_lines.append("")
        body_lines.append("```" + (rel_path.suffix.lstrip(".") or "text"))
        for i, ln in enumerate(src_lines, start=1):
            body_lines.append(f"{i:>5} | {ln}")
            line_on_page += 1
            if line_on_page >= LINES_PER_PAGE:
                body_lines.append("```")
                page_break()
                body_lines.append("```" + (rel_path.suffix.lstrip(".") or "text"))
        body_lines.append("```")

    overall = concat.hexdigest()
    est_pages = page

    header = [
        "# Biblio — листинг исходного кода (депонируемые материалы)",
        "",
        "> Автогенерируемый документ. **Не редактировать вручную** — пересобирается",
        "> скриптом `docs/legal/tools/gen_listing.py` (и workflow `legal-listing.yml`).",
        "> Для Роспатента (ст. 1262) берут значимые фрагменты в рекомендованном объёме",
        "> (ориентировочно первые ~50–70 страниц — уточнить по приказу № 211); ядро",
        "> системы размещено первым.",
        "",
        "| Параметр | Значение |",
        "|---|---|",
        f"| Продукт | Biblio — система автоматизации библиотек (АБИС) |",
        f"| Дата сборки листинга | {today} |",
        f"| Версия кода (git) | `{sha}` |",
        f"| Файлов в листинге | {len(files)} |",
        f"| Всего строк исходного кода | {total_src_lines} |",
        f"| Условных страниц (~{LINES_PER_PAGE} строк) | {est_pages} |",
        f"| **SHA-256 всего листинга** | `{overall}` |",
        "",
        "Перечень файлов и их контрольные суммы — в `MANIFEST.sha256.md`.",
        "",
        "---",
        "",
        "<!-- ─── страница 1 ─── -->",
    ]

    (out_dir / "SOURCE_LISTING.md").write_text(
        "\n".join(header + body_lines) + "\n", encoding="utf-8"
    )

    manifest = [
        "# Манифест депонируемых материалов Biblio (SHA-256)",
        "",
        f"- Дата сборки: **{today}**",
        f"- Версия кода (git): **`{sha}`**",
        f"- Файлов: **{len(files)}** · строк: **{total_src_lines}** · условных страниц: **{est_pages}**",
        f"- **SHA-256 всего листинга:** `{overall}`",
        "",
        "Контрольная сумма всего листинга фиксирует неизменность кода на дату сборки —",
        "её удобно указывать в описи на депонирование (`templates/10_zayavka_deponirovanie.md`).",
        "",
        "| Файл | Строк | SHA-256 |",
        "|---|---:|---|",
        *manifest_rows,
    ]
    (out_dir / "MANIFEST.sha256.md").write_text(
        "\n".join(manifest) + "\n", encoding="utf-8"
    )

    print(f"OK: {len(files)} файлов, {total_src_lines} строк, ~{est_pages} страниц")
    print(f"SHA-256 листинга: {overall}")
    print(f"git: {sha}  дата: {today}")


if __name__ == "__main__":
    main()
