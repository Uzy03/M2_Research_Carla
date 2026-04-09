# CARLA Counterfactual Dataset Generation - Configuration
import os

# --- CARLA Server Connection ---
# Can be overridden by environment variables (useful in Docker)
CARLA_HOST = os.environ.get("CARLA_HOST", "localhost")
CARLA_PORT = int(os.environ.get("CARLA_PORT", "2000"))
CARLA_TIMEOUT = 10.0

# --- Simulation Parameters ---
SYNC_MODE = True
FIXED_DELTA_SECONDS = 0.05  # 20 FPS
MAP_NAME = "Town03"

# --- Dataset Scale ---
NUM_TRAIN_SAMPLES = 10000
NUM_TEST_SAMPLES = 2000
NUM_COUNTERFACTUAL_VERSIONS = 10

# --- Phase 1: Factual Collection ---
SCENARIO_DURATION_STEPS = 400       # 20 seconds at 20 FPS
NUM_NPC_VEHICLES = 20
NUM_NPC_WALKERS = 10
QUICK_VISUALIZE_COUNT = 10          # First N samples to visualize

# --- Phase 2: Counterfactual Intervention ---
# Intervention timing range (seconds from start)
INTERVENTION_TIME_MIN = 3.0
INTERVENTION_TIME_MAX = 8.0

# Brake degradation factor range (0.0 = no brakes, 1.0 = full)
BRAKE_FACTOR_MIN = 0.1
BRAKE_FACTOR_MAX = 0.5

# Sensor noise std dev range
NOISE_STD_MIN = 0.1
NOISE_STD_MAX = 0.5

# Road friction range (default ~0.7)
FRICTION_MIN = 0.1
FRICTION_MAX = 0.4

COUNTERFACTUAL_DURATION_STEPS = 200  # 10 seconds post-intervention

# --- Intervention Types ---
INTERVENTION_TYPES = [
    "sensor_noise",
    "aeb_disable",
    "brake_degradation",
    "friction_change",
    "aggressive_npc",
    "combined",
]

# --- Data Paths ---
DATA_DIR = "data"
FACTUAL_DIR = f"{DATA_DIR}/factual"
COUNTERFACTUAL_DIR_TEMPLATE = f"{DATA_DIR}/counterfactual_v{{version}}"
LOG_SUFFIX = ".log"
META_SUFFIX = ".h5"

# --- Phase 3: Rendering ---
RENDER_IMAGE_WIDTH = 1920
RENDER_IMAGE_HEIGHT = 1080
RENDER_FOV = 90
RENDER_QUALITY = "Epic"
RENDER_CAMERA_HEIGHT = 50.0         # Spectator z offset
