import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import shlex
import shutil

import docker


IMAGE_TAG = 'tgbot-py310'
_executor = ThreadPoolExecutor(max_workers=1)


async def run_code(code: str, work_dir: str, timeout: float) -> tuple[str, dict]:
    return await asyncio.get_running_loop().run_in_executor(
        _executor,
        sync_run_code,
        code, work_dir, timeout,
    )


def sync_run_code(code: str, work_dir: str, timeout: float) -> tuple[str, dict]:
    client = docker.from_env()

    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    container_limits = {
        # 'cpus': '0.5',
        'mem_limit': '256m',
        'pids_limit': 100,
        # 'storage_opt': {
        #     'size': '256m',
        # },
    }

    code = shlex.quote(code)

    try:
        container = client.containers.run(
            image=IMAGE_TAG,
            command=f'python -c {code}',
            volumes={work_dir: {'bind': '/app', 'mode': 'rw'}},
            working_dir='/app',
            detach=True,
            network_disabled=True,
            **container_limits
        )

        container.wait(timeout=timeout)
        log = container.logs().decode('utf-8')
        container.remove()

        created_files = os.listdir(work_dir)
        files_content = {}
        for file_name in created_files:
            with open(os.path.join(work_dir, file_name), 'rb') as file:
                files_content[file_name] = file.read()
    finally:
        shutil.rmtree(work_dir)

    return log, files_content


async def build():
    return await asyncio.get_running_loop().run_in_executor(
        _executor,
        sync_build,
    )


def sync_build():
    client = docker.from_env()
    client.images.build(
        path='.',
        dockerfile='py310.dockerfile',
        tag=IMAGE_TAG,
    )
