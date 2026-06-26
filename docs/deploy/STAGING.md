# Staging-стенд Biblio (безопасный не-прод)

Узкое место, которое снимает staging: **нет места безопасно вывести и проверить
изменения до прода** — особенно staff-АРМы (их записи в ИРБИС/RDR жёстко гейтятся),
а также ops (индексатор, `.env`, деплой). Вывод из памяти проекта: «нужен STAGING +
CI/CD; работать через PR/стенд, а не ad-hoc prod-ssh». CI/CD есть (PR #260) — это
вторая половина.

## Топология
Staging — ОТДЕЛЬНЫЙ compose-проект `biblio-staging` на ТОМ ЖЕ хосте (pve / LXC 100),
рядом с продом (`deploy-*`):

| | Прод | Staging |
|---|---|---|
| compose-проект | `deploy` | `biblio-staging` |
| контейнеры | `deploy-*` | `biblio-staging-*` |
| тома | `deploy_*` | `biblio-staging_*` |
| порты хоста | 80/443 | **8080/8443** |
| ИРБИС | живой (192.168.1.55) | **отключён** (own-store only) |
| данные | боевые | копия EK-индекса + свои сторы |

**Безопасность:** overlay ставит `IRBIS_HOST=""` → боевой ИРБИС/RDR физически
недостижимы со стенда. Каталог/поиск — из own-store (`OWN_SEARCH_DBS=EK`), стенд
сидируется КОПИЕЙ боевого `catalog.db`. Все правки staff-АРМов (каталогизация/
книговыдача/комплектование/КО) пишутся в СОБСТВЕННЫЕ sqlite-сторы стенда (свои тома)
→ нулевой риск для прода.

## Первичный провижн (на pve, в LXC 100)
```bash
cd /opt/biblio/deploy
cp .env.staging.example .env.staging         # заполнить СМЕНИТЬ_* (свои секреты!)
docker compose -p biblio-staging --env-file .env.staging \
  -f docker-compose.yml -f docker-compose.staging.yml up -d --build
```
Проверка: `docker compose -p biblio-staging ps` → db/backend/proxy healthy;
`curl -fsk https://localhost:8443/api/health`.

## Сид реальным EK-индексом (реалистичные данные)
Скопировать боевой `catalog.db` (245k EK, см. #262) в том стенда — один раз и при
необходимости освежить:
```bash
docker run --rm \
  -v deploy_backend-data:/src:ro \
  -v biblio-staging_backend-data:/dst \
  alpine sh -c "cp /src/catalog.db /dst/catalog.db"
docker compose -p biblio-staging restart backend
```
(Прод-`catalog.db` — это own-индекс, БЕЗ ПДн читателей; копировать безопасно.)

## Доступ
- Портал: `https://<host>:8443/` (dev-сертификат — самоподписанный).
- Вход читателя: демо-билет `TEST_READER_TICKET` из `.env.staging` (стенд не ходит
  в боевой RDR).
- Staff-АРМы: вход сотрудника с тестовыми грантами (см. модуль доступа); правки
  каталога/выдачи остаются в томах стенда.

## Рабочий цикл (PR → staging → прод)
1. Изменение → ветка → PR → CI зелёный (44-тестовый гейт).
2. Выкатить на **staging** и проверить (особенно staff-АРМы и ops):
   ```bash
   docker compose -p biblio-staging --env-file .env.staging \
     -f docker-compose.yml -f docker-compose.staging.yml up -d --build
   ```
3. Убедившись на стенде — мерж в main → выкат на **прод** (`deploy/deploy.sh`).

## Остановка / сброс
```bash
docker compose -p biblio-staging --env-file .env.staging \
  -f docker-compose.yml -f docker-compose.staging.yml down          # стоп (тома живут)
# ...add -v чтобы снести и тома (полный сброс стенда)
```

## Открытые вопросы / следующие шаги
- Тестовые staff-гранты для стенда (сейчас вход сотрудника — через модуль доступа;
  завести seed тестовых учёток на стенде).
- Когда появится auth/режимы (следующий узел) — на стенде включить `режим=полная`
  для проверки staff-контура целиком.
- Опц.: nightly-сброс стенда к снимку (как у demo: `deploy/demo/reset_demo.sh`).
