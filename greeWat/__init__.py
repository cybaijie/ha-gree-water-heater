DOMAIN = "greeWat"

async def async_setup_entry(hass, entry):
    # 保证数据结构一定存在
    hass.data.setdefault("greeWat_entities", {})
    await hass.config_entries.async_forward_entry_setups(entry, ["water_heater", "sensor"])
    return True

async def async_unload_entry(hass, entry):
    await hass.config_entries.async_unload_platforms(entry, ["water_heater", "sensor"])
    return True