1. Celery 
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