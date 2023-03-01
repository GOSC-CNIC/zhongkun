import os
import subprocess
import datetime

from django.utils.version import get_version


VERSION = (0, 9, 0, 'rc', 1)     # 'alpha', 'beta', 'rc', 'final'


def get_git_changeset():
    # Repository may not be found if __file__ is undefined, e.g. in a frozen
    # module.
    if "__file__" not in globals():
        return None
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    git_log = subprocess.run(
        'git log --pretty="format:%ct||%an" --quiet -1',
        capture_output=True,
        shell=True,
        cwd=repo_dir,
        text=True,
    )

    try:
        cmd_output = git_log.stdout
        timestamp, author = cmd_output.split('||')
        tz = datetime.timezone.utc
        timestamp = datetime.datetime.fromtimestamp(int(timestamp), tz=tz)
    except ValueError:
        return None

    return {'timestamp': timestamp, 'author': author}


def get_git_tagset():
    # Repository may not be found if __file__ is undefined, e.g. in a frozen
    # module.
    if "__file__" not in globals():
        return None
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    git_log = subprocess.run(
        "git for-each-ref --count=3 --sort='-taggerdate' "
        "--format='%(refname:short) || %(taggerdate:format:%s) || %(*authorname) || %(*authoremail) || %(subject)'",
        capture_output=True,
        shell=True,
        cwd=repo_dir,
        text=True,
    )

    try:
        cmd_output = git_log.stdout
        lines = cmd_output.split('\n')[0:3]
        tags = [item.split('||') for item in lines if item]
        tz = datetime.timezone.utc
        for tag in tags:
            tag[1] = datetime.datetime.fromtimestamp(int(tag[1]), tz=tz)
            desc = tag[4]
            tag[4] = desc.replace('*', '\n*')

    except ValueError:
        return None

    return tags


__version__ = get_version(VERSION)
__git_changeset__ = get_git_changeset()
__git_tagset__ = get_git_tagset()
