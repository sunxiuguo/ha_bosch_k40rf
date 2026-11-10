"""Device routing regressions; no gateway or running Home Assistant is needed."""

from types import SimpleNamespace

import pytest

from custom_components.bosch_k40rf.binary_sensor import BoschK40BinarySensor
from custom_components.bosch_k40rf.const import DOMAIN
from custom_components.bosch_k40rf.models import (
    BoschK40BinarySensorEntityDescription,
    BoschK40SensorEntityDescription,
)
from custom_components.bosch_k40rf.sensor import BoschK40Sensor


@pytest.fixture(params=[
    (BoschK40Sensor, BoschK40SensorEntityDescription),
    (BoschK40BinarySensor, BoschK40BinarySensorEntityDescription),
], ids=["sensor", "binary_sensor"])
def entity_factory(request):
    entity_type, description_type = request.param

    def make(sub_id, *, hybrid=False, resource="/signals/SC.DampOutdTemp", appliance=True):
        def module(*, hw_ident=None, is_appliance=False):
            if is_appliance and appliance:
                return {"ProductName": "Synthetic heat pump", "Ver": "1.0"}
            if hw_ident == "MC":
                return {"ModuleHwIdentStr": "MC110", "Ver": "2.0"}
            return None

        coordinator = SimpleNamespace(
            hass=SimpleNamespace(config=SimpleNamespace(language="en")),
            gateway_info={}, gateway_device_id=None,
            is_hybrid_system=hybrid, get_basic_info_module=module,
        )
        description = description_type(
            key="synthetic", resource_id=resource,
            target_device_type="heat_source", device_sub_id=sub_id,
        )
        return entity_type(coordinator, SimpleNamespace(data={}), description, "test-gateway")

    return make


@pytest.mark.parametrize("sub_id", [None, "hs1", "hs2", "hybman", "kessel"])
def test_single_heat_source_has_primary_device(entity_factory, sub_id):
    entity = entity_factory(sub_id)
    info = entity.device_info
    assert info["identifiers"] == {(DOMAIN, "test-gateway_heat_source")}
    assert info["name"] == "Synthetic heat pump"
    assert info["via_device"] == (DOMAIN, "test-gateway")
    assert entity.device_info == info


@pytest.mark.parametrize("sub_id", ["hs3", "hs4", "hs5", "hs6"])
def test_single_system_keeps_cascade_devices(entity_factory, sub_id):
    info = entity_factory(sub_id).device_info
    assert info["identifiers"] == {(DOMAIN, f"test-gateway_heat_source_{sub_id}")}


@pytest.mark.parametrize("sub_id", [None, "hs1", "hybman", "kessel"])
def test_single_boiler_keeps_module_metadata(entity_factory, sub_id):
    info = entity_factory(sub_id, appliance=False).device_info
    assert info["identifiers"] == {(DOMAIN, "test-gateway_heat_source")}
    assert info["name"] == "Boiler (MC110)"
    assert info["sw_version"] == "2.0"


@pytest.mark.parametrize(("sub_id", "resource", "suffix"), [
    ("hs1", "/heatSources/hs1/actualPower", "kessel"),
    ("kessel", "/heatSources/actualPower", "kessel"),
    (None, "/heatSources/flameStatus", "kessel"),
    ("hybman", "/heatSources/fallbackOperation", "hybman"),
    (None, "/heatSources/fallbackOperation", "hybman"),
    ("hs2", "/heatSources/hs2/actualPower", None),
    (None, "/signals/ODUMONITOR.synthetic", None),
])
def test_hybrid_routing_is_unchanged(entity_factory, sub_id, resource, suffix):
    info = entity_factory(sub_id, hybrid=True, resource=resource).device_info
    expected = "test-gateway_heat_source" + (f"_{suffix}" if suffix else "")
    assert info["identifiers"] == {(DOMAIN, expected)}
