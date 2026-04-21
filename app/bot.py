from __future__ import annotations

from pathlib import Path
import re

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from app.config import Settings
from app.search import find_imo

TELEGRAM_TEXT_LIMIT = 4096
SAFE_MESSAGE_LIMIT = 3600


def _sanitize_text(text: str, *, max_len: int = 220) -> str:
    # Remove typical PDF glyph-noise sequences while keeping isolated tokens
    # that might be meaningful in source descriptions.
    no_glyph_tokens = re.sub(r"(?:/g\d+[A-Za-z]*){2,}", " ", text)
    no_glyph_tokens = re.sub(r"(?:\s+/g\d+[A-Za-z]*){3,}", " ", no_glyph_tokens)
    compact = re.sub(r"\s+", " ", no_glyph_tokens).strip()
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3].rstrip() + "..."


def _split_for_telegram(text: str, *, limit: int = SAFE_MESSAGE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    for block in text.split("\n\n"):
        candidate = block if not current else f"{current}\n\n{block}"
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(block) <= limit:
            current = block
            continue
        for i in range(0, len(block), limit):
            chunks.append(block[i : i + limit])
    if current:
        chunks.append(current)
    return chunks


def _format_results(imo: str, results_count: int, rendered_hits: list[str]) -> str:
    header = f"IMO {imo} найден. Совпадений: {results_count}\n"
    return header + "\n\n".join(rendered_hits)


def _make_dispatcher(settings: Settings) -> Dispatcher:
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def start_handler(message: Message) -> None:
        await message.answer(
            "Привет. Сейчас бот умеет только проверку по IMO номеру судна.\n"
            "Отправь IMO (7 цифр) или используй команду /check <imo>.",
            parse_mode="Markdown",
        )

    @dp.message(Command("help"))
    async def help_handler(message: Message) -> None:
        await message.answer(
            "Доступно:\n"
            "/check <imo> - поиск IMO в локальном индексе\n"
            "Также можно отправить IMO номер обычным сообщением."
        )

    @dp.message(Command("check"))
    async def check_handler(message: Message) -> None:
        if not message.text:
            await message.answer("Пустое сообщение.")
            return

        parts = message.text.split(maxsplit=1)
        if len(parts) != 2:
            await message.answer("Использование: /check <imo>")
            return

        await _handle_imo_query(message, settings, parts[1])

    @dp.message(F.text)
    async def text_handler(message: Message) -> None:
        await _handle_imo_query(message, settings, message.text or "")

    return dp


async def _handle_imo_query(message: Message, settings: Settings, raw_imo: str) -> None:
    try:
        results = find_imo(settings, raw_imo)
    except ValueError as exc:
        await message.answer(f"Невалидный IMO: {exc}")
        return

    if not results:
        await message.answer(
            "Совпадения не найдены.\n"
            "Рекомендуем дополнительно проверить IMO в исходных документах."
        )
        return

    imo = results[0].imo
    max_items = 10
    rendered = []
    for row in results[:max_items]:
        file_name = Path(row.document_path).name
        rendered.append(
            f"- {file_name}\n"
            f"  location: {row.location}\n"
            f"  context: {_sanitize_text(row.snippet)}"
        )
    if len(results) > max_items:
        rendered.append(f"... и еще {len(results) - max_items} совпадений")

    response_text = _format_results(imo, len(results), rendered)
    chunks = _split_for_telegram(response_text, limit=SAFE_MESSAGE_LIMIT)
    if len(chunks) > 1:
        chunks[0] = f"{chunks[0]}\n\n(1/{len(chunks)})"
        for idx in range(1, len(chunks)):
            chunks[idx] = f"{chunks[idx]}\n\n({idx + 1}/{len(chunks)})"

    for chunk in chunks:
        if len(chunk) > TELEGRAM_TEXT_LIMIT:
            chunk = chunk[: TELEGRAM_TEXT_LIMIT - 3] + "..."
        await message.answer(chunk)


async def run_bot(settings: Settings, *, drop_pending_updates: bool = False) -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Add it to .env")

    bot = Bot(token=settings.bot_token)
    dp = _make_dispatcher(settings)
    await dp.start_polling(bot, drop_pending_updates=drop_pending_updates)
