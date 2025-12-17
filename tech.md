## Celery 
   * why: To execute long running jobs in async when end-user is expecting an immediate response and we have execution time constraints.
   * celery is an asynchronous task queue / job queue
   * Steps
     * Define tasks
     * Push tasks to queue
     * Workers consume and execute tasks
     * Results can be null as well, i.e, optional
   * 3 major components
     1. Producer (where tasks gets created)
     2. Broker - a queue to store tasks untile workers picks these, Redis, RabbitMQ, SQS
     3. Worker - pulls tasks from broker and executes them
   * Retry options
     * @shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
   * Scheduling and Task chaining are another features
   * best practices
     * single unit task - SRP
     * using chains for sequential tasks
     * don't store results in redis - high traffic
     * do not pass objects to task args, because celery serializes the input args
     * setting visibility time out, rate limits

## OTel (OpenTelemetry)
  * Why: No vendor lockin, standard for observability metrics, traces and logs.
  * Observability pillars
    * Traces - request flow and included components
    * Metrics - latency, request count
    * Logs - trace_id, span_id
  * Core OTel building blocks
    * Span - smallest unit of work
    * Trace - collection of spans
    * Context propagation - same trace id passed across services which enables distributed tracing
  * Instrumentation
    * Auto - minimal code, framework level spans
    * Manual - custom business spans, critical logic
  * 
