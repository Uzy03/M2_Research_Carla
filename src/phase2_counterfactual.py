"""
Phase 2: Counterfactual Scenario Generation
Generates counterfactual scenarios by replaying factual logs and applying interventions.
"""

import carla
import numpy as np
import h5py
import os
from typing import Dict, List, Any

from src import config


class CounterfactualGenerator:
    """Generate counterfactual scenarios by intervening at specific times."""

    def __init__(
        self,
        client: carla.Client,
        world: carla.World,
        factual_log_path: str,
    ):
        """
        Initialize the counterfactual generator.

        Args:
            client: CARLA client connection
            world: CARLA world object
            factual_log_path: Path to factual scenario log file
        """
        self.client = client
        self.world = world
        self.factual_log_path = factual_log_path
        self.rng = np.random.default_rng()

    def generate(self, scenario_id: str, version: int) -> Dict[str, Any]:
        """
        Generate one counterfactual scenario.

        Args:
            scenario_id: Unique scenario identifier
            version: Counterfactual version number

        Returns:
            Dictionary with scenario metadata
        """
        try:
            # Choose random intervention time and type
            t_intervention = self.rng.uniform(
                config.INTERVENTION_TIME_MIN, config.INTERVENTION_TIME_MAX
            )
            intervention_type = self.rng.choice(list(config.INTERVENTION_TYPES))

            # Replay factual log up to intervention time
            frames_to_replay = int(t_intervention / config.FIXED_DELTA_SECONDS)
            self.client.replay_file(
                self.factual_log_path,
                start=0,
                duration=t_intervention,
                follow_id=0,
            )

            # Complete replay by ticking world
            for _ in range(5):
                self.world.tick()

            # Apply intervention
            self._apply_intervention(intervention_type)

            # Tick once to apply intervention changes
            self.world.tick()

            # Collect states after intervention
            states = self._collect_states(config.COUNTERFACTUAL_DURATION_STEPS)

            # Prepare output path
            output_dir = config.COUNTERFACTUAL_DIR_TEMPLATE.format(version=version)
            output_path = os.path.join(output_dir, f"{scenario_id}.h5")

            # Save to h5 file
            metadata = {
                "scenario_id": scenario_id,
                "intervention_type": intervention_type,
                "intervention_time": t_intervention,
                "version": version,
            }
            self._save_h5(output_path, states, metadata)

            return {
                "scenario_id": scenario_id,
                "version": version,
                "intervention_type": intervention_type,
                "intervention_time": t_intervention,
                "output_path": output_path,
                "has_collision": states.get("has_collision", False),
            }

        except Exception as e:
            print(f"Error generating counterfactual for {scenario_id}: {e}")
            raise

    def _apply_intervention(self, intervention_type: str) -> None:
        """
        Route to specific intervention method.

        Args:
            intervention_type: Type of intervention to apply
        """
        if intervention_type == "sensor_noise":
            self._intervene_sensor_noise()
        elif intervention_type == "aeb_disable":
            self._intervene_aeb_disable()
        elif intervention_type == "brake_degradation":
            self._intervene_brake_degradation()
        elif intervention_type == "friction_change":
            self._intervene_friction_change()
        elif intervention_type == "aggressive_npc":
            self._intervene_aggressive_npc()
        elif intervention_type == "combined":
            self._intervene_sensor_noise()
            self._intervene_brake_degradation()
            self._intervene_aggressive_npc()
        else:
            print(f"Unknown intervention type: {intervention_type}")

    def _intervene_sensor_noise(self) -> None:
        """Add sensor noise by modifying vehicle mass."""
        try:
            vehicles = self.world.get_actors().filter("vehicle.*")

            for vehicle in vehicles:
                try:
                    physics_control = vehicle.get_physics_control()

                    # Add random noise to mass (5-20% increase)
                    noise_factor = self.rng.uniform(
                        config.NOISE_STD_MIN, config.NOISE_STD_MAX
                    )
                    original_mass = physics_control.mass
                    physics_control.mass = original_mass * (1.0 + noise_factor)

                    vehicle.apply_physics_control(physics_control)
                except Exception as e:
                    print(f"Failed to apply sensor noise to {vehicle.id}: {e}")

        except Exception as e:
            print(f"Error in sensor noise intervention: {e}")

    def _intervene_aeb_disable(self) -> None:
        """Disable AEB and collision detection."""
        try:
            tm = self.client.get_trafficmanager()
            vehicles = self.world.get_actors().filter("vehicle.*")

            for vehicle in vehicles:
                try:
                    # Increase speed difference to simulate AEB disabling
                    tm.vehicle_percentage_speed_difference(vehicle, 30.0)

                    # Disable auto lane change
                    tm.auto_lane_change(vehicle, False)

                    # Disable collision detection with other vehicles
                    for other in vehicles:
                        if vehicle.id != other.id:
                            tm.collision_detection(vehicle, other, False)

                except Exception as e:
                    print(f"Failed to disable AEB for {vehicle.id}: {e}")

        except Exception as e:
            print(f"Error in AEB disable intervention: {e}")

    def _intervene_brake_degradation(self) -> None:
        """Degrade brake performance."""
        try:
            vehicles = self.world.get_actors().filter("vehicle.*")

            for vehicle in vehicles:
                try:
                    physics_control = vehicle.get_physics_control()

                    # Reduce max brake torque
                    brake_factor = self.rng.uniform(
                        config.BRAKE_FACTOR_MIN, config.BRAKE_FACTOR_MAX
                    )

                    for wheel in physics_control.wheels:
                        wheel.max_brake_torque *= brake_factor

                    vehicle.apply_physics_control(physics_control)
                except Exception as e:
                    print(f"Failed to apply brake degradation to {vehicle.id}: {e}")

        except Exception as e:
            print(f"Error in brake degradation intervention: {e}")

    def _intervene_friction_change(self) -> None:
        """Change road friction by modifying tire friction."""
        try:
            vehicles = self.world.get_actors().filter("vehicle.*")

            for vehicle in vehicles:
                try:
                    physics_control = vehicle.get_physics_control()

                    # Modify tire friction
                    friction = self.rng.uniform(config.FRICTION_MIN, config.FRICTION_MAX)

                    for wheel in physics_control.wheels:
                        wheel.tire_friction = friction

                    vehicle.apply_physics_control(physics_control)
                except Exception as e:
                    print(f"Failed to apply friction change to {vehicle.id}: {e}")

        except Exception as e:
            print(f"Error in friction change intervention: {e}")

    def _intervene_aggressive_npc(self) -> None:
        """Make NPC vehicles drive aggressively."""
        try:
            tm = self.client.get_trafficmanager()
            vehicles = self.world.get_actors().filter("vehicle.*")

            for vehicle in vehicles:
                try:
                    # Set distance to leading vehicle to 0
                    tm.distance_to_leading_vehicle(vehicle, 0.0)

                    # Increase speed by 50%
                    tm.vehicle_percentage_speed_difference(vehicle, -50.0)

                    # Ignore traffic lights
                    tm.ignore_lights_percentage(vehicle, 100.0)

                except Exception as e:
                    print(f"Failed to make {vehicle.id} aggressive: {e}")

        except Exception as e:
            print(f"Error in aggressive NPC intervention: {e}")

    def _collect_states(self, num_steps: int) -> Dict[str, Any]:
        """
        Collect vehicle states for specified number of steps.

        Args:
            num_steps: Number of simulation steps to collect

        Returns:
            Dictionary containing frames, actors, and collision info
        """
        try:
            frames = []
            actors_data = {}
            has_collision = False

            for step in range(num_steps):
                self.world.tick()

                # Record frame number
                frame_num = self.world.get_snapshot().frame

                vehicles = self.world.get_actors().filter("vehicle.*")

                for vehicle in vehicles:
                    actor_id = str(vehicle.id)

                    # Initialize actor data structure
                    if actor_id not in actors_data:
                        actors_data[actor_id] = {
                            "x": [],
                            "y": [],
                            "z": [],
                            "vx": [],
                            "vy": [],
                            "vz": [],
                        }

                    # Get position
                    loc = vehicle.get_location()
                    vel = vehicle.get_velocity()

                    # Append state
                    actors_data[actor_id]["x"].append(loc.x)
                    actors_data[actor_id]["y"].append(loc.y)
                    actors_data[actor_id]["z"].append(loc.z)
                    actors_data[actor_id]["vx"].append(vel.x)
                    actors_data[actor_id]["vy"].append(vel.y)
                    actors_data[actor_id]["vz"].append(vel.z)

                    # Check for collisions
                    if hasattr(vehicle, "collision_history"):
                        if len(vehicle.collision_history) > 0:
                            has_collision = True

                frames.append(frame_num)

            # Convert lists to numpy arrays
            for actor_id in actors_data:
                for key in actors_data[actor_id]:
                    actors_data[actor_id][key] = np.array(
                        actors_data[actor_id][key], dtype=np.float32
                    )

            return {
                "frames": frames,
                "actors": actors_data,
                "has_collision": has_collision,
            }

        except Exception as e:
            print(f"Error collecting states: {e}")
            raise

    def _save_h5(
        self, output_path: str, states: Dict[str, Any], metadata: Dict[str, Any]
    ) -> None:
        """
        Save collected states to HDF5 file.

        Args:
            output_path: Path to output HDF5 file
            states: Collected state data
            metadata: Scenario metadata
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with h5py.File(output_path, "w") as f:
                # Save metadata as attributes
                meta_group = f.create_group("metadata")
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float)):
                        meta_group.attrs[key] = value

                # Save frames
                frames_array = np.array(states["frames"], dtype=np.int32)
                f.create_dataset("frames", data=frames_array)

                # Save actor data
                actors_group = f.create_group("actors")
                for actor_id, actor_states in states["actors"].items():
                    actor_group = actors_group.create_group(actor_id)

                    for key, values in actor_states.items():
                        actor_group.create_dataset(key, data=values)

                # Save collision info
                f.attrs["has_collision"] = states.get("has_collision", False)

            print(f"Saved counterfactual scenario to {output_path}")

        except Exception as e:
            print(f"Error saving H5 file {output_path}: {e}")
            raise
