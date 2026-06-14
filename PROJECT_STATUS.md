# Jarvis Auto Bot — статус проекта (на 2026-06-14)

Telegram-бот автодиагностики. Пользователь Alex — нетехнический, генератор идей.
Все правки делает Claude. Репозиторий: sushentsov12-afk/jarvis-auto.bot
Хостинг: Railway (worker), Procfile: `worker: python jarvis_bot/bot.py`

## Архитектура
jarvis_bot/
  bot.py            — главный файл, все хендлеры
  config.py         — ADMIN_ID, GIGACHAT_CREDENTIALS, токены из env
  keyboards.py      — все клавиатуры (reply + inline)
  formatters.py     — форматирование текстов, format_diagnostic_for_level()
  diagnostic.py     — smart_search() / search_by_phrase() по diagnostic_base.json
  dialog_engine.py  — 11 диалоговых деревьев с уточняющими вопросами
  dialog_state.py   — простое in-memory хранилище состояний (без зависимостей)
  clarify.py        — fallback: уточняющие вопросы + сохранение unknown_queries в SQLite
  mechanic.py       — вопросы механику/экспертам (SQLite mechanic_questions)
  user_profile.py   — уровни пользователей (5 шт), рейтинги экспертов
  user_vehicle.py / user_history.py — SQLite (data/jarvis.db)
  photo_diagnosis.py — анализ фото через GigaChat-Pro Vision
  faq.py            — 8 готовых FAQ-ответов для новичков
  ai_assistant.py   — GigaChat: ask() + analyze_and_save()
  catalog.py, sponsors.py, sos_geo.py, broadcaster.py, vehicle_db.py, network.py

data/
  diagnostic_base.json — 212 записей, 1370 поисковых фраз
  vehicles.json (21 авто, вкл. Ford Fusion), vehicle_issues.json, parts.json, services.json

## Уровни пользователей (user_profile.py LEVELS)
novice🔰 / driver🚗 / garage🔧 / mechanic⚙️ / expert🏆
- Выбор уровня при первом /start (онбординг)
- /profile, /setlevel — просмотр/смена
- mechanic/expert получают вопросы от пользователей (notify_experts),
  кнопки ✅Ответить/➡️Пропустить, рейтинг через 👍/🤔/👎

## Поток диагностики (process_diagnostic_input в bot.py)
1. find_tree(text, threshold=55) — диалоговое дерево (11 шт, ~190 триггеров)
2. smart_search(text) — diagnostic_base.json (212/1370), порог 42%
   → format_diagnostic_for_level(result, level) — адаптация под уровень
3. find_best_match — каталог запчастей
4. Fallback: save_unknown_query() + 3 уточняющих вопроса (clarify.py)
   → после ответов повторный search_by_phrase(threshold=35)
   → если GigaChat включён — analyze_and_save() пробует пополнить базу

## Главное меню (main_reply_keyboard)
🔍 ДИАГНОСТИКА, 🚗 Моё авто, 📋 История, 🏪 Сервисы, 🆘 SOS,
ℹ️ Справка, 💬 Обратная связь, 🔧 Спросить механика, 📚 FAQ — частые вопросы
Админ (ADMIN_ID) видит admin_keyboard() с доп. кнопкой 🛠 Админ панель.

## Админ-панель (admin_panel_keyboard, callback "admin_*")
👥 Пользователи | ❓ Нераспознанные | 📢 Рассылка | 🗄 База диагностики |
🔧 Вопросы механику | 🏆 Эксперты
Команды механика: /answer_ID [текст], /add_ID (структурирует в базу через GigaChat)
Прочие команды: /start /profile /setlevel /admin /broadcast /stats /unknown

## Важные технические заметки
- ВСЕГДА проверять синтаксис после правок bot.py:
  `python3 -c "import ast; ast.parse(open('jarvis_bot/bot.py').read())"`
  Частая ошибка — литеральные \n в f-strings внутри bash heredoc.
  Решение: использовать \\n или собирать строку через переменные.
- Procfile/импорты: Railway запускает `python jarvis_bot/bot.py` из КОРНЯ репо,
  поэтому импорты внутри пакета — абсолютные (`from config import X`).
- Git push: `git remote set-url origin https://<PAT>@github.com/sushentsov12-afk/jarvis-auto.bot.git`
- requirements.txt: gigachat>=0.2.1 (обязательно, старая 0.1.33 не поддерживает Image/Vision)

## На горизонте / идеи (не реализовано)
- Режим "Объясни ещё проще" — кнопка под любым ответом
- Иллюстрации/схемы мест на авто (ограничения Telegram)
- Монетизация экспертов при рейтинге 4+ и 10+ ответов
- Дальнейшее пополнение diagnostic_base.json по логам /unknown
