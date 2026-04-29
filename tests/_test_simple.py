import pytest


def test_hello():
    assert True


@pytest.mark.parametrize("run", [1, 2, 3])
def test_world(run: int):
    assert True


@pytest.mark.parametrize("run", [1, 2, 3])
def test_world2(run: int):
    if run == 2:
        pytest.fail("Failed on run 2")

    assert True


@pytest.mark.skip
@pytest.mark.parametrize("run", [1, 2, 3])
def test_skip(run):
    pytest.fail("Should be skipped")


@pytest.mark.xfail
def test_xfail():
    assert True


@pytest.fixture
def strange_fixture():
    err = "Strange fixture error"
    raise ValueError(err)


def test_strange(strange_fixture):
    assert True
