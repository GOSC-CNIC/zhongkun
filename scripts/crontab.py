from crontab

class Crontab_Update(object):

    def __init__(self):
        # 创建当前用户的crontab，当然也可以创建其他用户的，但得有足够权限
        self.cron = CronTab(user=True)
        # self.cron = CronTab(user='website')

    def add_crontab_job(self, cmmand_line, time_str, commont_name, user):
        # 创建任务
        job = self.cron.new(command=cmmand_line)
        # 设置任务执行周期
        job.setall(time_str)
        # 给任务添加一个标识，给任务设置comment，这样就可以根据comment查询
        job.set_comment(commont_name)
        # 将crontab写入配置文件
        # self.cron.write()
        self.cron.write_to_user(user=user)  # 指定用户，写入指定用户下的crontab任务

    def del_crontab_jobs(self, comment_name, user):
        # 根据comment查询，当时返回值是一个生成器对象，
        # 不能直接根据返回值判断任务是否存在，
        # 如果只是判断任务是否存在，可直接遍历my_user_cron.crons
        # jobs = self.cron.find_comment(commont_name)

        # 返回所有的定时任务，返回的是一个列表
        # a = self.cron.crons
        # print 'a = ', a
        # print 'len(a) = ', len(a)

        # 按comment清除定时任务
        # self.cron.remove_all(comment=comment_name)

        # 按comment清除多个定时任务，一次write即可
        self.cron.remove_all(comment=comment_name)
        self.cron.remove_all(comment=comment_nam e+ ' =')

        # 清除所有定时任务
        # self.cron.remove_all()

        # 写入配置文件
        # self.cron.write()
        self.cron.write_to_user(user=user)  # 指定用户,删除指定用户下的crontab任务

