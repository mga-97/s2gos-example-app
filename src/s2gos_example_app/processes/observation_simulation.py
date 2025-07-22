# from pathlib import Path
# from typing import Optional

# from s2gos_common.models import Link
# from s2gos_utils import SceneDescription
# from s2gos_simulator.config import SimulationConfig
# from s2gos_simulator.backends.eradiate_backend import EradiateBackend, ERADIATE_AVAILABLE

# from s2gos_server.provider import get_service

# service = get_service()


# @service.process(
#     id="simulate_observation",
#     title="Simulate S2GOS observations.",
#     description=(
#         "Simulates observation from a scene that follows the scene description standard. "
#         "Saves it as netcdf in a temporary location. "
#         "Requires installed dask, xarray, and zarr packages."
#     ),
# )
# def simulate_observation(
#     scene_file_path: str,
#     simulation_config: SimulationConfig,
#     output_path: Optional[str] = None,
# ) -> Link:
#     """Run observation simulation using EradiateBackend."""

#     print(f"Starting simulation process...")
#     print(f"Scene file path: {scene_file_path}")
#     print(f"Simulation config: {simulation_config.name}")
#     print(f"Output path: {output_path}")

#     try:
#         if not ERADIATE_AVAILABLE:
#             error_msg = "Eradiate backend is not available. Please install Eradiate to run simulations."
#             print(f"ERROR: {error_msg}")
#             raise RuntimeError(error_msg)

#         scene_file = Path(scene_file_path)
#         if not scene_file.is_absolute():
#             scene_file = scene_file.resolve()
        
#         print(f"Resolved scene file path: {scene_file}")
        
#         if not scene_file.exists():
#             error_msg = f"Scene file not found: {scene_file}"
#             print(f"ERROR: {error_msg}")
#             if scene_file.parent.exists():
#                 print(f"Available files in {scene_file.parent}:")
#                 for f in scene_file.parent.iterdir():
#                     print(f"  - {f}")
#             raise FileNotFoundError(error_msg)
        
#         print(f"Scene file found, loading...")
        
#         scene = SceneDescription.load_yaml(scene_file)
#         print(f"Scene loaded successfully: {scene.name}")
        
#         print(f"Initializing EradiateBackend...")
#         backend = EradiateBackend(simulation_config)
#         print(f"Backend initialized successfully")
        
#         if not output_path:
#             output_path = "./s2gos_example_app_output"
        
#         output_dir = Path(output_path)
#         if not output_dir.is_absolute():
#             output_dir = output_dir.resolve()
        
#         print(f"Resolved output directory: {output_dir}")
        
#         output_dir.mkdir(parents=True, exist_ok=True)
#         print(f"Output directory created/verified: {output_dir}")
        
#         print(f"Starting simulation...")
#         scene_directory = scene_file.parent  # This is where the scene assets (textures, meshes) are located
#         print(f"Scene directory (for assets): {scene_directory}")
#         result = backend.run_simulation(
#             scene,
#             scene_directory,
#             plot_image=False
#         )
#         print(f"Simulation completed successfully!")
#         print(f"Result: {result}")

#         href = output_dir.as_uri()
        
#         return Link(href=href, type="application/octet-stream", title="Simulation Results")
        
#     except Exception as e:
#         print(f"ERROR: Simulation failed with exception: {e}")
#         print(f"Exception type: {type(e)}")
#         import traceback
#         traceback.print_exc()
#         raise









import pickle
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Optional

from s2gos_common.models import Link
from s2gos_utils import SceneDescription
from s2gos_simulator.config import SimulationConfig
from s2gos_simulator.backends.eradiate_backend import EradiateBackend, ERADIATE_AVAILABLE

from s2gos_server.provider import get_service

service = get_service()


@service.process(
    id="simulate_observation",
    title="Simulate S2GOS observations.",
    description=(
        "Simulates observation from a scene that follows the scene description standard. "
        "Saves it as netcdf in a temporary location. "
        "Requires installed dask, xarray, and zarr packages."
    ),
)
def simulate_observation(
    scene_file_path: str,
    simulation_config: SimulationConfig,
    output_path: Optional[str] = None,
) -> Link:
    """Run observation simulation using EradiateBackend."""

    print(f"Starting simulation process for scene: {scene_file_path}")

    try:
        if not ERADIATE_AVAILABLE:
            raise RuntimeError("Eradiate backend is not available.")

        scene_file = Path(scene_file_path).resolve()
        if not scene_file.exists():
            raise FileNotFoundError(f"Scene file not found: {scene_file}")

        scene = SceneDescription.load_yaml(scene_file)
        
        output_dir_str = output_path or "./s2gos_example_app_output"
        output_dir = Path(output_dir_str).resolve()

        # This string is a self-contained script to run the Eradiate backend.
        worker_script = """
import pickle, sys, traceback
from pathlib import Path
from s2gos_utils import SceneDescription
from s2gos_simulator.config import SimulationConfig
from s2gos_simulator.backends.eradiate_backend import EradiateBackend

try:
    with open(sys.argv[1], 'rb') as f: data = pickle.load(f)
    output_dir, scene_file = Path(sys.argv[2]), Path(sys.argv[3])

    print("Subprocess: Initializing EradiateBackend...")
    backend = EradiateBackend(data['config'])
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Subprocess: Starting simulation...")
    result = backend.run_simulation(data['scene'], scene_file.parent, plot_image=False)
    print(f"Subprocess finished successfully. Result: {result}")
    sys.exit(0)
except Exception:
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            worker_path = temp_dir_path / "worker.py"
            data_path = temp_dir_path / "data.pkl"

            worker_path.write_text(worker_script)
            with open(data_path, 'wb') as f:
                pickle.dump({'scene': scene, 'config': simulation_config}, f)

            command = [sys.executable, str(worker_path), str(data_path), str(output_dir), str(scene_file)]
            
            print("Spawning Eradiate subprocess...")
            proc = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
            print(proc.stdout)
            if proc.stderr:
                print(proc.stderr, file=sys.stderr)
            print("Subprocess completed.")

        return Link(href=output_dir.as_uri(), type="application/octet-stream", title="Simulation Results")
        
    except Exception as e:
        print(f"ERROR: Simulation failed: {e}", file=sys.stderr)
        if isinstance(e, subprocess.CalledProcessError):
            print("--- SUBPROCESS STDERR ---", file=sys.stderr)
            print(e.stderr, file=sys.stderr)
        else:
            traceback.print_exc(file=sys.stderr)
        raise