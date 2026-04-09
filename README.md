# Counterfactual Data Generation Framework for CARLA

CARLA Simulator を用いて「事実 vs 反事実」のペアデータセットを大規模生成するフレームワーク。

- **目標規模**: 学習用 10,000 件 + テスト用 2,000 件 × 10 パターン（計 30,000 件以上）
- **収集戦略**: No-Rendering モードで座標データを高速収集 → 選択的に Epic 品質で動画レンダリング

## システム構成

```
ローカル macOS                リモート Linux サーバー（GPU）
─────────────────            ──────────────────────────────
make sync ──────────────────> ファイル転送
                              CARLA Server (UE4, Docker)
                                  ↕
                              Python Client (Docker)
                                  ↓
                              data/factual/
                              data/counterfactual_v1〜v10/
                              data/renders/
```

## 動作フェーズ

| フェーズ | 内容 | モード |
|---|---|---|
| Phase 1 | 事実データ収集（座標・速度） | No-Rendering（高速） |
| Phase 2 | 反実仮想介入（6種類） | No-Rendering（高速） |
| Phase 3 | 興味深いシナリオの動画化 | Rendering（Epic品質） |

### Phase 2 の介入種類

| 介入タイプ | 内容 |
|---|---|
| `sensor_noise` | センサーノイズ（車両質量に乱数付与） |
| `aeb_disable` | AEB（自動緊急ブレーキ）の無効化 |
| `brake_degradation` | ブレーキ性能の劣化 |
| `friction_change` | 路面摩擦の低下 |
| `aggressive_npc` | 周辺車両の攻撃的挙動（信号無視・車間距離ゼロ） |
| `combined` | 上記の組み合わせ |

## セットアップ

### 必要条件（リモートサーバー）

- Ubuntu 22.04 LTS
- NVIDIA Driver 550 以上
- NVIDIA Container Toolkit
- Docker Engine 24 以上

### 初回セットアップ

```bash
# ローカルで .env を作成
make setup

# .env を編集（リモートサーバー情報を設定）
# REMOTE_HOST=192.168.1.100
# REMOTE_USER=ubuntu

# ファイルをリモートに転送
make sync REMOTE_HOST=192.168.1.100

# リモートサーバーにSSHログイン
ssh ubuntu@192.168.1.100
cd ~/Carla
make setup
make build-remote
```

## 実行

```bash
# 全フェーズ実行（リモートサーバー上）
make run

# フェーズ個別実行
make phase1 NUM_TRAIN=500 NUM_TEST=100
make phase2 NUM_VERSIONS=5
make phase3

# ログ確認
make logs

# 終了
make down
```

詳細は [command.md](command.md) を参照。

## データ構造

```
data/
├── factual/
│   ├── train_00000.log   # CARLAバイナリログ（replay用）
│   ├── train_00000.h5    # 座標メタデータ
│   └── ...
├── counterfactual_v1/
│   ├── train_00000.h5
│   └── ...
├── counterfactual_v2〜v10/
├── renders/              # Phase 3 の動画フレーム
│   └── train_00000_v1/
│       ├── 000001.png
│       └── ...
└── viz/                  # 2D軌跡プレビュー（最初の10件）
    └── train_00000.png
```

## ファイル構成

```
Carla/
├── main.py               # CLIエントリーポイント
├── src/
│   ├── config.py         # 設定値
│   ├── phase1_collect.py # Phase 1: 事実データ収集
│   ├── phase2_counterfactual.py  # Phase 2: 反実仮想生成
│   ├── phase3_render.py  # Phase 3: 選択的レンダリング
│   └── visualize.py      # 2D軌跡可視化
├── docker/
│   ├── Dockerfile
│   ├── compose.remote.yml  # リモートLinux（GPU）用
│   └── compose.local.yml   # ローカル開発用
├── Makefile
├── requirements.txt
├── command.md            # コマンドリファレンス
└── .env.example
```

## 参考文献

- [CARLA Simulator](https://carla.org/) — CARLA 0.9.15
- CARLA-Round: マルチファクター実験デザイン
- DriveInsight: 反実仮想介入による因果関係解析
- Fault Injection: AEB等の安全機能不具合注入
