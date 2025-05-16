def test_manifest_exists():
  import os
  assert os.path.exists("custom_components/mappedcover/manifest.json")

async def test_loader(hass):
  from homeassistant.loader import async_get_integration
  integration = await async_get_integration(hass, "mappedcover")
  assert integration is not None
