import trimesh

# Функция для расчета инерционных характеристик
def calculate_inertia(file_path, density):
    # Загрузка 3D-модели
    mesh = trimesh.load(file_path)
    
    # Вычисление объема
    volume = mesh.volume
    print(f"Volume: {volume} m^3")

    # Масса = объем * плотность
    mass = volume * density
    print(f"Mass: {mass} kg")

    # Вычисление центра масс
    center_of_mass = mesh.center_mass
    print(f"Center of mass: {center_of_mass}")

    # Тензор инерции относительно центра масс
    inertia_tensor = mesh.moment_inertia
    print(f"Inertia Tensor (relative to center of mass):\n{inertia_tensor}")

    return mass, center_of_mass, inertia_tensor

# Функция для генерации URDF тега с инерциальными характеристиками
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

def generate_sdf_inertia_tag(mass, center_of_mass, inertia_tensor):
    inertia_sdf = f"""
    <inertial>
        <mass>{mass}</mass>
        <pose>{center_of_mass[0]} {center_of_mass[1]} {center_of_mass[2]} 0 0 0</pose>
        <inertia>
            <ixx>{inertia_tensor[0, 0]}</ixx>
            <ixy>{inertia_tensor[0, 1]}</ixy>
            <ixz>{inertia_tensor[0, 2]}</ixz>
            <iyy>{inertia_tensor[1, 1]}</iyy>
            <iyz>{inertia_tensor[1, 2]}</iyz>
            <izz>{inertia_tensor[2, 2]}</izz>
        </inertia>
    </inertial>
    """
    return inertia_sdf

# Пример использования
if __name__ == "__main__":
    file_path = "rbs_assets_library/bishop/meshes/bishop.stl"
    density = 6.0

    mass, center_of_mass, inertia_tensor = calculate_inertia(file_path, density)
    urdf_inertia_tag = generate_urdf_inertia_tag(mass, center_of_mass, inertia_tensor)
    sdf_inertia_tag = generate_sdf_inertia_tag(mass, center_of_mass, inertia_tensor)
    
    print("Generated URDF Inertia Tag:")
    print(urdf_inertia_tag)

    print("Generated SDF Inertia Tag:")
    print(sdf_inertia_tag)
