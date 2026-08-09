from .models import AuditLog


def get_client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (
        forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    ) or None


def record_audit(
    *, request, action: str, actor=None, target=None, metadata: dict | None = None
) -> AuditLog:
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        target_type=target._meta.label if target else "",
        target_id=str(target.pk) if target else "",
        metadata=metadata or {},
        ip_address=get_client_ip(request),
    )
