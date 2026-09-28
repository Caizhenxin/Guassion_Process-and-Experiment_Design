"""一键构建：按顺序渲染 4 幕场景（1080p60），并拼接成单个视频。

用法（在 1_Code/Animation_Manim 目录下）::

    ..\\..\\.venv-manim\\Scripts\\python.exe build_video.py
    ..\\..\\.venv-manim\\Scripts\\python.exe build_video.py --quick   # 480p 快速预览

产物：3_Figures/Animation/GP_Demo_1080p60.mp4（或 _preview480p.mp4）

注意：Manim 会缓存每段动画的分片文件（`media/videos/<模块>/<画质>/partial_movie_files`）。
若某次渲染被中途中断，缓存里会残留不完整的文件，下次渲染会报
`InvalidDataError: Invalid data found when processing input`。
此时删掉对应画质目录下的 `partial_movie_files` 再重跑即可。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import av

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
OUT_DIR = PROJECT_ROOT / "3_Figures" / "Animation"

# 场景顺序即视频播放顺序
SCENES = [
    ("scenes/s0_title.py", "S0Title"),
    ("scenes/s1_design_space.py", "S1DesignSpace"),
    ("scenes/s2_gp_prior.py", "S2GPPrior"),
    ("scenes/s3_gp_posterior.py", "S3GPPosterior"),
    ("scenes/s4_kernel_length_scale.py", "S4KernelLengthScale"),
    ("scenes/s5_higher_dimension.py", "S5HigherDimension"),
    ("scenes/s6_response_surface.py", "S6ResponseSurface"),
    ("scenes/s7_decision.py", "S7Decision"),
    ("scenes/s8_closing.py", "S8Closing"),
]

QUALITY_PRESETS = {
    "high": ("-qh", "1080p60"),
    "quick": ("-ql", "480p15"),
}


def render(python_exe: Path, quality: str) -> list[Path]:
    flag, subdir = QUALITY_PRESETS[quality]
    outputs: list[Path] = []

    for rel_path, scene_name in SCENES:
        module_name = Path(rel_path).stem
        cmd = [
            str(python_exe),
            "-m",
            "manim",
            flag,
            rel_path,
            scene_name,
        ]
        print(f"\n>>> 渲染 {scene_name} ...", flush=True)
        subprocess.run(cmd, cwd=HERE, check=True)

        video = HERE / "media" / "videos" / module_name / subdir / f"{scene_name}.mp4"
        if not video.exists():
            raise FileNotFoundError(f"未找到渲染结果：{video}")
        outputs.append(video)
        print(f"    完成：{video.name}", flush=True)

    return outputs


def concat(video_paths: list[Path], out_path: Path) -> None:
    """把多段视频按顺序拼成一段。

    沿用 Manim 内部 combine_files 的做法：用 concat 分离器做**流拷贝**，
    不重新编码，因此速度快且无画质损失。
    """
    print(f"\n>>> 拼接 {len(video_paths)} 段视频 ...", flush=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    file_list = HERE / "media" / "concat_list.txt"
    file_list.parent.mkdir(parents=True, exist_ok=True)
    with file_list.open("w", encoding="utf-8") as fh:
        for path in video_paths:
            fh.write(f"file '{path.resolve().as_posix()}'\n")

    input_container = av.open(
        str(file_list), options={"safe": "0", "an": "1"}, format="concat"
    )
    input_stream = input_container.streams.video[0]

    output_container = av.open(str(out_path), mode="w")
    output_stream = output_container.add_stream_from_template(template=input_stream)

    for packet in input_container.demux(input_stream):
        # demux 在末尾会产生 dts 为 None 的冲刷包，需要跳过
        if packet.dts is None:
            continue
        # 各段之间 dts 不保证单调递增，交给 libav 重新计算
        packet.dts = None
        packet.stream = output_stream
        output_container.mux(packet)

    input_container.close()
    output_container.close()
    file_list.unlink(missing_ok=True)

    print(f"    输出：{out_path}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--quick",
        action="store_true",
        help="用 480p15 快速渲染，仅用于检查剪辑节奏",
    )
    args = parser.parse_args()

    quality = "quick" if args.quick else "high"
    python_exe = Path(sys.executable)

    videos = render(python_exe, quality)

    if args.quick:
        out_path = OUT_DIR / "GP_Demo_preview480p.mp4"
    else:
        out_path = OUT_DIR / "GP_Demo_1080p60.mp4"

    concat(videos, out_path)

    if quality == "high":
        # 高清版同时留一份在 Animation_Manim 目录下便于快速取用
        shutil.copy2(out_path, HERE / out_path.name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())