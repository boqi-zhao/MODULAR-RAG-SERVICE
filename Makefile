# 常用开发命令；与 README 的启动说明保持一致，配方行必须使用 Tab 缩进。
UV := uv
PORT ?= 8080

.PHONY: api db migrate test lint

# 启动服务；先确保 PostgreSQL 在运行且结构已升级，再启动 Uvicorn。
# 换端口：make api PORT=8000
api: db
	$(UV) run --env-file .env uvicorn api.main:app --app-dir src --host 127.0.0.1 --port $(PORT)

# 启动本地 PostgreSQL 并升级到最新迁移；重复执行安全。
db:
	docker compose up -d --wait postgres
	$(UV) run --env-file .env alembic upgrade head

# 只执行迁移；用于手动检查数据库结构。
migrate:
	$(UV) run --env-file .env alembic upgrade head

# 运行真实 PG 测试；未加载数据库配置时测试会跳过，跳过不算验证通过。
test:
	$(UV) run --env-file .env pytest -q

# 静态检查与格式检查，不修改文件。
lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .
