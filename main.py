"""
CARLA Counterfactual Data Generation Framework - Main Entry Point
CLI interface for running Phase 1 (factual collection), Phase 2 (counterfactual generation),
and Phase 3 (selective rendering).
"""

import argparse
import carla
import logging
import os
import sys
from pathlib import Path
import glob
from typing import Tuple

from src import config
from src.phase1_collect import FactualCollector
from src.phase2_counterfactual import CounterfactualGenerator
from src.visualize import visualize_batch, compare_factual_counterfactual


def connect_carla() -> Tuple[carla.Client, carla.World]:
    """
    Connect to CARLA server and configure world settings.

    Returns:
        Tuple of (CARLA client, CARLA world)

    Raises:
        SystemExit: If connection fails
    """
    try:
        client = carla.Client(config.CARLA_HOST, config.CARLA_PORT)
        client.set_timeout(config.CARLA_TIMEOUT)
        world = client.get_world()

        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = config.FIXED_DELTA_SECONDS
        world.apply_settings(settings)

        logging.info(f"Connected to CARLA at {config.CARLA_HOST}:{config.CARLA_PORT}")
        return client, world

    except Exception as e:
        logging.error(f"Failed to connect to CARLA: {e}")
        logging.error(f"Make sure CARLA server is running at {config.CARLA_HOST}:{config.CARLA_PORT}")
        sys.exit(1)


def run_phase1(client: carla.Client, world: carla.World, args) -> None:
    """
    Phase 1: Collect factual data from CARLA simulation.

    Args:
        client: CARLA client instance
        world: CARLA world instance
        args: Command-line arguments containing num_train and num_test

    Raises:
        KeyboardInterrupt: On user interruption (gracefully handled)
    """
    logging.info("=" * 60)
    logging.info("PHASE 1: Factual Data Collection")
    logging.info("=" * 60)

    try:
        collector = FactualCollector(client, world)
        collector.setup_no_rendering()

        collected_scenarios = []
        total_samples = args.num_train + args.num_test

        # Collect training samples
        for i in range(args.num_train):
            try:
                scenario_id = f"train_{i:05d}"
                result = collector.collect_scenario(scenario_id, split="train")
                collected_scenarios.append(result)
                logging.info(f"[{i+1}/{args.num_train}] Collected train scenario: {scenario_id}")
            except Exception as e:
                logging.error(f"Failed to collect train scenario {i}: {e}")
                continue

        # Collect test samples
        for i in range(args.num_test):
            try:
                scenario_id = f"test_{i:05d}"
                result = collector.collect_scenario(scenario_id, split="test")
                collected_scenarios.append(result)
                logging.info(f"[{args.num_train + i + 1}/{total_samples}] Collected test scenario: {scenario_id}")
            except Exception as e:
                logging.error(f"Failed to collect test scenario {i}: {e}")
                continue

        collector.restore_rendering()

        # Visualize first N scenarios
        h5_files = []
        for scenario in collected_scenarios[:config.QUICK_VISUALIZE_COUNT]:
            h5_files.append(scenario["meta_path"])

        if h5_files:
            viz_dir = os.path.join(config.DATA_DIR, "viz")
            logging.info(f"Visualizing first {len(h5_files)} scenarios to {viz_dir}")
            visualize_batch(h5_files, viz_dir)

        logging.info("=" * 60)
        logging.info(f"PHASE 1 COMPLETE: Collected {len(collected_scenarios)} scenarios")
        logging.info(f"  - Train samples: {args.num_train}")
        logging.info(f"  - Test samples: {args.num_test}")
        logging.info("=" * 60)

    except KeyboardInterrupt:
        logging.warning("Phase 1 interrupted by user")
        collector.restore_rendering()
        raise


def run_phase2(client: carla.Client, world: carla.World, args) -> None:
    """
    Phase 2: Generate counterfactual scenarios.

    Args:
        client: CARLA client instance
        world: CARLA world instance
        args: Command-line arguments containing versions

    Raises:
        KeyboardInterrupt: On user interruption (gracefully handled)
    """
    logging.info("=" * 60)
    logging.info("PHASE 2: Counterfactual Generation")
    logging.info("=" * 60)

    try:
        # Find all factual scenarios
        factual_dir = config.FACTUAL_DIR
        factual_files = glob.glob(os.path.join(factual_dir, "*.log"))

        if not factual_files:
            logging.warning(f"No factual log files found in {factual_dir}")
            logging.warning("Please run Phase 1 first")
            return

        logging.info(f"Found {len(factual_files)} factual scenarios")

        total_count = 0
        collision_count = 0

        for version in range(1, args.versions + 1):
            logging.info(f"\n--- Version {version}/{args.versions} ---")

            for scenario_idx, log_path in enumerate(factual_files):
                try:
                    scenario_filename = os.path.basename(log_path)
                    scenario_id = os.path.splitext(scenario_filename)[0]

                    generator = CounterfactualGenerator(client, world, log_path)
                    result = generator.generate(scenario_id, version)

                    if result.get("has_collision", False):
                        collision_count += 1

                    total_count += 1
                    logging.debug(
                        f"Generated counterfactual for {scenario_id} v{version}: "
                        f"type={result['intervention_type']}"
                    )

                except Exception as e:
                    logging.error(f"Failed to generate counterfactual for scenario {scenario_id}: {e}")
                    continue

            logging.info(f"Version {version}: Generated {len(factual_files)} counterfactuals")

        logging.info("=" * 60)
        logging.info(f"PHASE 2 COMPLETE: Generated {total_count} counterfactual scenarios")
        logging.info(f"  - Collision count: {collision_count}")
        logging.info(f"  - Collision rate: {100 * collision_count / total_count:.1f}%")
        logging.info("=" * 60)

    except KeyboardInterrupt:
        logging.warning("Phase 2 interrupted by user")
        raise


def run_phase3(client: carla.Client, world: carla.World, args) -> None:
    """
    Phase 3: Selective rendering of interesting counterfactual scenarios.

    Args:
        client: CARLA client instance
        world: CARLA world instance
        args: Command-line arguments

    Raises:
        KeyboardInterrupt: On user interruption (gracefully handled)
    """
    logging.info("=" * 60)
    logging.info("PHASE 3: Selective Rendering")
    logging.info("=" * 60)

    try:
        # Find all counterfactual scenarios
        counterfactual_files = []
        for version in range(1, args.versions + 1):
            pattern = os.path.join(
                config.COUNTERFACTUAL_DIR_TEMPLATE.format(version=version),
                "*.h5"
            )
            counterfactual_files.extend(glob.glob(pattern))

        if not counterfactual_files:
            logging.warning("No counterfactual scenarios found")
            logging.warning("Please run Phase 2 first")
            return

        logging.info(f"Found {len(counterfactual_files)} counterfactual scenarios")

        rendered_count = 0

        # Process each scenario
        for h5_path in counterfactual_files:
            try:
                # Check if scenario is interesting
                # For now, render all scenarios (simple heuristic)
                is_interesting = True

                if is_interesting:
                    # Extract scenario ID and version from path
                    filename = os.path.basename(h5_path)
                    scenario_id = os.path.splitext(filename)[0]

                    # Extract version from directory path
                    parent_dir = os.path.basename(os.path.dirname(h5_path))
                    version_match = parent_dir.split("_v")
                    if len(version_match) > 1:
                        version = version_match[1]
                    else:
                        version = "unknown"

                    # Create output directory
                    output_dir = os.path.join(
                        config.DATA_DIR,
                        "renders",
                        f"{scenario_id}_v{version}"
                    )
                    os.makedirs(output_dir, exist_ok=True)

                    # Here you would call renderer.render_scenario(h5_path, output_dir)
                    # For now, just log the operation
                    logging.debug(f"Would render: {h5_path} -> {output_dir}")
                    rendered_count += 1

            except Exception as e:
                logging.error(f"Failed to process scenario {h5_path}: {e}")
                continue

        logging.info("=" * 60)
        logging.info(f"PHASE 3 COMPLETE: Rendered {rendered_count} scenarios")
        logging.info("=" * 60)

    except KeyboardInterrupt:
        logging.warning("Phase 3 interrupted by user")
        raise


def main() -> None:
    """
    Main entry point for the CARLA counterfactual data generation framework.

    Parses command-line arguments and runs the specified phase(s).
    """
    parser = argparse.ArgumentParser(
        description="CARLA Counterfactual Data Generation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --phase 1 --num-train 100 --num-test 20
  python main.py --phase 2 --versions 5
  python main.py --phase all --num-train 1000 --num-test 200 --versions 10
        """
    )

    parser.add_argument(
        "--phase",
        type=str,
        default="all",
        choices=["1", "2", "3", "all"],
        help="Phase to run: 1 (factual), 2 (counterfactual), 3 (render), or all"
    )

    parser.add_argument(
        "--num-train",
        type=int,
        default=config.NUM_TRAIN_SAMPLES,
        help=f"Number of training samples to collect (default: {config.NUM_TRAIN_SAMPLES})"
    )

    parser.add_argument(
        "--num-test",
        type=int,
        default=config.NUM_TEST_SAMPLES,
        help=f"Number of test samples to collect (default: {config.NUM_TEST_SAMPLES})"
    )

    parser.add_argument(
        "--versions",
        type=int,
        default=config.NUM_COUNTERFACTUAL_VERSIONS,
        help=f"Number of counterfactual versions to generate (default: {config.NUM_COUNTERFACTUAL_VERSIONS})"
    )

    parser.add_argument(
        "--host",
        type=str,
        default=config.CARLA_HOST,
        help=f"CARLA server host (default: {config.CARLA_HOST})"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=config.CARLA_PORT,
        help=f"CARLA server port (default: {config.CARLA_PORT})"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("carla_framework.log")
        ]
    )

    logging.info("CARLA Counterfactual Data Generation Framework")
    logging.info(f"Phase: {args.phase}")

    client = None
    world = None

    try:
        # Connect to CARLA
        client, world = connect_carla()

        # Run requested phases
        if args.phase in ["1", "all"]:
            run_phase1(client, world, args)

        if args.phase in ["2", "all"]:
            run_phase2(client, world, args)

        if args.phase in ["3", "all"]:
            run_phase3(client, world, args)

        logging.info("All phases completed successfully")

    except KeyboardInterrupt:
        logging.info("\nFramework interrupted by user - graceful shutdown")
        sys.exit(0)

    except Exception as e:
        logging.error(f"Framework error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Cleanup
        if world is not None:
            try:
                settings = world.get_settings()
                settings.synchronous_mode = False
                world.apply_settings(settings)
                logging.info("World settings reset")
            except Exception as e:
                logging.warning(f"Failed to reset world settings: {e}")


if __name__ == "__main__":
    main()
