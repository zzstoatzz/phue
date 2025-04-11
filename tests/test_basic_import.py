from types import ModuleType


def test_import_works():
    import phue2

    assert isinstance(phue2, ModuleType)
