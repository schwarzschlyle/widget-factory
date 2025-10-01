from app.core.celery_app import celery_app

def main():
    from celery.bin import worker as celery_worker_bin
    # Set the default app for the worker
    celery_app.worker_main([
        "worker",
        "--loglevel=INFO",
        "--queues=default"
    ])

if __name__ == "__main__":
    main()
