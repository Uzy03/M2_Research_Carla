import logging
import psutil

MEMORY_LIMIT_GB = 30.0
CARLA_SERVER_CONTAINER = "carla-counterfactual-remote-carla-server-1"


class MemoryLimitExceeded(RuntimeError):
    pass


def _stop_server_container():
    """Docker socket経由でCARLAサーバーコンテナを停止する。"""
    try:
        import docker
        client = docker.from_env()
        try:
            container = client.containers.get(CARLA_SERVER_CONTAINER)
            logging.warning(f"コンテナ {CARLA_SERVER_CONTAINER} を停止します...")
            container.stop(timeout=10)
            logging.warning("CARLAサーバーコンテナを停止しました。")
        except docker.errors.NotFound:
            logging.warning(f"コンテナ {CARLA_SERVER_CONTAINER} が見つかりません。")
    except Exception as e:
        logging.error(f"コンテナ停止に失敗しました: {e}")


def check_memory():
    """現在のRAM使用量が MEMORY_LIMIT_GB を超えていたら MemoryLimitExceeded を送出する。"""
    used_gb = psutil.virtual_memory().used / (1024 ** 3)
    if used_gb >= MEMORY_LIMIT_GB:
        msg = f"RAM使用量 {used_gb:.1f}GB が閾値 {MEMORY_LIMIT_GB}GB を超えました"
        logging.error(msg)
        _stop_server_container()
        raise MemoryLimitExceeded(msg)
    logging.debug(f"RAM使用量: {used_gb:.1f}GB / {MEMORY_LIMIT_GB}GB")
