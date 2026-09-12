"""Short database-only admission and independent paid-work leases."""

from datetime import timedelta
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import OperationalError
from django.db.models import F
from django.utils import timezone

from .errors import ChatError
from .models import LiveUsage, LiveUsageGate


def lock_gate():
    # Called first inside the reservation transaction. UPDATE takes a write lock
    # on SQLite as well as a row lock on PostgreSQL, before any quota reads.
    # Recreate the singleton after a database flush, with the same lock before
    # quota reads. The initial write also avoids SQLite read-to-write upgrades.
    if not LiveUsageGate.objects.filter(pk=1).update(revision=F("revision") + 1):
        LiveUsageGate.objects.get_or_create(pk=1)
        LiveUsageGate.objects.filter(pk=1).update(revision=F("revision") + 1)


def reserve(owner):
    """Caller holds the global gate and owner row until the turn is committed."""
    now = timezone.now()
    if LiveUsage.objects.filter(owner=owner, finished_at__isnull=True, expires_at__gt=now).exists():
        raise ChatError("account_busy", 409)
    today = now.astimezone(dt_timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if (
        LiveUsage.objects.filter(owner=owner, created_at__gt=now - timedelta(hours=1)).count()
        >= settings.FEMAKTIV_LIVE_USER_HOURLY_LIMIT
        or LiveUsage.objects.filter(created_at__gte=today).count()
        >= settings.FEMAKTIV_LIVE_DAILY_LIMIT
    ):
        raise ChatError("rate_limited", 429)
    return LiveUsage.objects.create(
        owner=owner, created_at=now, expires_at=now + timedelta(seconds=60)
    )


def finish(usage_id):
    if usage_id is None:
        return
    try:
        LiveUsage.objects.filter(pk=usage_id, finished_at__isnull=True).update(
            finished_at=timezone.now()
        )
    except OperationalError:
        # A failed lease release must not lead to another provider call. The
        # independent deadline still expires admission even after chat deletion.
        pass
