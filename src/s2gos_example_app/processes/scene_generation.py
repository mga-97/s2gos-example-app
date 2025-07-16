from pathlib import Path
from typing import Optional

from s2gos_common.models import Link
from s2gos_server.provider import get_service

from s2gos_generator.core import SceneGenerationPipeline
from s2gos_generator.core.config import SceneGenConfig

service = get_service()


@service.process(
    id="generate_scene",
    title="Generate S2GOS scene given a complete scene configuration.",
    description=(
        "Generate a complete synthetic scene using a SceneGenConfig object. "
        "The server will validate the configuration before processing. "
        "This process creates all necessary assets and a final scene YAML file."
    ),
)
def generate_scene(config: SceneGenConfig) -> Link:
    """
    Generate a synthetic scene using the SceneGenerationPipeline from a validated
    SceneGenConfig object.

    Args:
        config: A complete and validated SceneGenConfig object, provided by the
                server from the client's request body.

    Returns:
        A Link object pointing to the generated scene's YAML file.
    """
    print(f"Received valid configuration for scene: {config.scene_name}")
    print(f"Output will be generated in a subdirectory of: {config.output_dir}")

    if isinstance(config.output_dir, str):
        config.output_dir = Path(config.output_dir).resolve()
    else:
        config.output_dir = config.output_dir.resolve()
        
    if hasattr(config, 'data_sources') and config.data_sources:
        if isinstance(config.data_sources.dem_root_dir, str):
            config.data_sources.dem_root_dir = Path(config.data_sources.dem_root_dir)
        if isinstance(config.data_sources.landcover_root_dir, str):
            config.data_sources.landcover_root_dir = Path(config.data_sources.landcover_root_dir)
        if isinstance(config.data_sources.dem_index_path, str):
            config.data_sources.dem_index_path = Path(config.data_sources.dem_index_path)
        if isinstance(config.data_sources.landcover_index_path, str):
            config.data_sources.landcover_index_path = Path(config.data_sources.landcover_index_path)
        if isinstance(config.data_sources.material_config_path, str):
            config.data_sources.material_config_path = Path(config.data_sources.material_config_path)
    
    print(f"Resolved absolute output directory: {config.output_dir}")
    print(f"Resolved absolute scene output directory: {config.scene_output_dir}")
    
    pipeline = SceneGenerationPipeline(config)
    scene_description = pipeline.run_full_pipeline()
    print(f"\nSuccess! Scene generated: {scene_description.name}")

    scene_output_dir = Path(config.scene_output_dir) if isinstance(config.scene_output_dir, str) else config.scene_output_dir
    output_file = scene_output_dir / f"{scene_description.name}.yml"
    href = output_file.resolve().as_uri()

    return Link(
        href=href,
        type="application/x-yaml",
        title=f"Scene Description for {scene_description.name}"
    )