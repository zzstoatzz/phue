"""Test the Scene class."""

from phue.scene import Scene


def test_scene_creation():
    """Test creating a Scene object with standard parameters."""
    scene = Scene(
        sid="1",
        name="Test Scene",
        lights=["1", "2", "3"],
        group="0",
        type="GroupScene",
    )

    assert scene.scene_id == "1"
    assert scene.name == "Test Scene"
    assert scene.lights == [1, 2, 3]
    assert scene.group == "0"
    assert scene.type == "GroupScene"


def test_scene_with_additional_parameters():
    """Test that the Scene class handles additional parameters from the API."""
    # This test verifies the specific issue with the 'image' parameter
    scene = Scene(
        sid="1",
        name="Test Scene",
        lights=["1", "2", "3"],
        image="/path/to/image.png",  # This parameter was causing issues
        extra_param="value",  # Another future parameter
    )

    assert scene.scene_id == "1"
    assert scene.name == "Test Scene"
    assert scene.lights == [1, 2, 3]
    # We don't assert on image or extra_param because we don't store them
    # The point is just to verify that the constructor doesn't raise an exception


def test_scene_repr():
    """Test the string representation of a Scene object."""
    scene = Scene(
        sid="1",
        name="Test Scene",
        lights=["1", "2", "3"],
    )

    # Check that the repr includes the scene_id, name, and lights
    repr_str = repr(scene)
    assert 'id="1"' in repr_str
    assert 'name="Test Scene"' in repr_str
    assert "lights=[1, 2, 3]" in repr_str


def test_scene_empty_lights():
    """Test that the Scene class handles empty lights list."""
    scene = Scene(
        sid="1",
        name="Test Scene",
    )

    assert scene.scene_id == "1"
    assert scene.name == "Test Scene"
    assert scene.lights == []
