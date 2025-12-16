import asyncio
from homeassistant.components.sensor import SensorEntity

class GreeWaterHeaterSensor(SensorEntity):
    def __init__(self, water_heater, sensor_type, name, unit):
        self._water_heater = water_heater
        self._sensor_type = sensor_type
        mac = getattr(water_heater, "_mac_addr", "")
        mac_str = "".join([c for c in mac if c.isalnum()])
        self._attr_unique_id = f"gree_{mac_str}_re_shui_qi_{sensor_type.lower()}"
        self._attr_name = name  # 直接用中文名
        self._attr_native_unit_of_measurement = unit

    @property
    def state(self):
        value = self._water_heater._acOptions.get(self._sensor_type)
        if value is not None:
            return (value - 100)
        return None

    @property
    def available(self):
        return self._water_heater.available

    @property
    def device_info(self):
        return self._water_heater.device_info

#热水百分比
class GreeWaterHotPercentSensor(SensorEntity):
    def __init__(self, water_heater):
        self._water_heater = water_heater
        mac = getattr(water_heater, "_mac_addr", "")
        mac_str = "".join([c for c in mac if c.isalnum()])
        self._attr_unique_id = f"gree_{mac_str}_re_shui_qi_hot_percent"
        self._attr_name = "实际热水占比"
        self._attr_native_unit_of_measurement = "%"
        self._attr_device_class = "humidity"  # 或 "percentage"
        self._attr_state_class = "measurement"

    @property
    def state(self):
        try:
            tH = self._water_heater._acOptions.get('WsenTmpH')
            tM = self._water_heater._acOptions.get('WsenTmpM')
            tL = self._water_heater._acOptions.get('WsenTmpL')
            set_tmp = self._water_heater._acOptions.get('WsetTmp')  # 设定温度（原始*10）
            if None in (tH, tM, tL, set_tmp):
                return None

            # 设备原始温度有偏移
            tH -= 100
            tM -= 100
            tL -= 100
            set_temp = set_tmp / 10  # 设定温度

            # 判断线
            threshold = 41
            if set_temp < 41:
                threshold = set_temp

            tank_temps = [
                tH,
                (tH + tM) / 2,
                tM,
                (tM + tL) / 2,
                tL
            ]
            hot_count = sum(1 for t in tank_temps if t >= threshold)
            percent = hot_count * 20
            return percent
        except Exception as e:
            import logging; logging.error(f"计算热水占比出错: {e}")
            return None

    @property
    def available(self):
        return self._water_heater.available

    @property
    def device_info(self):
        return self._water_heater.device_info
        return self._water_heater.device_info
        
    
    
#目标热水占比
class GreeWaterTargetHotPercentSensor(SensorEntity):
    """目标热水占比传感器"""
    def __init__(self, water_heater):
        self._water_heater = water_heater
        mac = getattr(water_heater, "_mac_addr", "")
        mac_str = "".join([c for c in mac if c.isalnum()])
        self._attr_unique_id = f"gree_{mac_str}_re_shui_qi_target_hot_percent"
        self._attr_name = "目标热水占比"
        self._attr_native_unit_of_measurement = "%"
        self._attr_device_class = "humidity"  # 或 "percentage"

    @property
    def state(self):
        try:
            tH = self._water_heater._acOptions.get('WsenTmpH')
            tM = self._water_heater._acOptions.get('WsenTmpM')
            tL = self._water_heater._acOptions.get('WsenTmpL')
            set_tmp = self._water_heater._acOptions.get('WsetTmp')  # 设定温度（原始*10）
            if None in (tH, tM, tL, set_tmp):
                return None

            # 设备原始温度有偏移
            tH -= 100
            tM -= 100
            tL -= 100
            set_temp = set_tmp / 10  # 设定温度

            # 水箱温度
            tank_temps = [
                tH,
                (tH + tM) / 2,
                tM,
                (tM + tL) / 2,
                tL
            ]
            total_capacity = 200
            tank_capacity = total_capacity / 5

            hot_water = 0.0

            if set_temp <= 41:
                # 目标温度≤41时，达标的水箱直接算满，未达为0
                for temp in tank_temps:
                    if temp >= set_temp:
                        hot_water += tank_capacity
                percent = int(round(hot_water / total_capacity * 100))
                return percent
            else:
                # 目标温度>41时，采用线性权重
                for temp in tank_temps:
                    if temp < 41:
                        continue  # 低于41度不计入
                    if temp >= set_temp:
                        weight = 1
                    else:
                        weight = (temp - 41) / (set_temp - 41)
                        weight = min(max(weight, 0), 1)
                    hot_water += tank_capacity * weight
                percent = int(round(hot_water / total_capacity * 100))
                return percent

        except Exception as e:
            import logging; logging.error(f"计算目标热水占比出错: {e}")
            return None

    @property
    def available(self):
        return self._water_heater.available

    @property
    def device_info(self):
        return self._water_heater.device_info
        
        
async def async_setup_entry(hass, entry, async_add_entities):
    # 不要等待太久，最多等2秒
    for _ in range(10):
        water_heater = hass.data["greeWat_entities"].get(entry.entry_id)
        if water_heater:
            break
        await asyncio.sleep(0.2)
    else:
        import logging
        logging.error(f"greeWat sensor async_setup_entry error: water_heater entity not found for entry_id {entry.entry_id}")
        return

    sensors = [
        GreeWaterHotPercentSensor(water_heater),
        GreeWaterTargetHotPercentSensor(water_heater),
        GreeWaterHeaterSensor(water_heater, 'WsenTmpH', '热水器高温值', '°C'),
        GreeWaterHeaterSensor(water_heater, 'WsenTmpM', '热水器中温值', '°C'),
        GreeWaterHeaterSensor(water_heater, 'WsenTmpL', '热水器低温值', '°C'),
    ]
    async_add_entities(sensors, True)

async def async_unload_entry(hass, entry):
    await hass.config_entries.async_unload_platforms(entry, ["water_heater", "sensor"])
    hass.data.get("greeWat_entities", {}).pop(entry.entry_id, None)
    return True