"""Configuración común de pytest: los tests nunca descargan portadas reales."""

import pytest

from src.images import shared_image_loader


@pytest.fixture(autouse=True)
def _disable_network_images():
    loader = shared_image_loader()
    loader.enabled = False
    yield
    loader.enabled = True
