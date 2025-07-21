#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "click",
#     "kubernetes",
# ]
# ///

import logging
from pathlib import Path
import shutil
import time
import click
from kubernetes import client, config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--label-selector",
    envvar="KUBERNETES_LABEL_SELECTOR",
    help="Label selector for filtering ConfigMaps",
    required=True,
    type=str,
)
@click.option(
    "--namespace",
    default="default",
    envvar="KUBERNETES_NAMESPACE",
    required=True,
    type=str,
)
@click.option(
    "--output-dir",
    help="Directory to write config files",
    required=True,
    type=click.Path(exists=False, file_okay=False, writable=True),
)
@click.option(
    "--sleep",
    default=30,
    help="Sleep interval between syncs",
    required=True,
    type=int,
)
def main(
    label_selector: str,
    namespace: str,
    output_dir: str | Path,
    sleep: int,
):
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Load Kubernetes config
    logger.info("Loading Kubernetes config...")
    try:
        config.load_incluster_config()
    except config.config_exception.ConfigException:
        config.load_kube_config()
    else:
        logger.info("Kubernetes config loaded successfully")

    # Create Kubernetes API client
    api = client.CoreV1Api()

    # Monitor loop
    while True:
        # Retrieve ConfigMaps with the specified label selector
        configmaps = api.list_namespaced_config_map(
            namespace=namespace,
            label_selector=label_selector,
        )
        logger.info(
            f'Fetched {len(configmaps.items)} ConfigMaps with selector "{label_selector}"'
        )

        # Delete saved ConfigMaps no longer matching the specified label selector
        desired_configmap_names = {cm.metadata.name for cm in configmaps.items}
        current_configmap_names = {cm.name for cm in output_dir_path.iterdir()}
        for cm_name in current_configmap_names - desired_configmap_names:
            cm_dir = output_dir_path / cm_name
            shutil.rmtree(cm_dir, ignore_errors=True)
            logger.info(f"Deleted directory: {cm_dir} (no matching ConfigMap)")

        # Save ConfigMaps matching the specified label selector
        for cm in configmaps.items:
            cm_dir = output_dir_path / cm.metadata.name
            cm_dir.mkdir(parents=True, exist_ok=True)

            # Delete files with names not matching any key in the ConfigMap
            existing_file_names = {x.name for x in cm_dir.iterdir()}
            desired_file_names = set(cm.data.keys())
            for file_name in existing_file_names - desired_file_names:
                file_path = cm_dir / file_name
                file_path.unlink(missing_ok=True)
                logger.info(f"Deleted file: {file_path}")

            # Write files for keys in the ConfigMap
            for key, value in cm.data.items():
                file_path = cm_dir / key
                file_path.write_text(value)
                file_path.chmod(0o644)
                logger.info(f"Wrote file: {file_path}")

        # Sleep before next iteration
        time.sleep(sleep)


if __name__ == "__main__":
    main()
