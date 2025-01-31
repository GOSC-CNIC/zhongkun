import os
import subprocess
import datetime


VERSION = (3, 2, 0, 'final', 0)     # 'alpha', 'beta', 'rc', 'final'


def get_version(version=None):
    main = '.'.join(str(x) for x in version[:3])

    sub = ''
    if version[3] != 'final':
        mapping = {'alpha': 'a', 'beta': 'b', 'rc': 'rc'}
        sub = mapping[version[3]] + str(version[4])

    return main + sub


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
        "--format='%(refname:short) || %(taggerdate:format:%s) || %(*authorname) || %(*authoremail) || %(subject)'"
        " refs/tags/*",
        capture_output=True,
        shell=True,
        cwd=repo_dir,
        text=True,
    )

    try:
        cmd_output = git_log.stdout
        lines = cmd_output.split('\n')[0:3]
        tz = datetime.timezone.utc
        tags = []
        for line in lines:
            tag = line.split('||')
            if len(tag) == 5:
                version, tm, author, email, content = tag
                new_tag = [
                    version.strip(' ').lower(),
                    datetime.datetime.fromtimestamp(int(tm), tz=tz),
                    author, email,
                    content.replace('*', '\n*')
                ]
                tags.append(new_tag)

    except ValueError:
        return None

    return tags


__version__ = get_version(VERSION)
__git_changeset__ = get_git_changeset()
__git_tagset__ = get_git_tagset()
