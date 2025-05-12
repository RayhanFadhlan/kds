.PHONY: up up-d down build rebuild logs ps init-db scrape clean db-shell db-query db-dump db-restore up-no-db scrape-run up-backend up-scraper

# Extract database URL properly with SSL parameters intact
DB_URL ?= $(shell grep DATABASE_URL .env 2>/dev/null | cut -d '=' -f2)

up-backend:
	docker-compose --env-file .env --profile backend-only up -d

up-scraper:
	docker-compose --env-file .env --profile scraper-only up -d
a
up:
	docker-compose --env-file .env up

up-d:
	docker-compose --env-file .env up -d

up-no-db:
	docker-compose --env-file .env --profile external-db up -d

down:
	docker-compose --env-file .env down

build:
	docker-compose --env-file .env build

rebuild:
	docker-compose --env-file .env build --no-cache

logs:
	docker-compose --env-file .env logs -f

ps:
	docker-compose --env-file .env ps

init-db:
	docker-compose --env-file .env exec scraper python -m src.init_db

init-db-external:
	docker-compose --env-file .env exec -e "DATABASE_URL=$(DB_URL)" scraper python -m src.init_db

scrape:
	docker-compose --env-file .env exec scraper python -m src.main

scrape-with-options:
	docker-compose --env-file .env exec scraper python -m src.main $(SCRAPER_OPTS)

db-shell:
	@if [[ "$(DB_URL)" == *"neon.tech"* ]]; then \
		echo "Connecting to Neon database..."; \
		docker-compose --env-file .env exec scraper apt-get update && apt-get install -y postgresql-client && \
		docker-compose --env-file .env exec scraper psql "$(DB_URL)"; \
	else \
		docker-compose --env-file .env exec postgres psql -U $${POSTGRES_USER:-bacterial_user} -d $${POSTGRES_DB:-bacterial_classification}; \
	fi

db-shell-external:
	@echo "Connecting to external database: $(DB_URL)"
	docker-compose --env-file .env exec scraper apt-get update && apt-get install -y postgresql-client && \
	docker-compose --env-file .env exec scraper psql "$(DB_URL)"

db-query:
	@if [ -z "$(QUERY)" ]; then \
		echo "Usage: make db-query QUERY='SELECT * FROM bacteria LIMIT 10;'"; \
	elif [[ "$(DB_URL)" == *"neon.tech"* ]]; then \
		echo "Running query on Neon database..."; \
		docker-compose --env-file .env exec scraper apt-get update && apt-get install -y postgresql-client && \
		docker-compose --env-file .env exec scraper psql "$(DB_URL)" -c "$(QUERY)"; \
	else \
		docker-compose --env-file .env exec postgres psql -U $${POSTGRES_USER:-bacterial_user} -d $${POSTGRES_DB:-bacterial_classification} -c "$(QUERY)"; \
	fi

db-query-external:
	@if [ -z "$(QUERY)" ]; then \
		echo "Usage: make db-query-external QUERY='SELECT * FROM bacteria LIMIT 10;'"; \
	else \
		docker-compose --env-file .env exec scraper apt-get update && apt-get install -y postgresql-client && \
		docker-compose --env-file .env exec scraper psql "$(DB_URL)" -c "$(QUERY)"; \
	fi

db-dump:
	@if [ -z "$(FILE)" ]; then \
		FILE="backup-$$(date +%Y%m%d-%H%M%S).sql"; \
		echo "Dumping to $$FILE"; \
		if [[ "$(DB_URL)" == *"neon.tech"* ]]; then \
			docker-compose --env-file .env exec scraper apt-get update && apt-get install -y postgresql-client && \
			docker-compose --env-file .env exec scraper pg_dump "$(DB_URL)" > $$FILE; \
		else \
			docker-compose --env-file .env exec -T postgres pg_dump -U $${POSTGRES_USER:-bacterial_user} -d $${POSTGRES_DB:-bacterial_classification} > $$FILE; \
		fi \
	else \
		if [[ "$(DB_URL)" == *"neon.tech"* ]]; then \
			docker-compose --env-file .env exec scraper apt-get update && apt-get install -y postgresql-client && \
			docker-compose --env-file .env exec scraper pg_dump "$(DB_URL)" > $(FILE); \
		else \
			docker-compose --env-file .env exec -T postgres pg_dump -U $${POSTGRES_USER:-bacterial_user} -d $${POSTGRES_DB:-bacterial_classification} > $(FILE); \
		fi \
	fi

db-dump-external:
	@if [ -z "$(FILE)" ]; then \
		FILE="backup-$$(date +%Y%m%d-%H%M%S).sql"; \
		echo "Dumping to $$FILE"; \
		docker-compose --env-file .env exec scraper apt-get update && apt-get install -y postgresql-client && \
		docker-compose --env-file .env exec scraper pg_dump "$(DB_URL)" > $$FILE; \
	else \
		docker-compose --env-file .env exec scraper apt-get update && apt-get install -y postgresql-client && \
		docker-compose --env-file .env exec scraper pg_dump "$(DB_URL)" > $(FILE); \
	fi

db-restore:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make db-restore FILE=backup.sql"; \
	elif [[ "$(DB_URL)" == *"neon.tech"* ]]; then \
		echo "Restoring to Neon database..."; \
		docker-compose --env-file .env exec scraper apt-get update && apt-get install -y postgresql-client && \
		docker-compose --env-file .env exec -T scraper psql "$(DB_URL)" < $(FILE); \
	else \
		docker-compose --env-file .env exec -T postgres psql -U $${POSTGRES_USER:-bacterial_user} -d $${POSTGRES_DB:-bacterial_classification} < $(FILE); \
	fi

db-restore-external:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make db-restore-external FILE=backup.sql"; \
	else \
		docker-compose --env-file .env exec scraper apt-get update && apt-get install -y postgresql-client && \
		docker-compose --env-file .env exec -T scraper psql "$(DB_URL)" < $(FILE); \
	fi

shell-backend:
	docker-compose --env-file .env exec backend bash

shell-scraper:
	docker-compose --env-file .env exec scraper bash

shell-db:
	docker-compose --env-file .env exec postgres bash

clean:
	docker-compose --env-file .env down -v
	docker-compose --env-file .env rm -f

batch-scrape:
	docker-compose --env-file .env exec scraper python -m src.batch_scraper $(BATCH_OPTS)

batch-scrape-external:
	docker-compose --env-file .env exec -e "DATABASE_URL=$(DB_URL)" scraper python -m src.batch_scraper $(BATCH_OPTS)

db-stats:
	docker-compose --env-file .env exec scraper python -m src.batch_scraper --stats-only

db-stats-external:
	docker-compose --env-file .env exec -e "DATABASE_URL=$(DB_URL)" scraper python -m src.batch_scraper --stats-only

resume-scrape:
	docker-compose --env-file .env exec scraper python -m src.batch_scraper $(BATCH_OPTS)

resume-scrape-external:
	docker-compose --env-file .env exec -e "DATABASE_URL=$(DB_URL)" scraper python -m src.batch_scraper $(BATCH_OPTS)

reset-scrape:
	docker-compose --env-file .env exec scraper python -m src.batch_scraper --reset-progress $(BATCH_OPTS)

reset-scrape-external:
	docker-compose --env-file .env exec -e "DATABASE_URL=$(DB_URL)" scraper python -m src.batch_scraper --reset-progress $(BATCH_OPTS)
