from types import ModuleType


def test_import_works():
    import phue

    assert isinstance(phue, ModuleType)
