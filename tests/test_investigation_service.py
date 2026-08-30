from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.exceptions import ValidationError


def test_create_investigation(ctx):
    inv = ctx.investigation_service.create_investigation("USG Abdomen", "1000")
    assert inv.default_fee == Decimal("1000.00")
    assert inv.is_active


def test_create_investigation_requires_name(ctx):
    with pytest.raises(ValidationError):
        ctx.investigation_service.create_investigation("", "500")


def test_create_investigation_rejects_negative_fee(ctx):
    with pytest.raises(ValidationError):
        ctx.investigation_service.create_investigation("USG Pelvis", "-100")


def test_investigation_activate_deactivate(ctx):
    inv = ctx.investigation_service.create_investigation("USG Pelvis", "800")
    ctx.investigation_service.deactivate(inv.id)
    assert inv.id not in [i.id for i in ctx.investigation_service.list_active()]
    ctx.investigation_service.activate(inv.id)
    assert inv.id in [i.id for i in ctx.investigation_service.list_active()]


def test_changing_default_fee_does_not_change_default_fee_of_get(ctx):
    inv = ctx.investigation_service.create_investigation("USG Abdomen", "1000")
    ctx.investigation_service.update_investigation(inv.id, "USG Abdomen", "1200")
    updated = ctx.investigation_service.get(inv.id)
    assert updated.default_fee == Decimal("1200.00")
