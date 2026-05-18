import importlib.util
import sys
import types
from pathlib import Path


def load_batch_print_module(monkeypatch):
    fake_dotenv = types.SimpleNamespace(load_dotenv=lambda *_args, **_kwargs: None)
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)

    module_path = Path(__file__).with_name("batch_print_v2.py")
    spec = importlib.util.spec_from_file_location("batch_print_v2_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeHwpSet:
    def SetItem(self, _name, _value):
        pass


class FakeHwpAction:
    def CreateSet(self):
        return FakeHwpSet()

    def GetDefault(self, _hset):
        pass

    def Execute(self, _hset):
        return True


class FakeHwp:
    def Open(self, *_args):
        pass

    def CreateAction(self, _name):
        return FakeHwpAction()

    def Clear(self, _mode):
        pass


def test_print_hwpx_restores_auto_default_source_zero(monkeypatch):
    module = load_batch_print_module(monkeypatch)
    monkeypatch.setattr(module.time, "sleep", lambda *_args: None)

    set_values = []

    class DevMode:
        DefaultSource = 0

    devmode = DevMode()
    fake_win32print = types.SimpleNamespace(
        OpenPrinter=lambda _printer: object(),
        GetPrinter=lambda _handle, _level: {"pDevMode": devmode},
        SetPrinter=lambda _handle, _level, _info, _command: set_values.append(devmode.DefaultSource),
        ClosePrinter=lambda _handle: None,
    )
    monkeypatch.setitem(sys.modules, "win32print", fake_win32print)

    assert module.print_hwpx(FakeHwp(), "notice.hwpx", copies=1, printer="Printer", paper_source=3)
    assert set_values == [3, 0]


def test_restore_printer_default_after_run_sets_configured_tray(monkeypatch):
    module = load_batch_print_module(monkeypatch)
    module.POST_PRINT_TRAY = 15

    set_values = []

    class DevMode:
        DefaultSource = 3

    devmode = DevMode()
    fake_win32print = types.SimpleNamespace(
        OpenPrinter=lambda _printer: object(),
        GetPrinter=lambda _handle, _level: {"pDevMode": devmode},
        SetPrinter=lambda _handle, _level, _info, _command: set_values.append(devmode.DefaultSource),
        ClosePrinter=lambda _handle: None,
    )
    monkeypatch.setitem(sys.modules, "win32print", fake_win32print)

    assert module._restore_printer_default_after_run("Printer")
    assert set_values == [15]
