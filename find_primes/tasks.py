import json

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from opentelemetry import trace

from find_primes.models import PrimeNumberRequests, PrimeNumberRequestStatus
from prime_numbers.celery import TracedTask

tracer = trace.get_tracer(__name__)


def is_prime_number(number):
    has_other_factor = False
    for factor in range(2, number):
        if number % factor == 0:
            has_other_factor = True
            break
    return False if has_other_factor else True

@shared_task(base=TracedTask, bind=True)
def find_n_primes(self, no_of_primes, request_id):

    with transaction.atomic():
        request_obj = PrimeNumberRequests.objects.select_for_update().get(pk=request_id)
        request_obj.status = PrimeNumberRequestStatus.RUNNING.value
        request_obj.save()

    with tracer.start_as_current_span("celery-worker.find-primes-core-logic") as span:
        primes = []
        number, counter = 1, 0
        while True:
            if is_prime_number(number):
                primes.append(number)
                counter += 1
            if counter == no_of_primes:
                break
            number += 1
        result = {"primes": primes}

        span.set_attribute("no_of_primes", no_of_primes)
        span.set_attribute("request", request_id)
        span.add_event("prime numbers calculation completed")

    with transaction.atomic():
        request_obj = PrimeNumberRequests.objects.select_for_update().get(pk=request_id)
        request_obj.status = PrimeNumberRequestStatus.FINISHED.value
        request_obj.completed_at = timezone.now()
        request_obj.result = json.dumps(result)
        request_obj.save()
    return json.dumps(result)