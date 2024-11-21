import subprocess
import trimesh
import os
from rbs_assets_library import get_models_path, get_model_names, get_model_file


def get_git_user_info():
    """
    Retrieve user name and email from Git configuration.
    If unavailable, prompt the user to input them manually.
    """
    try:
        name = subprocess.check_output(
            ["git", "config", "--global", "user.name"], text=True
        ).strip()
    except subprocess.CalledProcessError:
        name = ""

    try:
        email = subprocess.check_output(
            ["git", "config", "--global", "user.email"], text=True
        ).strip()
    except subprocess.CalledProcessError:
        email = ""

    if not name:
        name = input("Git user name not found. Please enter your name: ").strip()
    if not email:
        email = input("Git user email not found. Please enter your email: ").strip()

    return name, email


def calculate_inertia(file_path, density):
    mesh = trimesh.load(file_path)
    
    volume = mesh.volume
    print(f"Volume: {volume} m^3")

    mass = volume * density
    print(f"Mass: {mass} kg")

    center_of_mass = mesh.center_mass
    print(f"Center of mass: {center_of_mass}")

    inertia_tensor = mesh.moment_inertia
    print(f"Inertia Tensor (relative to center of mass):\n{inertia_tensor}")

    return mass, center_of_mass, inertia_tensor


def generate_urdf_inertia_tag(mass, center_of_mass, inertia_tensor):
    inertia_urdf = f"""
    <inertial>
        <mass value="{mass}"/>
        <origin xyz="{center_of_mass[0]} {center_of_mass[1]} {center_of_mass[2]}"/>
        <inertia ixx="{inertia_tensor[0, 0]}" ixy="{inertia_tensor[0, 1]}" ixz="{inertia_tensor[0, 2]}"
                iyy="{inertia_tensor[1, 1]}" iyz="{inertia_tensor[1, 2]}" izz="{inertia_tensor[2, 2]}"/>
    </inertial>
    """
    return inertia_urdf


def generate_model_config(
    model_name,
    author_name,
    author_email,
    version=0.0,
    description="",
    sdf_version: float = 1.7,
):
    model_config = f"""<?xml version="1.0"?>
<model>
  <name>{model_name}</name>
  <version>{version}</version>
  <sdf version="{sdf_version}">model.urdf</sdf>
  <author>
    <name>{author_name}</name>
    <email>{author_email}</email>
  </author>
  <description>
    {description}
  </description>
</model>
"""
    return model_config


def generate_urdf(
    model_name,
    mass,
    center_of_mass,
    inertia_tensor,
    visual_mesh_filepath: str,
    collision_mesh_filepath: str,
):
    model_urdf = f"""<?xml version="1.0"?>
<robot name="{model_name}">
  <link name="body">
    {generate_urdf_inertia_tag(mass, center_of_mass, inertia_tensor)}
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <mesh filename="{visual_mesh_filepath}" scale="1.0 1.0 1.0"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <mesh filename="{collision_mesh_filepath}" scale="1.0 1.0 1.0"/>
      </geometry>
    </collision>
  </link>
</robot>
"""
    return model_urdf


# File extensions for meshes
mesh_extensions = {
    "visual": [".dae"],
    "collision": [".stl", ".obj"]
}


def get_user_model_choice(models):
    print("\nAvailable models:")
    for idx, model in enumerate(models, 1):
        print(f"{idx}. {model}")
    
    # Get the user's input
    user_input = input("\nSelect models (comma separated or range of numbers, e.g., 1, 3, 5-7): ").strip()

    selected_models = set()
    try:
        # Parse input
        for part in user_input.split(","):
            part = part.strip()
            if "-" in part:  # If the part is a range (e.g., 3-5)
                start, end = map(int, part.split("-"))
                selected_models.update(range(start, end + 1))
            else:  # If the part is a single number (e.g., 1, 3)
                selected_models.add(int(part))
    except ValueError:
        print("Invalid input. Please provide valid model numbers.")
        return []

    # Ensure the selection is within the correct range
    selected_models = {model for model in selected_models if 1 <= model <= len(models)}
    
    return [models[i - 1] for i in selected_models]


if __name__ == "__main__":
    density = 1050.0
    author_name, author_email = get_git_user_info()
    models_path = get_models_path()
    model_names = get_model_names()

    # Identify models without a main file
    models_without_main_file = [
        model for model in model_names if get_model_file(model) == ""
    ]

    # Get user selection of models
    selected_models = get_user_model_choice(model_names)

    if not selected_models:
        print("No models selected, exiting.")
    else:
        for model in selected_models:
            model_folder_path = os.path.join(models_path, model)
            mesh = {"name": model, "visual": None, "collision": None}
            collision_candidates = []

            # Locate mesh files
            for root, _, files in os.walk(model_folder_path):
                for file in files:
                    file_path = os.path.join(root, file)

                    # Match against visual extensions
                    if any(file.endswith(ext) for ext in mesh_extensions["visual"]):
                        mesh["visual"] = file_path

                    # Collect collision candidates
                    if any(file.endswith(ext) for ext in mesh_extensions["collision"]):
                        collision_candidates.append((file_path, file))

            # Prioritize collision meshes by extension: .stl > .obj
            for ext in mesh_extensions["collision"]:
                for path, filename in collision_candidates:
                    if filename.endswith(ext):
                        mesh["collision"] = path
                        break
                if mesh["collision"]:
                    break

            if not mesh["visual"] or not mesh["collision"]:
                print(f"Skipping {model}: visual or collision mesh not found.")
                continue

            # Calculate inertia
            mass, center_of_mass, inertia_tensor = calculate_inertia(
                mesh["collision"], density
            )

            # Create model.config
            model_config = generate_model_config(
                model_name=model,
                author_name=author_name,
                author_email=author_email,
                version=1.0,
                description="Autogenerated model."
            )

            config_path = os.path.join(model_folder_path, "model.config")
            with open(config_path, "w") as f:
                f.write(model_config)

            # Create model.urdf
            model_urdf = generate_urdf(
                model_name=model,
                mass=mass,
                center_of_mass=center_of_mass,
                inertia_tensor=inertia_tensor,
                visual_mesh_filepath=os.path.relpath(mesh["visual"], model_folder_path),
                collision_mesh_filepath=os.path.relpath(mesh["collision"], model_folder_path),
            )

            urdf_path = os.path.join(model_folder_path, "model.urdf")
            with open(urdf_path, "w") as f:
                f.write(model_urdf)

            print(f"Generated files for model {model}:")
            print(f"  - model.config: {config_path}")
            print(f"  - model.urdf: {urdf_path}")
