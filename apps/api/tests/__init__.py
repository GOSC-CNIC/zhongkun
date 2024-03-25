from utils.test import get_or_create_user, MyAPITestCase, MyAPITransactionTestCase  # 不能删除，其他模块会从此导入


def set_auth_header(test_case):
    password = 'password'
    user = get_or_create_user(password=password)
    # token = AccessToken.for_user(user)
    # test_case.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
    test_case.client.force_login(user=user)
    test_case.user = user
    return user
