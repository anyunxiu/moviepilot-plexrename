import argparse
from pathlib import Path

from app.services.namer import Namer
from app.services.recognizer import NameRecognizer


def main() -> int:
    parser = argparse.ArgumentParser(description="识别媒体并输出/应用重命名")
    parser.add_argument("path", help="文件或目录的完整路径")
    parser.add_argument("--apply", action="store_true", help="直接执行重命名")
    args = parser.parse_args()

    target = Path(args.path).expanduser()
    if not target.exists():
        print("路径不存在")
        return 1

    recognizer = NameRecognizer()
    media = recognizer.recognize(target)
    if not media:
        print("未识别到媒体信息")
        return 1

    namer = Namer()
    new_path = namer.render(media, target)
    if not new_path:
        print("未生成重命名路径")
        return 1

    print(f"推荐名称: {new_path.name}")
    print(f"推荐路径: {new_path}")

    if not args.apply:
        return 0

    try:
        target.rename(new_path)
        print(f"已重命名为: {new_path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"重命名失败: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
