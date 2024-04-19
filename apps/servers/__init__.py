
def format_who_action_str(username: str, vo_name: str = None):
    s = f'[user]{username}'
    if vo_name:
        s = f'{s};[vo]{vo_name}'

    return s
