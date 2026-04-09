.DEFAULT_GOAL := help
.PHONY: help init init-local data-dirs detect setup env \
        build-remote build-local \
        up down logs shell \
        phase1 phase2 phase3 run \
        phase1-local phase2-local phase3-local run-local down-local \
        sync \
        clean clean-data clean-all

# ── 設定 ────────────────────────────────────────────────
ENV_FILE   ?= .env
-include $(ENV_FILE)

CARLA_VERSION ?= 0.9.15
NUM_TRAIN     ?= 10000
NUM_TEST      ?= 2000
NUM_VERSIONS  ?= 10
CARLA_HOST    ?= localhost
CARLA_PORT    ?= 2000

COMPOSE_REMOTE = docker compose -f docker/compose.remote.yml --env-file $(ENV_FILE)
COMPOSE_LOCAL  = docker compose -f docker/compose.local.yml  --env-file $(ENV_FILE)

# リモートサーバー接続情報（.env または引数で上書き可）
REMOTE_USER ?= ubuntu
REMOTE_HOST ?=
REMOTE_DIR  ?= ~/Carla

# ── ヘルプ ───────────────────────────────────────────────
help:
	@echo ""
	@echo "  CARLA Counterfactual Dataset Framework"
	@echo ""
	@echo "  セットアップ（初回）"
	@echo "    make init            .env作成 + 接続情報自動検出 + data/作成 + Dockerビルド（リモートLinux用）"
	@echo "    make init-local      同上（ローカル開発用）"
	@echo "    make setup           .env を作成して依存ライブラリをインストール（pip）"
	@echo "    make env             .env.example → .env をコピー（既存は上書きしない）"
	@echo ""
	@echo "  リモートサーバーへの同期"
	@echo "    make sync REMOTE_HOST=192.168.1.100   ファイルをリモートに転送"
	@echo "    make sync REMOTE_HOST=x.x.x.x REMOTE_USER=ubuntu"
	@echo ""
	@echo "  ── リモート Linux サーバー ──"
	@echo "    make build-remote    Dockerイメージをビルド"
	@echo "    make up              CARLAサーバー + クライアントを起動"
	@echo "    make down            コンテナを停止・削除"
	@echo "    make logs            CARLAサーバーのログを表示"
	@echo "    make shell           クライアントコンテナにシェルで入る"
	@echo "    make phase1          Phase 1: 事実データ収集"
	@echo "    make phase2          Phase 2: 反実仮想生成"
	@echo "    make phase3          Phase 3: 選択的レンダリング"
	@echo "    make run             Phase all: 全フェーズ実行"
	@echo ""
	@echo "  ── ローカル（macOS / Linux、GPU不要） ──"
	@echo "    make build-local     Dockerイメージをビルド"
	@echo "    make phase1-local    CARLAサーバーを起動して Phase 1（小規模テスト: 100件）"
	@echo "    make phase2-local    Phase 2"
	@echo "    make phase3-local    Phase 3"
	@echo "    make run-local       Phase all"
	@echo "    make down-local      CARLAサーバーを停止"
	@echo ""
	@echo "  クリーンアップ"
	@echo "    make clean           Dockerイメージ・コンテナを削除"
	@echo "    make clean-data      data/ 以下を削除（要確認）"
	@echo "    make clean-all       上記すべて"
	@echo ""
	@echo "  設定例（.env またはコマンドライン引数で上書き可）:"
	@echo "    make phase1 NUM_TRAIN=500 NUM_TEST=100"
	@echo "    make run    CARLA_HOST=192.168.1.10"
	@echo ""

# ── 初回セットアップ ─────────────────────────────────────
init: env detect data-dirs build-remote
	@echo "✅ 初回セットアップ完了（リモートLinux用）"

detect:
	$(eval _USER := $(shell whoami))
	$(eval _HOST := $(shell hostname -I | awk '{print $$1}'))
	$(eval _DIR  := $(shell pwd))
	@sed -i.bak \
	    -e "s|^REMOTE_USER=.*|REMOTE_USER=$(_USER)|" \
	    -e "s|^REMOTE_HOST=.*|REMOTE_HOST=$(_HOST)|" \
	    -e "s|^REMOTE_DIR=.*|REMOTE_DIR=$(_DIR)|" \
	    $(ENV_FILE)
	@rm -f $(ENV_FILE).bak
	@echo "🔍 検出結果を .env に反映しました:"
	@echo "   REMOTE_USER=$(_USER)"
	@echo "   REMOTE_HOST=$(_HOST)"
	@echo "   REMOTE_DIR=$(_DIR)"

init-local: env data-dirs build-local
	@echo "✅ 初回セットアップ完了（ローカル開発用）"

data-dirs:
	mkdir -p data/factual data/counterfactual data/renders data/viz

# ── セットアップ ─────────────────────────────────────────
env:
	@if [ ! -f $(ENV_FILE) ]; then \
	    cp .env.example $(ENV_FILE); \
	    echo "✅ .env を作成しました。内容を確認・編集してください。"; \
	else \
	    echo "ℹ️  $(ENV_FILE) は既に存在します。"; \
	fi

setup: env
	pip install -r requirements.txt
	@echo "✅ セットアップ完了"

# ── リモートサーバー ─────────────────────────────────────
build-remote:
	$(COMPOSE_REMOTE) build

up:
	$(COMPOSE_REMOTE) up -d carla-server
	@echo "⏳ CARLAサーバーの起動を待機中..."
	$(COMPOSE_REMOTE) up --no-start client

down:
	$(COMPOSE_REMOTE) down

logs:
	$(COMPOSE_REMOTE) logs -f carla-server

shell:
	$(COMPOSE_REMOTE) run --rm client /bin/bash

phase1:
	$(COMPOSE_REMOTE) up -d carla-server
	$(COMPOSE_REMOTE) run --rm -e RUN_PHASE=1 \
	    -e NUM_TRAIN=$(NUM_TRAIN) -e NUM_TEST=$(NUM_TEST) client

phase2:
	$(COMPOSE_REMOTE) up -d carla-server
	$(COMPOSE_REMOTE) run --rm -e RUN_PHASE=2 \
	    -e NUM_VERSIONS=$(NUM_VERSIONS) client

phase3:
	$(COMPOSE_REMOTE) up -d carla-server
	$(COMPOSE_REMOTE) run --rm -e RUN_PHASE=3 \
	    -e NUM_VERSIONS=$(NUM_VERSIONS) client

run:
	$(COMPOSE_REMOTE) up -d carla-server
	$(COMPOSE_REMOTE) run --rm \
	    -e RUN_PHASE=all \
	    -e NUM_TRAIN=$(NUM_TRAIN) \
	    -e NUM_TEST=$(NUM_TEST) \
	    -e NUM_VERSIONS=$(NUM_VERSIONS) \
	    client

# ── ローカル macOS ───────────────────────────────────────
build-local:
	$(COMPOSE_LOCAL) build

phase1-local:
	$(COMPOSE_LOCAL) up -d carla-server
	$(COMPOSE_LOCAL) run --rm \
	    -e NUM_TRAIN=100 -e NUM_TEST=20 -e RUN_PHASE=1 client

phase2-local:
	$(COMPOSE_LOCAL) up -d carla-server
	$(COMPOSE_LOCAL) run --rm \
	    -e NUM_VERSIONS=3 -e RUN_PHASE=2 client

phase3-local:
	$(COMPOSE_LOCAL) up -d carla-server
	$(COMPOSE_LOCAL) run --rm \
	    -e NUM_VERSIONS=3 -e RUN_PHASE=3 client

run-local:
	$(COMPOSE_LOCAL) up -d carla-server
	$(COMPOSE_LOCAL) run --rm \
	    -e RUN_PHASE=all \
	    -e NUM_TRAIN=$(NUM_TRAIN) \
	    -e NUM_TEST=$(NUM_TEST) \
	    -e NUM_VERSIONS=$(NUM_VERSIONS) \
	    client

down-local:
	$(COMPOSE_LOCAL) down

# ── リモート同期 ─────────────────────────────────────────
sync:
	@if [ -z "$(REMOTE_HOST)" ]; then \
	    echo "❌ REMOTE_HOST が未設定です。例: make sync REMOTE_HOST=192.168.1.100"; \
	    exit 1; \
	fi
	rsync -av --exclude=data/ --exclude=__pycache__ --exclude=.git \
	    ./ $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)/
	@echo "✅ 同期完了: $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)"

# ── クリーンアップ ───────────────────────────────────────
clean:
	$(COMPOSE_REMOTE) down --rmi local --volumes --remove-orphans 2>/dev/null || true
	$(COMPOSE_LOCAL)  down --rmi local --volumes --remove-orphans 2>/dev/null || true

clean-data:
	@echo "⚠️  data/ 以下のデータをすべて削除します。よろしいですか？ [y/N]"; \
	read ans; \
	if [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]; then \
	    rm -rf data/factual/* data/counterfactual* data/renders data/viz; \
	    echo "✅ データを削除しました。"; \
	else \
	    echo "キャンセルしました。"; \
	fi

clean-all: clean clean-data
