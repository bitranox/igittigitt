# STDLIB
import platform
import signal
import sys
from typing import Optional
from types import FrameType

# EXT
import click

# OWN
import cli_exit_tools

# PROJ
try:
    from . import __init__conf__
    from . import igittigitt
except (ImportError, ModuleNotFoundError):  # pragma: no cover
    # imports for doctest
    import __init__conf__  # type: ignore  # pragma: no cover
    import igittigitt  # type: ignore  # pragma: no cover

# CONSTANTS
CLICK_CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

is_platform_windows = platform.system().lower() == "windows"
is_platform_linux = platform.system().lower() == "linux"
is_platform_darwin = platform.system().lower() == "darwin"
is_platform_posix = not is_platform_windows


class SigIntError(Exception):
    """wird bei Signal SigInt ausgelöst"""
    pass


class SigTermError(Exception):
    """wird bei Signal SigTerm ausgelöst"""
    pass


if is_platform_windows:
    """import win32 api on windows systems"""
    try:
        import win32api  # type: ignore # noqa
    except ModuleNotFoundError:  # for install_python_libs_python3.py - at that time pywin32 (win32api) might not be installed
        pass


def _set_signal_handlers() -> None:
    """
    setzt die signal handler so, das entsprechende Exceptions geraised werden.
    Dies dient dazu ein sauberes Handling für Cleanup in den Applikationen
    zu gewährleisten
    """
    # sigterm handler setzen
    if is_platform_linux:
        signal.signal(signal.SIGTERM, _sigterm_handler)
    elif is_platform_windows:
        try:
            win32api.SetConsoleCtrlHandler(_sigterm_handler, True)
        except NameError:  # for install_python_libs_python3.py - at that time pywin32 (win32api) might not be installed
            pass

    # sigint handler setzen
    signal.signal(signal.SIGINT, _sigint_handler)


def _sigint_handler(_signo: int, _stack_frame: Optional[FrameType]) -> None:
    raise SigIntError


def _sigterm_handler(_signo: int, _stack_frame: Optional[FrameType]) -> None:
    raise SigTermError


def info() -> None:
    """
    >>> info()
    Info for ...

    """
    __init__conf__.print_info()


@click.group(help=__init__conf__.title, context_settings=CLICK_CONTEXT_SETTINGS)    # type: ignore
@click.version_option(
    version=__init__conf__.version,
    prog_name=__init__conf__.shell_command,
    message=f"{__init__conf__.shell_command} version {__init__conf__.version}",
)
@click.option(
    "--traceback/--no-traceback",
    is_flag=True,
    type=bool,
    default=None,
    help="return traceback information on cli",
)
def cli_main(traceback: Optional[bool] = None) -> None:
    if traceback is not None:
        cli_exit_tools.config.traceback = traceback


@cli_main.command("info", context_settings=CLICK_CONTEXT_SETTINGS)  # type: ignore
def cli_info() -> None:
    """get program information"""
    info()


# entry point if main
if __name__ == "__main__":
    try:
        _set_signal_handlers()
        cli_main()  # type: ignore
    except Exception as exc:
        cli_exit_tools.print_exception_message()
        sys.exit(cli_exit_tools.get_system_exit_code(exc))
    finally:
        cli_exit_tools.flush_streams()
