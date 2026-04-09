"""
Phase 1: Factual Data Collection from CARLA Simulation
Collects high-speed coordinate data in no-rendering mode.
"""

import carla
import logging
import os
import random
import numpy as np
import h5py
from typing import List, Tuple, Dict

from src.config import (
    FIXED_DELTA_SECONDS,
    NUM_NPC_VEHICLES,
    NUM_NPC_WALKERS,
    SCENARIO_DURATION_STEPS,
    FACTUAL_DIR,
)


class FactualCollector:
    """Collects factual scenario data from CARLA in no-rendering mode."""

    def __init__(self, client: carla.Client, world: carla.World):
        """
        Initialize the factual collector.

        Args:
            client: CARLA client instance
            world: CARLA world instance
        """
        self.client = client
        self.world = world
        self.logger = logging.getLogger(__name__)

    def setup_no_rendering(self) -> None:
        """Enable no-rendering mode for faster data collection."""
        settings = self.world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = FIXED_DELTA_SECONDS
        settings.no_rendering_mode = True
        self.world.apply_settings(settings)
        self.logger.info("No-rendering mode enabled")

    def restore_rendering(self) -> None:
        """Disable no-rendering mode to restore normal rendering."""
        settings = self.world.get_settings()
        settings.no_rendering_mode = False
        self.world.apply_settings(settings)
        self.logger.info("Rendering mode restored")

    def spawn_traffic(
        self, num_vehicles: int = NUM_NPC_VEHICLES, num_walkers: int = NUM_NPC_WALKERS
    ) -> Tuple[List[carla.Actor], List[carla.Actor]]:
        """
        Spawn NPC vehicles and walkers.

        Args:
            num_vehicles: Number of NPC vehicles to spawn
            num_walkers: Number of NPC walkers to spawn

        Returns:
            Tuple of (vehicles list, walkers list)
        """
        vehicles = []
        walkers = []
        blueprint_library = self.world.get_blueprint_library()
        traffic_manager = self.client.get_trafficmanager()

        # Spawn vehicles
        vehicle_blueprints = blueprint_library.filter("vehicle.*")
        vehicle_blueprints = [bp for bp in vehicle_blueprints if int(bp.get_attribute("number_of_wheels")) == 4]

        spawn_points = self.world.get_map().get_spawn_points()
        for _ in range(num_vehicles):
            if not spawn_points:
                break
            try:
                bp = random.choice(vehicle_blueprints)
                spawn_point = random.choice(spawn_points)
                vehicle = self.world.spawn_actor(bp, spawn_point)
                vehicle.set_autopilot(True, traffic_manager.get_port())
                vehicles.append(vehicle)
                self.logger.debug(f"Spawned vehicle {vehicle.id}")
            except Exception as e:
                self.logger.warning(f"Failed to spawn vehicle: {e}")

        # Spawn walkers
        walker_blueprints = blueprint_library.filter("walker.pedestrian.*")
        walker_controller_bp = blueprint_library.find("controller.ai.walker")

        for _ in range(num_walkers):
            if not spawn_points:
                break
            try:
                bp = random.choice(walker_blueprints)
                spawn_point = random.choice(spawn_points)
                walker = self.world.spawn_actor(bp, spawn_point)
                controller = self.world.spawn_actor(walker_controller_bp, carla.Transform(), walker)
                controller.start()
                controller.go_to_location(self.world.get_random_location_from_navigation())
                walkers.append(walker)
                self.logger.debug(f"Spawned walker {walker.id}")
            except Exception as e:
                self.logger.warning(f"Failed to spawn walker: {e}")

        self.logger.info(f"Spawned {len(vehicles)} vehicles and {len(walkers)} walkers")
        return vehicles, walkers

    def collect_scenario(self, scenario_id: str, split: str = "train") -> Dict:
        """
        Collect one scenario's worth of factual data.

        Args:
            scenario_id: Unique scenario identifier
            split: Dataset split ('train' or 'test')

        Returns:
            Dictionary with scenario metadata
        """
        # Ensure FACTUAL_DIR exists
        os.makedirs(FACTUAL_DIR, exist_ok=True)

        vehicles = None
        walkers = None
        try:
            # Spawn traffic
            vehicles, walkers = self.spawn_traffic()

            # Start recording
            log_path = os.path.join(FACTUAL_DIR, f"{scenario_id}.log")
            self.client.start_recorder(log_path)
            self.logger.info(f"Started recording to {log_path}")

            # Collect states during simulation
            states = {"frames": [], "actors": {}}
            for frame in range(SCENARIO_DURATION_STEPS):
                self.world.tick()
                step_data = self._collect_step_states()
                self._accumulate_states(step_data, frame, states)

            # Stop recording
            self.client.stop_recorder()
            self.logger.info("Stopped recording")

            # Save H5 file
            meta_path = os.path.join(FACTUAL_DIR, f"{scenario_id}.h5")
            self._save_h5(meta_path, states, scenario_id)

            result = {
                "scenario_id": scenario_id,
                "log_path": log_path,
                "meta_path": meta_path,
                "num_frames": len(states["frames"]),
                "num_actors": len(states["actors"]),
            }
            self.logger.info(
                f"Collected scenario {scenario_id}: {result['num_frames']} frames, "
                f"{result['num_actors']} actors"
            )
            return result

        finally:
            # Cleanup: destroy all actors
            if vehicles:
                for vehicle in vehicles:
                    try:
                        vehicle.destroy()
                    except Exception as e:
                        self.logger.warning(f"Failed to destroy vehicle {vehicle.id}: {e}")

            if walkers:
                for walker in walkers:
                    try:
                        walker.destroy()
                    except Exception as e:
                        self.logger.warning(f"Failed to destroy walker {walker.id}: {e}")

            self.logger.info("Cleaned up all actors")

    def _collect_step_states(self) -> Dict:
        """
        Collect actor states at current simulation step.

        Returns:
            Dict mapping actor_id (str) to {'x', 'y', 'z', 'vx', 'vy', 'vz'}
        """
        step_data = {}
        for actor in self.world.get_actors().filter("vehicle.*"):
            try:
                transform = actor.get_transform()
                velocity = actor.get_velocity()

                step_data[str(actor.id)] = {
                    "x": transform.location.x,
                    "y": transform.location.y,
                    "z": transform.location.z,
                    "vx": velocity.x,
                    "vy": velocity.y,
                    "vz": velocity.z,
                }
            except Exception as e:
                self.logger.warning(f"Failed to collect state for actor {actor.id}: {e}")

        return step_data

    def _accumulate_states(self, step_data: Dict, frame: int, states: Dict) -> None:
        """
        Accumulate state data for frame tracking.

        Args:
            step_data: State data from current step
            frame: Current frame number
            states: Accumulator dictionary to update in-place
        """
        states["frames"].append(frame)

        for actor_id, data in step_data.items():
            if actor_id not in states["actors"]:
                states["actors"][actor_id] = {
                    "x": [],
                    "y": [],
                    "z": [],
                    "vx": [],
                    "vy": [],
                    "vz": [],
                }

            states["actors"][actor_id]["x"].append(data["x"])
            states["actors"][actor_id]["y"].append(data["y"])
            states["actors"][actor_id]["z"].append(data["z"])
            states["actors"][actor_id]["vx"].append(data["vx"])
            states["actors"][actor_id]["vy"].append(data["vy"])
            states["actors"][actor_id]["vz"].append(data["vz"])

    def _save_h5(self, output_path: str, states: Dict, scenario_id: str) -> None:
        """
        Save collected states to HDF5 file.

        Args:
            output_path: Path to output HDF5 file
            states: Accumulated state data
            scenario_id: Scenario identifier
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with h5py.File(output_path, "w") as f:
            # Store metadata
            f.attrs["scenario_id"] = scenario_id

            # Store frame numbers
            f.create_dataset("frames", data=np.array(states["frames"], dtype=np.int32))

            # Store actor trajectories
            actors_group = f.create_group("actors")
            for actor_id, actor_data in states["actors"].items():
                actor_group = actors_group.create_group(actor_id)
                actor_group.create_dataset("x", data=np.array(actor_data["x"], dtype=np.float32))
                actor_group.create_dataset("y", data=np.array(actor_data["y"], dtype=np.float32))
                actor_group.create_dataset("z", data=np.array(actor_data["z"], dtype=np.float32))
                actor_group.create_dataset("vx", data=np.array(actor_data["vx"], dtype=np.float32))
                actor_group.create_dataset("vy", data=np.array(actor_data["vy"], dtype=np.float32))
                actor_group.create_dataset("vz", data=np.array(actor_data["vz"], dtype=np.float32))

        self.logger.info(f"Saved H5 metadata to {output_path}")
