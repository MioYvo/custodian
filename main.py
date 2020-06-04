import logging
from datetime import datetime
from os import getenv, remove, popen
import tarfile
from pathlib import Path
import time

import sentry_sdk
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

SENTRY_KEY = getenv("SENTRY_KEY", "")
if SENTRY_KEY:
    sentry_sdk.init(
        dsn=SENTRY_KEY,
    )


DEFAULT_FORMAT = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d] %(message)s"  # noqa: E501
DEFAULT_DATE_FORMAT = "%y%m%d %H:%M:%S"
DEFAULT_COLORS = {
    logging.DEBUG: 4,  # Blue
    logging.INFO: 2,  # Green
    logging.WARNING: 3,  # Yellow
    logging.ERROR: 1,  # Red
}
logging.basicConfig(level=logging.INFO, format=DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

path = Path(getenv('path', '.'))
pattern = getenv('path', '*.sql.gz')
max_files = int(getenv('max_files', 5))
cron_fields = [
    'year',
    'month',
    'week',
    'day',
    'day_of_week',
    'hour',
    'minute',
    'second'
]
cron_trigger_kwargs = {}
for field in cron_fields:
    cron_trigger_kwargs[field] = getenv(field, '*')
trigger = CronTrigger(**cron_trigger_kwargs)

jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}

job_defaults = {
    'coalesce': True,
    'max_instances': 1
}
scheduler = BlockingScheduler(jobstores=jobstores, job_defaults=job_defaults)

MARIA_USER = getenv('MARIA_USER')
if not MARIA_USER:
    MARIA_USER_FILE = getenv('MARIA_USER_FILE')
    if MARIA_USER_FILE:
        with open(MARIA_USER_FILE) as f:
            MARIA_USER = f.read().strip()
assert MARIA_USER

MARIA_PASS = getenv('MARIA_PASS')
if not MARIA_PASS:
    MARIA_PASS_FILE = getenv('MARIA_PASS_FILE')
    if MARIA_PASS_FILE:
        with open(MARIA_PASS_FILE) as f:
            MARIA_PASS = f.read().strip()
assert MARIA_PASS

MARIA_DB = getenv('MARIA_DB')
if not MARIA_DB:
    MARIA_DB_FILE = getenv('MARIA_DB_FILE')
    if MARIA_DB_FILE:
        with open(MARIA_DB_FILE) as f:
            MARIA_DB = f.read().strip()
assert MARIA_DB

MARIA_HOST = getenv('MARIA_HOST', '127.0.0.1')
MARIA_PORT = int(getenv('MARIA_PORT', '3306'))

# source_dir = Path('/data')
source_dir = Path('./backup/')

access_key_id = getenv('access_key_id')
secret_access_key = getenv('secret_access_key')
endpoint = getenv('endpoint')
provider = getenv('provider', 'Alibaba')
_type = getenv('type', 's3')
name = getenv('name', 'oss')
run_once_immediately = bool(int(getenv('run_once_immediately', 0)))
OSS_DEST = getenv('OSS_DEST', f'{name}:wachmen-monitor-backup')
TABLES = getenv('TABLES')


def dump():
    # sql = [
    #     'mysqldump', '--force', '--single-transaction', '--opt', f'--host={MARIA_HOST}', f'--port={MARIA_PORT}',
    #     f'--user={MARIA_USER}', f'-p{MARIA_PASS}',
    #     '--skip-extended-insert', '--databases', f'{MARIA_DB}',
    #     '|', 'gzip -9',
    #     '>', f'{(source_dir / datetime.utcnow().replace(microsecond=0).isoformat()).absolute()}.sql.gz'
    # ]
    file_name = f"{(source_dir / datetime.utcnow().replace(microsecond=0).isoformat()).absolute()}.sql.gz"
    logging.info(f'dumping {file_name}')
    commd = '/usr/bin/mysqldump ' \
            '--force ' \
            '--single-transaction ' \
            '--opt ' \
            f'--host={MARIA_HOST} ' \
            f'--port={MARIA_PORT} ' \
            f'--user={MARIA_USER} ' \
            f'-p{MARIA_PASS} ' \
            '--skip-extended-insert ' \
            f'--databases {MARIA_DB} {f"--tables {TABLES}" if TABLES else ""} | gzip -9 > ' \
            f'"{file_name}"'
    popen(commd)


def tar_files(file_path: Path) -> Path:
    tgz_file_p = file_path.parent / (file_path.name + '.tar.gz')
    with tarfile.open(tgz_file_p, "w:gz") as tar:
        # 创建压缩包
        tar.add(file_path, arcname=file_path.name)
    return tgz_file_p


def sync(source: Path = source_dir, dest: str = OSS_DEST):
    import rclone
    with open('rclone.conf') as cf:
        cfg = cf.read()
        cfg = cfg.format(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            endpoint=endpoint,
            provider=provider,
            name=name,
            type=_type
        )
    logging.info(f'syncing {source.absolute()} {dest}')
    rst = rclone.with_config(cfg).sync(source=str(source.absolute()), dest=dest)
    logging.info(rst)


def keep_files():
    remove_files = set(source_dir.iterdir()) - set(source_dir.glob(pattern=pattern))
    for i in remove_files:
        i: Path
        logging.info(f"removing {i}")
        remove(str(i.absolute()))

    files = sorted(list(source_dir.iterdir()))
    if len(files) > max_files:
        for rf in files[:len(files)-max_files]:
            logging.info(f"removing {rf}")
            # noinspection PyTypeChecker
            remove(rf)


def main():
    if not (source_dir.exists() or source_dir.is_dir()):
        source_dir.mkdir(parents=True, exist_ok=True)
    try:
        dump()
        time.sleep(1)
        keep_files()
        time.sleep(1)
        sync()
    except Exception as e:
        logging.error(e)
        pass


if __name__ == '__main__':
    if run_once_immediately:
        main()
    job = scheduler.add_job(func=main, trigger=trigger, name='rclone to oss', id='1', replace_existing=True)
    # job.modify(next_run_time=datetime.now(scheduler.timezone) + timedelta(seconds=10))

    for job in scheduler.get_jobs():
        logging.info(f"{job.name}: {job.trigger}")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
