"""Tests for scenario management and target kinematics."""

import numpy as np
import pytest

from radar_sim.models import Target
from radar_sim.scenario.world import Scenario


class TestDefaultScenario:
    def test_has_five_targets(self) -> None:
        s = Scenario.create_default_scenario()
        assert len(s.targets) == 5

    def test_target_ids_unique(self) -> None:
        s = Scenario.create_default_scenario()
        ids = [t.id for t in s.targets]
        assert len(ids) == len(set(ids))

    def test_time_starts_at_zero(self) -> None:
        s = Scenario.create_default_scenario()
        assert s.time == 0.0


class TestScenarioUpdate:
    def test_update_advances_time(self) -> None:
        s = Scenario.create_default_scenario()
        s.update(1.0)
        np.testing.assert_allclose(s.time, 1.0)

    def test_update_moves_targets(self) -> None:
        s = Scenario()
        t = Target(id="t", x=0, y=0, altitude=0, vx=10, vy=20, rcs=1.0)
        s.add_target(t)
        s.update(5.0)
        assert t.x == 50.0
        assert t.y == 100.0

    def test_multiple_updates_accumulate(self) -> None:
        s = Scenario()
        t = Target(id="t", x=0, y=0, altitude=0, vx=1, vy=0, rcs=1.0)
        s.add_target(t)
        s.update(1.0)
        s.update(1.0)
        np.testing.assert_allclose(t.x, 2.0)
        np.testing.assert_allclose(s.time, 2.0)


class TestCustomScenario:
    def test_add_target(self) -> None:
        s = Scenario()
        s.add_target(Target(id="custom", x=100, y=200, altitude=300, vx=0, vy=0, rcs=5.0))
        assert len(s.targets) == 1
        assert s.targets[0].id == "custom"

    def test_reset(self) -> None:
        s = Scenario()
        s.update(10.0)
        s.reset()
        assert s.time == 0.0
