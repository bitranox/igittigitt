from typing import List

collect_ignore: List[str] = []


def pytest_cmdline_preparse(args: List[str]) -> None:
    """
    # run tests on multiple processes if pytest-xdist plugin is available
    # unfortunately it does not work with codecov
    import sys
    if "xdist" in sys.modules:  # pytest-xdist plugin
        import multiprocessing

        num = int(max(multiprocessing.cpu_count() / 2, 1))
        args[:] = ["-n", str(num)] + args
    """

    additional_pytest_args: List[str] = []
    args[:] = list(set(args + additional_pytest_args))
