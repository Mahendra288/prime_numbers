import json

# Create your views here.
from django.http import HttpResponse

from find_primes.models import PrimeNumberRequests, PrimeNumberRequestStatus
import logging
from opentelemetry import trace
# Get a tracer for this module
tracer = trace.get_tracer(__name__)

def find_primes(request):
    from find_primes.tasks import find_n_primes

    no_of_primes = int(request.GET['no_of_primes'])

    # find primes in background
    prime_number_request = PrimeNumberRequests.objects.create(
        no_of_primes=no_of_primes,
        status=PrimeNumberRequestStatus.QUEUED.value
    )

    with tracer.start_as_current_span("django-server.find-primes-api") as span:
        async_request = find_n_primes.delay(
            no_of_primes=no_of_primes,
            request_id=prime_number_request.pk
        )
        prime_number_request.celery_req_id = async_request.id
        prime_number_request.save()

        span.set_attribute("celery_req_id", async_request.id)
        span.set_attribute("prime_number_request_id", prime_number_request.pk)
        span.add_event(f"pushed-to-celery-queue with celery req id {async_request.id}")

    response = {
        "request_id": prime_number_request.pk
    }
    logging.info(f"API Response: {json.dumps(response)}")
    return HttpResponse(json.dumps(response), content_type="application/json")

def get_primes_req_status(request):
    request_id = request.GET['request_id']

    # find primes in background
    prime_number_request = PrimeNumberRequests.objects.get(pk=request_id)

    result_dict = json.loads(prime_number_request.result) if prime_number_request.result else {}
    primes = result_dict.get('primes', [])
    response = {
        "request_id": prime_number_request.pk,
        "status": prime_number_request.status,
        "result": primes
    }
    logging.info(f"API Response: {response}")
    return HttpResponse(json.dumps(response), content_type="application/json")
