"""Build an EB source ZIP with manage.py at the root and no local secrets."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent.parent


def build_package():
    output = ROOT / "dist" / "swe1-app.zip"
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for filename in ("manage.py", "requirements.txt", "Procfile"):
            archive.write(ROOT / filename, filename)
        for folder in ("mysite", "polls", ".ebextensions"):
            for path in sorted((ROOT / folder).rglob("*")):
                if (
                    path.is_file()
                    and "__pycache__" not in path.parts
                    and path.suffix != ".pyc"
                ):
                    archive.write(path, path.relative_to(ROOT).as_posix())
    with ZipFile(output) as archive:
        assert "manage.py" in archive.namelist()
        assert ".ebextensions/django.config" in archive.namelist()
        assert not any(
            name.endswith((".sqlite3", ".pem", ".key", ".pyc"))
            for name in archive.namelist()
        )
    return output


if __name__ == "__main__":
    print(build_package())
