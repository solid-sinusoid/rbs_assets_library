from  pathlib import Path
import numpy as np
import pyrender
import trimesh
import os
from PIL import Image
import os.path as osp
from tqdm import tqdm
import argparse
from trimesh_utils import as_mesh
from trimesh_utils import get_obj_diameter
os.environ["DISPLAY"] = ":1"
os.environ["PYOPENGL_PLATFORM"] = "egl"


def render(
    mesh,
    output_dir,
    obj_poses,
    img_size,
    intrinsic,
    light_itensity=0.6,
    is_tless=False,
    re_center_transform=np.eye(4),
):
    # camera pose is fixed as np.eye(4)
    cam_pose = np.eye(4)
    # convert openCV camera
    cam_pose[1, 1] = -1
    cam_pose[2, 2] = -1
    # create scene config
    ambient_light = np.array([0.02, 0.02, 0.02, 1.0])  # np.array([1.0, 1.0, 1.0, 1.0])
    if light_itensity != 0.6:
        ambient_light = np.array([1.0, 1.0, 1.0, 1.0])
    scene = pyrender.Scene(
        bg_color=np.array([0.0, 0.0, 0.0, 0.0]), ambient_light=ambient_light
    )
    light = pyrender.SpotLight(
        color=np.ones(3),
        intensity=light_itensity,
        innerConeAngle=np.pi / 16.0,
        outerConeAngle=np.pi / 6.0,
    )
    scene.add(light, pose=cam_pose)

    # create camera and render engine
    fx, fy, cx, cy = intrinsic[0][0], intrinsic[1][1], intrinsic[0][2], intrinsic[1][2]
    camera = pyrender.IntrinsicsCamera(
        fx=fx, fy=fy, cx=cx, cy=cy, znear=0.05, zfar=100000
    )
    scene.add(camera, pose=cam_pose)
    render_engine = pyrender.OffscreenRenderer(img_size[1], img_size[0])
    cad_node = scene.add(mesh, pose=np.eye(4), name="cad")

    for idx_frame in range(obj_poses.shape[0]):
        scene.set_pose(cad_node, obj_poses[idx_frame] @ re_center_transform)
        rgb, depth = render_engine.render(scene, pyrender.constants.RenderFlags.RGBA)
        rgb = Image.fromarray(np.uint8(rgb))
        rgb.save(osp.join(output_dir, f"{idx_frame:06d}.png"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cad_path", nargs="?", help="Path to the model file")
    parser.add_argument("obj_pose", nargs="?", help="Path to the model file")
    parser.add_argument(
        "output_dir", nargs="?", help="Path to where the final files will be saved"
    )
    parser.add_argument("gpus_devices", nargs="?", help="GPU devices")
    parser.add_argument("disable_output", nargs="?", help="Disable output of blender")
    parser.add_argument("light_itensity", nargs="?", type=float, default=1.0, help="Light itensity")
    parser.add_argument("radius", nargs="?", type=float, default=0.4, help="Distance from camera to object")
    parser.add_argument("model_name", nargs="?", type=str)
    args = parser.parse_args()
    print(args)

    from rbs_assets_library import get_assets_path, get_model_meshes_info, get_model_names

    if args.model_name not in get_model_names():
        raise argparse.ArgumentError(args.model_name, f"Model name is invalid, available model names is: {get_model_names()}")

    output_dir = get_assets_path()
    output_dir = Path(output_dir)
    output_dir = output_dir / "cnos_data" / args.model_name
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    current_file = Path(__file__)
    obj_pose = current_file.parent / "predefined_poses" / "obj_poses_level0.npy"
    poses = np.load(obj_pose)
    # we can increase high energy for lightning but it's simpler to change just scale of the object to meter
    # poses[:, :3, :3] = poses[:, :3, :3] / 1000.0
    poses[:, :3, 3] = poses[:, :3, 3] / 1000.0
    if args.radius != 1:
        poses[:, :3, 3] = poses[:, :3, 3] * args.radius
    intrinsic = np.array(
        [[572.4114, 0.0, 325.2611], [0.0, 573.57043, 242.04899], [0.0, 0.0, 1.0]]
    )
    img_size = [480, 640]
    is_tless = False

    mesh_data = get_model_meshes_info(args.model_name)

    cad_path = mesh_data["collision"]

    # load mesh to meter
    mesh = trimesh.load_mesh(cad_path)

    # re-center objects at the origin
    re_center_transform = np.eye(4)
    re_center_transform[:3, 3] = -mesh.bounding_box.centroid
    print(f"Object center at {mesh.bounding_box.centroid}")

    diameter = get_obj_diameter(mesh)
    if diameter > 100: # object is in mm
        mesh.apply_scale(0.001)

    mesh = pyrender.Mesh.from_trimesh(as_mesh(mesh))
    os.makedirs(output_dir, exist_ok=True)
    render(
        output_dir=output_dir,
        mesh=mesh,
        obj_poses=poses,
        intrinsic=intrinsic,
        img_size=(480, 640),
        light_itensity=args.light_itensity,
        re_center_transform=re_center_transform,
    )
