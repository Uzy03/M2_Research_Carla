# コマンドリファレンス

## セットアップ

```bash
make setup
```
`.env` ファイルを作成して Python 依存ライブラリをインストールする。初回のみ実行。

```bash
make env
```
`.env.example` を `.env` にコピーする。既存の `.env` は上書きしない。

---

## リモートサーバーへのファイル転送

```bash
make sync REMOTE_HOST=192.168.1.100
make sync REMOTE_HOST=192.168.1.100 REMOTE_USER=ubuntu
```
ローカルのプロジェクトファイルをリモートサーバーに rsync で転送する。  
`data/` と `__pycache__/` は除外される。  
`REMOTE_USER` のデフォルトは `ubuntu`、`REMOTE_DIR` のデフォルトは `~/Carla`。

`.env` に書いておくと引数不要：
```
REMOTE_HOST=192.168.1.100
REMOTE_USER=ubuntu
```

---

## リモート Linux サーバー（GPU環境）

### 前提条件
- NVIDIA Driver 550 以上
- NVIDIA Container Toolkit インストール済み
- Docker Engine 24 以上

### ビルド

```bash
make build-remote
```
Python クライアントの Docker イメージをビルドする。コードを変更したら再実行。

### 起動・停止

```bash
make up
```
CARLA サーバーをバックグラウンドで起動する。

```bash
make down
```
CARLA サーバーとクライアントコンテナをすべて停止・削除する。

```bash
make logs
```
CARLA サーバーのログをリアルタイムで表示する（`Ctrl+C` で抜ける）。

```bash
make shell
```
クライアントコンテナに bash で入る。デバッグ用。

### データ収集・生成

```bash
make phase1
```
Phase 1：No-Rendering モードで事実データ（座標・速度）を収集する。  
デフォルト: 学習用 10,000 件 + テスト用 2,000 件。

```bash
make phase2
```
Phase 2：Phase 1 のログを replay して反実仮想介入を生成する。  
デフォルト: 10 バージョン × 全シナリオ。

```bash
make phase3
```
Phase 3：衝突など「物理的に興味深い」反実仮想のみを Epic 品質で動画レンダリングする。

```bash
make run
```
Phase 1 → 2 → 3 を順番に全て実行する。

### パラメータ上書き

コマンドライン引数で件数・バージョン数を変更できる：

```bash
make phase1 NUM_TRAIN=500 NUM_TEST=100
make phase2 NUM_VERSIONS=5
make run NUM_TRAIN=1000 NUM_TEST=200 NUM_VERSIONS=3
```

---

## ローカル実行（GPU なし・開発・テスト用）

> CARLA サーバーは UE4 ベースのため、GPU なしでは低速になる。  
> 小規模テストや動作確認に用いる。

### ビルド

```bash
make build-local
```

### データ収集・生成

```bash
make phase1-local   # 学習 100 件 / テスト 20 件の小規模テスト
make phase2-local   # バージョン 3 で生成
make phase3-local   # レンダリング
make run-local      # 全フェーズ（.env の NUM_TRAIN / NUM_TEST / NUM_VERSIONS を使用）
```

### 停止

```bash
make down-local
```
ローカルの CARLA サーバーコンテナを停止・削除する。

---

## クリーンアップ

```bash
make clean
```
Docker イメージ・コンテナ・ボリュームを削除する。イメージを作り直したいときに使う。

```bash
make clean-data
```
`data/` 以下のデータをすべて削除する。実行前に確認プロンプトが出る。

```bash
make clean-all
```
`make clean` + `make clean-data` を両方実行する。

---

## 典型的なワークフロー

### リモートサーバーで初めて実行する場合

```bash
# 1. ローカルmacOSでファイルを転送
make sync REMOTE_HOST=192.168.1.100

# 2. リモートサーバーにSSHログイン
ssh ubuntu@192.168.1.100
cd ~/Carla

# 3. セットアップ（初回のみ）
make setup
make build-remote

# 4. 実行
make run

# 5. 終了後
make down
```

### コードを修正して再実行する場合

```bash
# ローカルで修正後、転送 → 再ビルド → 実行
make sync REMOTE_HOST=192.168.1.100
ssh ubuntu@192.168.1.100 "cd ~/Carla && make build-remote && make run"
```

### フェーズを個別に実行する場合

```bash
make phase1 NUM_TRAIN=200 NUM_TEST=50   # まず小規模で確認
make phase2 NUM_VERSIONS=2
make phase3
```
