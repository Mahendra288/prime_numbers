from django.core.exceptions import ValidationError
from django.db import models
import enum

class PrimeNumberRequestStatus(enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"

    @classmethod
    def values(cls):
        return cls.__members__.values()


def generate_uuid():
    from uuid import uuid4
    return str(uuid4())

def validate_prime_number_request_status(status):
    if status not in PrimeNumberRequestStatus.values():
        raise ValidationError(f"Invalid status value: {status}")


class PrimeNumberRequests(models.Model):
    request_id = models.CharField(primary_key=True, max_length=255, default=generate_uuid)
    no_of_primes = models.PositiveIntegerField()
    requested_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=255, validators=[validate_prime_number_request_status])
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.TextField(default="{}")

    # Monitoring fields
    celery_req_id = models.CharField(max_length=255, null=True, blank=True)