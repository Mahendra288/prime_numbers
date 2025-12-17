1. start your redis server - redis-server
2. up your celery worker - celery -A project_name worker -l info
3. run your django server and fire the api calls