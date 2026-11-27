# Запуск бота через Docker Compose и Tuna

Команды выполняются в PowerShell из папки `D:\Work\wishlist_bot`.
Нужен запущенный Docker Desktop с Linux-контейнерами.

## Первый запуск

1. Установите Tuna и войдите в аккаунт (после установки при необходимости откройте новый PowerShell):

   ```powershell
   winget install --id yuccastream.tuna
   tuna login --web
   ```

2. Если `.env` ещё нет, скопируйте шаблон:

   ```powershell
   Copy-Item .env.example .env
   ```

   В `.env` задайте параметры ниже. Существующий файл и секреты сохраняйте.
   Домен возьмите из кабинета Tuna; здесь указан домен из документации проекта.

   ```dotenv
   APP_ENV=production
   PUBLIC_BASE_URL=https://fast-tundra-1847.a.tuna.free
   DEV_LOGIN_ENABLED=false
   SESSION_SECRET=<случайная строка длиной не менее 32 символов>
   TELEGRAM_MODE=polling
   TELEGRAM_ALLOW_PRIVATE_LOGIN=true
   TELEGRAM_BOT_TOKEN=<токен от BotFather>
   TELEGRAM_BOT_USERNAME=<имя бота без @>
   TELEGRAM_APP_NAME=<short name Mini App из BotFather>
   TELEGRAM_CHAT_ID=
   ```

   Для личного использования `TELEGRAM_CHAT_ID` оставьте пустым. Для общего
   пространства укажите ID группы и назначьте бота её администратором.
   Новый `SESSION_SECRET` можно получить командой, если установлен Python:
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

3. Запустите приложение, примените настройку Telegram и запустите бота:

   ```powershell
   docker compose up -d --build --wait
   docker compose exec api python -m src.cli configure-telegram
   docker compose --profile telegram up -d bot
   ```

4. В отдельном окне PowerShell запустите туннель и оставьте окно открытым:

   ```powershell
   tuna http 127.0.0.1:3000 --domain=fast-tundra-1847.a.tuna.free --inspect=false --https-redirect
   ```

   Домен в команде должен совпадать с `PUBLIC_BASE_URL`. Дождитесь `Forwarding https://...`.

5. В BotFather настройте Mini App: URL — значение `PUBLIC_BASE_URL`,
   short name — значение `TELEGRAM_APP_NAME`. Откройте личный чат с ботом,
   отправьте `/start` и нажмите «Мой вишлист».

## Повторный запуск

Если `.env` и Mini App уже настроены:

```powershell
docker compose --profile telegram up -d --build --wait
```

Затем в отдельном окне запустите Tuna командой из шага 4.
Compose сам туннель не запускает.

## Проверка и остановка

```powershell
docker compose --profile telegram ps
docker compose logs --tail=50 api bot
curl.exe -i -H "tuna-skip-browser-warning: 1" https://fast-tundra-1847.a.tuna.free/api/v1/health
```

Ожидаемый ответ проверки — HTTP 200 и `{"status":"ok"}`. Если используется
другой домен, замените его и в команде проверки. При 404 проверьте, что Tuna
работает и домен совпадает с `.env`. Бесплатный Tuna может показать предупреждение
при первом открытии: проверьте переход в приложение из Telegram.

Остановка: `Ctrl+C` в окне Tuna, затем:

```powershell
docker compose --profile telegram stop
```

Данные сохраняются. Не используйте `docker compose down -v`, если они нужны.
При смене домена обновите `.env` и URL в BotFather, повторите команду запуска
Compose и отправьте боту новый `/start`.

## Общий чат

Просто добавить бота в группу недостаточно — `/app` отвечает только настроенному чату.

1. Добавьте бота в группу и сделайте **администратором** (нужно для проверки участников).
2. Узнайте ID группы и пропишите его в `.env` как `TELEGRAM_CHAT_ID`.
3. Перезапустите стек и выполните:

   ```powershell
   docker compose exec api python -m src.cli configure-telegram
   docker compose --profile telegram up -d bot
   ```

4. В группе команда `/app` даст кнопку «Открыть вишлисты». Участники при входе
   попадают в общее сообщество.

Без `TELEGRAM_CHAT_ID` остаётся личный режим: у каждого свой вишлист, друзья —
только по приглашениям. Групповые списки и дружба по ссылкам — разные механизмы.

Подробности: [README.md](README.md).
