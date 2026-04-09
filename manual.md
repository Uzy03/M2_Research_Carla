# CARLA API 操作マニュアル：AIエージェント操作とデータセット生成

本ドキュメントは、CARLA SimulatorのPython APIを用いて、AIエージェントの自律走行、センサーデータの保存、および反実仮想（Counterfactual）データセット作成のためのレコーダー操作を自動化するための技術リファレンスである。

## 1. サーバー接続と世界（World）の初期化

CARLAサーバー（UE4）に接続し、同期モードを設定する。反実仮想データの生成には、物理演算の確定性を担保するために**同期モード（Synchronous Mode）**が必須である。

```python
import carla
import random

# 1.1 接続設定
client = carla.Client('localhost', 2000)
client.set_timeout(10.0)

# 1.2 世界の取得とマップ変更
world = client.get_world()
# world = client.load_world('Town03')  # 必要に応じてマップ変更

# 1.3 同期モードの設定（確定性確保）
settings = world.get_settings()
settings.synchronous_mode = True
settings.fixed_delta_seconds = 0.05  # 20 FPS固定
world.apply_settings(settings)
```

## 2. AIエージェントのスポーンと自律走行

BehaviorAgent を用いて、周囲の交通状況に反応するリアルな走行エージェントを構成する。

```python
import sys
import os

# CARLAのPythonAPIパスをシステムに追加（インストールパスに合わせて調整）
# sys.path.append('path/to/carla/PythonAPI/carla')
from agents.navigation.behavior_agent import BehaviorAgent

# 2.1 車両のスポーン
blueprint_library = world.get_blueprint_library()
bp = blueprint_library.filter('vehicle.tesla.model3')
spawn_point = random.choice(world.get_map().get_spawn_points())
vehicle = world.spawn_actor(bp, spawn_point)

# 2.2 BehaviorAgentの設定
# 性格設定: 'cautious' (慎重), 'normal' (普通), 'aggressive' (積極的)
agent = BehaviorAgent(vehicle, behavior='normal')

# 目的地（Waypoint）の設定
destination = random.choice(world.get_map().get_spawn_points()).location
agent.set_destination(destination)
```

## 3. センサーデータの記録（データセット生成）

カメラを車両にアタッチし、listen メソッドを用いてフレームごとに画像を保存する。

```python
# 3.1 RGBカメラのセットアップ
cam_bp = blueprint_library.find('sensor.camera.rgb')
cam_bp.set_attribute('image_size_x', '800')
cam_bp.set_attribute('image_size_y', '600')
cam_bp.set_attribute('fov', '90')

# 車両のフロント上部に設置
cam_transform = carla.Transform(carla.Location(x=1.5, z=2.4))
camera = world.spawn_actor(cam_bp, cam_transform, attach_to=vehicle)

# 3.2 データのディスク保存コールバック
# out/ フォルダに画像が保存される
camera.listen(lambda image: image.save_to_disk('out/%06d.png' % image.frame))
```

## 4. レコーダー機能：反実仮想データの生成

「事実（Factual）」のログを記録し、それを再生しながら「反事実（Counterfactual）」の分岐を生成するワークフロー。

### A. 事実（Factual）の記録

```python
# 記録開始
client.start_recorder("factual_scenario.log")

# ループ内でエージェントを動かす
for _ in range(200):
    world.tick()  # サーバーを1ステップ進める
    control = agent.run_step()
    vehicle.apply_control(control)

client.stop_recorder()
```

### B. 反事実（Counterfactual）の再生と介入

記録したログをある時点（例：5秒目）まで再生し、そこからアクションを変えて分岐させる。

```python
# 1. ログを5.0秒目まで正確に再生
# start: 開始秒数, duration: 再生期間, follow_id: 追従対象
client.replay_file("factual_scenario.log", 0, 5.0, vehicle.id)
world.tick()

# 2. 再生終了後、制御を奪って介入（反実仮想の実行）
# オートパイロットをオフにし、ハンドルを左に切るなどの介入
agent.set_autopilot(False)
intervention_control = carla.VehicleControl(throttle=1.0, steer=-1.0)
vehicle.apply_control(intervention_control)

# 3. 分岐した展開をさらに継続してシミュレート
for _ in range(100):
    world.tick()
    # センサーデータは自動的に camera.listen によって保存される
```

## 5. デバッグとクリーンアップ

```python
# 5.1 動画確認用のスペクテイター（神の視点）移動
spectator = world.get_spectator()
transform = vehicle.get_transform()
spectator.set_transform(
    carla.Transform(
        transform.location + carla.Location(z=50),
        carla.Rotation(pitch=-90)
    )
)

# 5.2 終了時のアクター削除
camera.destroy()
vehicle.destroy()
```
