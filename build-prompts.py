from pathlib import Path


def build_prompts(root: Path) -> None:
    skills = root / "skills"
    prompts = root / "prompts"
    prompts.mkdir(exist_ok=True)
    for skill in skills.glob("*/SKILL.md"):
        name = skill.parent.name
        out = prompts / f"{name}.prompt.md"
        out.write_text(skill.read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    build_prompts(Path(__file__).resolve().parent)
