from weschatbot.utils.db import provide_session


@provide_session
def create_job_run(session=None):
    pass


@provide_session
def execute_job_runs(session=None):
    pass


@provide_session
def schedule(session=None):
    while True:
        create_job_run()
        execute_job_runs()
