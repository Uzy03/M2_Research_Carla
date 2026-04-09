# CARLA Counterfactual Dataset Generation - Phase 3: Selective Rendering (Visual Verification)

import carla
import os
import h5py
import logging
from src.config import (
    RENDER_IMAGE_WIDTH,
    RENDER_IMAGE_HEIGHT,
    RENDER_FOV,
    RENDER_CAMERA_HEIGHT,
)


class SelectiveRenderer:
    """
    Renders interesting counterfactual scenarios to video frames for visual verification.
    
    Uses CARLA's replay API to reconstruct scenarios and captures RGB camera output.
    Efficiently handles rendering pipeline with enable/disable toggles.
    """

    def __init__(self, client: carla.Client, world: carla.World):
        """
        Initialize the SelectiveRenderer.

        Args:
            client: CARLA client instance
            world: CARLA world instance
        """
        self.client = client
        self.world = world
        self.logger = logging.getLogger(__name__)
        self.camera = None
        self.frame_buffer = []

    def is_interesting(self, counterfactual_h5_path: str) -> bool:
        """
        Determine if a counterfactual result is "physically interesting".

        Criteria:
        - Has collision attribute set to True
        - Vehicle speed decreased significantly (avg velocity < 0.5 m/s)

        Args:
            counterfactual_h5_path: Path to counterfactual H5 metadata file

        Returns:
            bool: True if scenario is interesting, False otherwise
        """
        try:
            with h5py.File(counterfactual_h5_path, "r") as f:
                # Check for collision attribute
                if "has_collision" in f.attrs:
                    if f.attrs["has_collision"]:
                        return True

                # Check for speed change in actors
                if "actors" in f:
                    actors_group = f["actors"]
                    for actor_id in actors_group.keys():
                        actor = actors_group[actor_id]
                        if "velocity" in actor:
                            velocities = actor["velocity"][:]
                            if len(velocities) > 0:
                                avg_velocity = float(
                                    (velocities**2).sum(axis=1) ** 0.5
                                ).mean()
                                if avg_velocity < 0.5:
                                    return True
            return False
        except Exception as e:
            self.logger.warning(
                f"Error checking if scenario is interesting: {e}"
            )
            return False

    def enable_rendering(self) -> None:
        """Enable rendering mode in CARLA world."""
        settings = self.world.get_settings()
        settings.no_rendering_mode = False
        self.world.apply_settings(settings)
        self.logger.debug("Rendering enabled")

    def disable_rendering(self) -> None:
        """Disable rendering mode in CARLA world."""
        settings = self.world.get_settings()
        settings.no_rendering_mode = True
        self.world.apply_settings(settings)
        self.logger.debug("Rendering disabled")

    def attach_camera(
        self, vehicle: carla.Vehicle, output_dir: str
    ) -> carla.Actor:
        """
        Attach RGB camera to vehicle and start listening for frames.

        Camera is positioned 1.5m ahead and 2.4m above vehicle center.

        Args:
            vehicle: Target vehicle actor
            output_dir: Directory to save frame PNG files

        Returns:
            carla.Actor: The camera actor
        """
        blueprint_library = self.world.get_blueprint_library()
        cam_bp = blueprint_library.find("sensor.camera.rgb")
        cam_bp.set_attribute("image_size_x", str(RENDER_IMAGE_WIDTH))
        cam_bp.set_attribute("image_size_y", str(RENDER_IMAGE_HEIGHT))
        cam_bp.set_attribute("fov", str(RENDER_FOV))

        cam_transform = carla.Transform(carla.Location(x=1.5, z=2.4))
        camera = self.world.spawn_actor(
            cam_bp, cam_transform, attach_to=vehicle
        )

        os.makedirs(output_dir, exist_ok=True)

        camera.listen(
            lambda img: img.save_to_disk(
                f"{output_dir}/{img.frame:06d}.png"
            )
        )

        self.camera = camera
        self.logger.debug(
            f"Camera attached to vehicle {vehicle.id} -> {output_dir}"
        )
        return camera

    def render_scenario(
        self,
        factual_log_path: str,
        scenario_id: str,
        version: int,
        output_dir: str,
    ) -> str:
        """
        Render a single counterfactual scenario to video frames.

        Steps:
        1. Enable rendering
        2. Replay the factual log file
        3. Wait for replay to start
        4. Get first vehicle from world
        5. Attach camera to vehicle
        6. Position spectator above vehicle
        7. Capture 200 ticks (10 seconds at 20 FPS)
        8. Cleanup

        Args:
            factual_log_path: Path to factual scenario log file
            scenario_id: Unique scenario identifier
            version: Counterfactual version number
            output_dir: Directory to save rendered frames

        Returns:
            str: Output directory path

        Raises:
            RuntimeError: If vehicle not found or rendering fails
        """
        try:
            self.enable_rendering()

            # Replay the scenario
            self.client.replay_file(factual_log_path, 0, 0, 0)
            self.logger.debug(
                f"Replaying {factual_log_path} for scenario {scenario_id}"
            )

            # Wait for replay to start
            for _ in range(5):
                self.world.tick()

            # Get first vehicle
            vehicles = self.world.get_actors().filter("vehicle.*")
            if len(vehicles) == 0:
                raise RuntimeError(
                    f"No vehicles found in replay for {factual_log_path}"
                )

            vehicle = vehicles[0]
            self.logger.debug(
                f"Found vehicle {vehicle.id} for rendering"
            )

            # Attach camera
            self.attach_camera(vehicle, output_dir)

            # Position spectator above vehicle for monitoring
            spectator = self.world.get_spectator()
            spectator_transform = carla.Transform(
                carla.Location(x=vehicle.get_location().x,
                               y=vehicle.get_location().y,
                               z=RENDER_CAMERA_HEIGHT)
            )
            spectator.set_transform(spectator_transform)

            # Capture frames: 200 ticks = 10 seconds at 20 FPS
            for i in range(200):
                self.world.tick()
                if (i + 1) % 50 == 0:
                    self.logger.debug(
                        f"Rendered {i + 1}/200 frames for {scenario_id}"
                    )

            self.logger.info(
                f"Completed rendering scenario {scenario_id} v{version} "
                f"-> {output_dir}"
            )
            return output_dir

        finally:
            self.cleanup()
            self.disable_rendering()

    def cleanup(self) -> None:
        """Cleanup camera actor if present."""
        if self.camera is not None:
            self.camera.destroy()
            self.camera = None
            self.logger.debug("Camera destroyed")
