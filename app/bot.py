from __future__ import annotations

from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from app.config import Settings
from app.search import find_imo


def _format_results(imo: str, results_count: int, rendered_hits: list[str]) -> str:
    header = f"IMO `{imo}` найден. Совпадений: {results_count}\n"
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
        await message.answer("Совпадения не найдены.")
        return

    imo = results[0].imo
    max_items = 10
    rendered = []
    for row in results[:max_items]:
        file_name = Path(row.document_path).name
        rendered.append(
            f"- `{file_name}`\n"
            f"  location: {row.location}\n"
            f"  context: {row.snippet}"
        )
    if len(results) > max_items:
        rendered.append(f"... и еще {len(results) - max_items} совпадений")

    await message.answer(
        _format_results(imo, len(results), rendered),
        parse_mode="Markdown",
    )


async def run_bot(settings: Settings, *, drop_pending_updates: bool = False) -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Add it to .env")

    bot = Bot(token=settings.bot_token)
    dp = _make_dispatcher(settings)
    await dp.start_polling(bot, drop_pending_updates=drop_pending_updates)
