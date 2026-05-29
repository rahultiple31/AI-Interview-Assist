import platform
import sys


class UnsupportedOperatingSystem(RuntimeError):
    pass


def ensure_supported_windows() -> None:
    if platform.system() != "Windows":
        raise UnsupportedOperatingSystem(
            "AI Interview Assist can only run on Windows 10 or Windows 11."
        )

    version = sys.getwindowsversion()
    if version.major != 10 or version.build < 10240:
        raise UnsupportedOperatingSystem(
            "AI Interview Assist supports Windows 10 and Windows 11 only."
        )

    edition = platform.win32_edition()
    if "Server" in edition:
        raise UnsupportedOperatingSystem(
            "AI Interview Assist supports Windows 10 and Windows 11 client editions only."
        )


def windows_display_name() -> str:
    if platform.system() != "Windows":
        return platform.system()

    version = sys.getwindowsversion()
    if version.build >= 22000:
        return f"Windows 11 build {version.build}"
    return f"Windows 10 build {version.build}"
