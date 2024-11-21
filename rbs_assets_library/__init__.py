import enum
import os
import tempfile
from pathlib import Path
from typing import IO, List, Union


def get_models_path() -> str:
    """
    Return the path where the models have been installed.

    Returns:
        A string containing the path of the models.
    """
    models_dir = os.path.join(os.path.dirname(__file__))
    return models_dir + "/models/"


def get_worlds_path() -> str:
    """
    Return the path where the worlds have been installed.

    Returns:
        A string containing the path of the worlds.
    """
    models_dir = os.path.join(os.path.dirname(__file__))
    return models_dir + "/worlds/"

def get_model_names() -> List[str]:
    """
    Return the names of the available robots.

    The name of the robot matches with the folder containing its model file.

    Returns:
        A list of strings containing the available models.
    """
    root_dir = get_models_path()
    dirs = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]
    return [d for d in dirs if not d.startswith("__")]


def get_world_names() -> list[str]:
    root_dir = get_worlds_path()
    files = [
        f.split(".")[0] for f in os.listdir(root_dir) if os.path.isfile(os.path.join(root_dir, f))
    ]
    return [f for f in files if not f.startswith("__")]


def get_model_file(model_name: str) -> str:
    """
    Return the path to the model file of the selected robot.

    Args:
        model_name: The name of the selected robot.

    Returns:
        The path to the model of the selected robot.
    """
    if model_name not in get_model_names():
        raise RuntimeError(f"Failed to find robot '{model_name}'")

    model_dir = os.path.join(get_models_path(), model_name)

    if not os.path.isdir(model_dir):
        raise FileNotFoundError(model_dir)  # TODO

    models_found = []

    for root, dirs, files in os.walk(model_dir):
        for file in files:
            if file.endswith((".urdf", ".sdf")):
                models_found.append(file)

    if len(models_found) > 1:
        raise RuntimeError(f"Found multiple models in the same folder: {models_found}")
    if len(models_found) == 0:
        return ""

    model_abs_path = os.path.join(model_dir, models_found[0])
    return model_abs_path


def get_world_file(world_name: str) -> str:
    if world_name not in get_world_names():
        raise RuntimeError(f"Failed to find world: '{world_name}'")

    world_name = f"{world_name}.sdf"
    world_path = os.path.join(get_worlds_path(), world_name)

    if not os.path.isfile(world_path):
        raise FileNotFoundError(world_path)

    return world_path


def get_model_string(model_name: str) -> str:
    """
    Return the string containing the selected robot model.

    Args:
        model_name: The name of the selected robot.

    Returns:
        A string containing the selected robot model.
    """

    model_file = get_model_file(model_name=model_name)

    with open(model_file, "r") as f:
        string = f.read()

    return string


def setup_environment() -> None:
    """
    Configure the environment variables.
    """

    models_path = Path(get_models_path())
    worlds_path = Path(get_worlds_path())

    if not models_path.exists():
        raise NotADirectoryError(f"Failed to find path '{models_path}'")

    # Setup the environment to find the models
    if "GZ_SIM_RESOURCE_PATH" in os.environ:
        os.environ["GZ_SIM_RESOURCE_PATH"] += f":{models_path}"
        os.environ["GZ_SIM_RESOURCE_PATH"] += f":{worlds_path}"
    else:
        os.environ["GZ_SIM_RESOURCE_PATH"] = f"{models_path}"
        os.environ["GZ_SIM_RESOURCE_PATH"] += f":{worlds_path}"

    # Models with mesh files
    # Workaround for https://github.com/osrf/sdformat/issues/227
    models_with_mesh = []

    # Setup the environment to find the mesh files
    for model in models_with_mesh:
        model_path = Path(get_models_path()) / model

        if not model_path.exists():
            raise NotADirectoryError(f"Failed to find path '{model_path}'")

        if "GZ_SIM_RESOURCE_PATH" in os.environ:
            os.environ["GZ_SIM_RESOURCE_PATH"] += f":{model_path}"
            os.environ["GZ_SIM_RESOURCE_PATH"] += f":{worlds_path}"
        else:
            os.environ["GZ_SIM_RESOURCE_PATH"] = f"{model_path}"
            os.environ["GZ_SIM_RESOURCE_PATH"] += f":{worlds_path}"


class ResourceType(enum.Enum):
    SDF_FILE = enum.auto()
    SDF_PATH = enum.auto()
    SDF_STRING = enum.auto()

    URDF_FILE = enum.auto()
    URDF_PATH = enum.auto()
    URDF_STRING = enum.auto()


def get_model_resource(
    model_name: str, resource_type: ResourceType = ResourceType.URDF_PATH
) -> Union[str, IO]:
    """
    Return the resource of the selected robot.

    Args:
        model_name: The name of the selected robot.
        resource_type: The type of the desired resource.

    Note:
        If a format conversion is performed, this method creates a temporary file.
        If ``ResourceType.*_FILE`` is used, the file gets automatically deleted when
        it goes out of scope. Instead, if ``ResourceType._*PATH`` is used, the caller
        is responsible to delete it.

    Returns:
        The desired resource of the selected robot.
    """

    stored_model = get_model_file(model_name=model_name)

    if not stored_model.endswith((".urdf", ".sdf")):
        raise RuntimeError(f"Model '{model_name} has no urdf nor sdf resource")

    if stored_model.endswith(".urdf"):
        if resource_type is ResourceType.URDF_PATH:
            return stored_model

        if resource_type is ResourceType.URDF_FILE:
            return open(file=stored_model, mode="r+")

        if resource_type is ResourceType.URDF_STRING:
            with open(file=stored_model, mode="r+") as f:
                return f.read()

        if resource_type in {
            ResourceType.SDF_FILE,
            ResourceType.SDF_PATH,
            ResourceType.SDF_STRING,
        }:
            try:
                from scenario import gazebo as scenario_gazebo
            except ImportError:
                msg = "URDF to SDF conversion requires the 'scenario' package"
                raise RuntimeError(msg)

        if resource_type is ResourceType.SDF_FILE:
            file_name = Path(stored_model).with_suffix("").name
            sdf_file = tempfile.NamedTemporaryFile(
                mode="w+", prefix=file_name, suffix=".sdf"
            )
            sdf_string = get_model_resource(
                model_name=model_name, resource_type=ResourceType.SDF_STRING
            )
            sdf_file.write(sdf_string)
            return sdf_file

        if resource_type is ResourceType.SDF_PATH:
            file_name = Path(stored_model).with_suffix("").name
            fd, sdf_path = tempfile.mkstemp(prefix=file_name, suffix=".sdf", text=True)
            sdf_string = get_model_resource(
                model_name=model_name, resource_type=ResourceType.SDF_STRING
            )
            with open(sdf_path, "w") as f:
                f.write(sdf_string)
            return sdf_path

        if resource_type is ResourceType.SDF_STRING:
            from scenario import gazebo as scenario_gazebo

            return scenario_gazebo.urdffile_to_sdfstring(urdf_file=stored_model)

        raise ValueError(resource_type)

    if stored_model.endswith(".sdf"):
        if resource_type is ResourceType.SDF_PATH:
            return stored_model

        if resource_type in {
            ResourceType.URDF_FILE,
            ResourceType.URDF_PATH,
            ResourceType.URDF_STRING,
        }:
            raise ValueError("SDF to URDF conversion is not supported")

        if resource_type is ResourceType.SDF_STRING:
            with open(file=stored_model, mode="r+") as f:
                return f.read()

        if resource_type is ResourceType.SDF_FILE:
            return open(file=stored_model, mode="r+")

        raise ValueError(resource_type)


# Setup the environment when the package is imported
setup_environment()
