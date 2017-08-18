#!/usr/bin/env python
# -*- coding:UTF-8 -*-

"""
后期提升：
    2017.06.27: 修改使用html格式发送解决windows,linux字体显示格式不一致的问题。
    2017.07.15: 任务分类为never,failed,succeeded,running
    2017.08.15: 过滤已经禁用的job
"""

import os
import json
import datetime
import smtplib
import logging
import sys
import time
import getopt
import xml.etree.ElementTree as ET

import requests
from prettytable import PrettyTable
from email.mime.text import MIMEText


import tianfei_log

__author__ = "Talen Hao(天飞)<talenhao@gmail.com>"
__status__ = "product"
__last_date__ = "2017.08.18"
__version__ = __last_date__
__create_date__ = "2017.06.16"

rundeck_server_ip = '192.168.1.111'
rundeck_server_port = '4440'
rundeck_server_protocol = 'http'
rundeck_project = 'in-jobs'
rundeck_token = 'Orbv4nQJ6vXJboj9LKTguQg7j5taRBJx'

# smtplib send mail.修改成自己的正确信息.
mail_host = "smtp.mailserver.talen"
mail_user = "user@mailserver.talen"
mail_pass = "FtAe+Zsfsfiiwoeowiewriworqo843098r092093284842kdoiewj3jijdw09e02r9w"
from_addr = 'user@mailserver.talen'

all_args = sys.argv[1:]
usage = '''
用法：
%s [--命令选项] [参数]

命令选项：
    --help, -h                      帮助。
    --version, -V                   输出版本号。
    --mailaddr, -m 用户名@邮件域名,用户名@邮件域名,...   接收邮件的地址。
''' % sys.argv[0]

LogPath = '/tmp/%s.log.%s' % (os.path.basename(__file__), datetime.datetime.now().strftime('%Y-%m-%d,%H.%M'))
c_logger = tianfei_log.GetLogger(LogPath, __name__, logging.DEBUG).get_l()
today = datetime.date.fromtimestamp(time.time())
c_logger.debug("today is : %s", today)


def get_options():
    mail_user = ''
    if all_args:
        c_logger.debug("命令行参数是 %s", str(all_args))
    else:
        c_logger.error(usage)
        sys.exit()
    try:
        opts, args = getopt.getopt(all_args, "hm:V", ["help", "mail_address=", "version"])
    except getopt.GetoptError:
        c_logger.error(usage)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', "--help"):
            c_logger.info(usage)
            sys.exit()
        elif opt in ("-V", "--version"):
            print('Current version is %0.2f' % float(__version__))
            c_logger.debug('Version %s', __version__)
            sys.exit()
        elif opt in ("-m", "--mail_address"):
            c_logger.info("接收邮件地址名单 %s", arg)
            mail_user = arg
    return mail_user


def get_jobs_uuid():
    jobs_uuid_dict_enable = {}
    jobs_uuid_dict_disable = {}
    jobs_url_api = '%s://%s:%s/api/17/project/%s/jobs' % (rundeck_server_protocol, rundeck_server_ip, rundeck_server_port, rundeck_project)
    jobs_url_api_headers = {'x-rundeck-auth-token': rundeck_token, 'Accept': 'application/json'}
    # jobs_url_api_params = {'jobFilter': 'begin', 'scheduledFilter': 'true'}
    # jobs_url_api_params = {'scheduledFilter': 'true'}
    jobs_url_api_params = {'enabled': 'true'}
    jobs_list = requests.get(jobs_url_api, params=jobs_url_api_params, headers=jobs_url_api_headers)
    c_logger.debug("url: %s", jobs_list.url)
    c_logger.debug("respone code: %s", jobs_list)
    jobs_list_json_data = json.loads(jobs_list.text)
    c_logger.debug(jobs_list_json_data)
    for job in jobs_list_json_data:
        c_logger.debug("job name : %s, enabled: %s, type: %s", job['name'], job['enabled'], type(job['enabled']))
        if job['enabled'] == 1:
            c_logger.debug("job %s is enabled.", job['name'])
            jobs_uuid_dict_enable[job['name']] = job['id']
        elif job['enabled'] == 0:
            c_logger.debug("job %s is diabled.", job['name'])
            jobs_uuid_dict_disable[job['name']] = job['id']
    c_logger.debug("All job num: %s", len(jobs_list_json_data))
    c_logger.debug("Current job num: %s", len(jobs_uuid_dict_enable))
    return jobs_uuid_dict_enable, jobs_uuid_dict_disable


def jobs_status(uuids):
    '''
    {'job_name': {'job_status': status, 'job_started': started, ...}, 'job_name2': {...}}
    '''
    jobs_status_running = {}
    jobs_status_failed = {}
    jobs_status_succeeded = {}
    jobs_status_never = {}
    count = 0
    uuids = sorted(uuids.items(), key=lambda d: d[0])
    for name, uuid in uuids:
        # name = str('rdjob_' + name)
        count += 1
        c_logger.debug(type(name))
        job_execution_url_api_headers = {'x-rundeck-auth-token': rundeck_token}
        # running url request
        job_execution_url_running = '%s://%s:%s/api/1/job/%s/executions?status=running' % (
            rundeck_server_protocol, rundeck_server_ip, rundeck_server_port, uuid)
        job_execution_running = requests.get(job_execution_url_running, headers=job_execution_url_api_headers)
        job_root_running = ET.fromstring(job_execution_running.text)
        root = job_root_running
        c_logger.debug("running url: %r, content: %r", job_execution_running.url, job_execution_running.raw.read())
        job_running_result_count = int(root.findall("./executions")[0].get('count'))
        c_logger.debug("%s: job_running_result_count is %s", name, job_running_result_count)
        if job_running_result_count > 0:
            jobs_status_running[name] = {}
            jobs_status_running[name]['job_ended'] = 'running'
            jobs_status_running[name]['job_name'] = root.findtext("./executions/execution/job/name")
            jobs_status_running[name]['job_status'] = 'running'
            jobs_status_running[name]['job_started'] = root.findtext("./executions/execution/date-started")
        elif job_running_result_count == 0:
            # finished url request
            job_execution_url = '%s://%s:%s/api/1/job/%s/executions?max=1' % (
                rundeck_server_protocol, rundeck_server_ip, rundeck_server_port, uuid)
            job_execution = requests.get(job_execution_url, headers=job_execution_url_api_headers)
            c_logger.debug("finished url: %r, content: %r", job_execution.url, job_execution.raw.read())
            job_root = ET.fromstring(job_execution.text)
            root = job_root
            job_result_count = int(root.findall("./executions")[0].get('count'))
            if job_result_count == 0:
                c_logger.debug("job_result_count: %r, 从来没有执行过。", job_result_count)
                jobs_status_never[name] = {}
                jobs_status_never[name]['job_ended'] = "Never execution."
                jobs_status_never[name]['job_name'] = name
                jobs_status_never[name]['job_status'] = "Never"
                jobs_status_never[name]['job_started'] = "Never"
            elif job_result_count > 0 and root.findall("./executions/execution")[0].get('status') == 'succeeded':
                c_logger.debug("%r, %r, %r, %r",
                               root.findtext("./executions/execution/date-ended"),
                               root.findtext("./executions/execution/job/name"),
                               root.findall("./executions/execution")[0].get('status'),
                               root.findtext("./executions/execution/date-started"))
                jobs_status_succeeded[name] = {}
                jobs_status_succeeded[name]['job_ended'] = root.findtext("./executions/execution/date-ended")
                jobs_status_succeeded[name]['job_name'] = root.findtext("./executions/execution/job/name")
                jobs_status_succeeded[name]['job_status'] = root.findall("./executions/execution")[0].get('status')
                jobs_status_succeeded[name]['job_started'] = root.findtext("./executions/execution/date-started")
            else:
                print(root.text)
                jobs_status_failed[name] = {}
                jobs_status_failed[name]['job_ended'] = root.findtext("./executions/execution/date-ended")
                jobs_status_failed[name]['job_name'] = root.findtext("./executions/execution/job/name")
                jobs_status_failed[name]['job_status'] = root.findall("./executions/execution")[0].get('status')
                jobs_status_failed[name]['job_started'] = root.findtext("./executions/execution/date-started")
        c_logger.info(count)
    return jobs_status_running, jobs_status_succeeded, jobs_status_failed, jobs_status_never


def format_job_status(title, msg):
    job_status_list = PrettyTable(["Job name", "Status", "Started time", "Ended time"])
    job_status_list.align = "l"  # Left align
    job_status_list.padding_width = 1  # One space between column edges and contents (default)
    job_status_list.header = True
    # job_status_list.sortby = 'Job name'
    for name,item in msg.items():
        c_logger.debug('%r,%r', name, item)
        if item:
            job_status_list.add_row([item['job_name'], item['job_status'], item['job_started'], item['job_ended']])
    message = "%s" % (title + job_status_list.get_html_string(format=True))
    c_logger.debug('message: %r', message)
    return message


def status_format(content):
    running_jobs = format_job_status('RUNNING JOBS', content[0])
    succeeded_jobs = format_job_status('succeeded JOBS', content[1])
    failed_jobs = format_job_status('FAILED JOBS', content[2])
    never_jobs = format_job_status('NEVER RUN JOBS', content[3])
    msg = "%s" % (running_jobs + failed_jobs + never_jobs + succeeded_jobs)
    c_logger.debug("msg: %s", msg)
    return msg


def send_mail(mailuser, msg):
    # Create a text/plain message
    # windows与linux显示不相同，修改成发送html格式
    # mmsg = MIMEText(msg, 'plain', 'utf-8')
    mmsg = MIMEText(msg, 'html', 'utf-8')
    mmsg['Subject'] = 'Rundeck result %s.' % today
    mmsg['From'] = 'rundeck-server@in66.cc'

    # to_addr = ['talenhao@gmail.com']
    to_addr = mailuser.split(',')
    c_logger.debug("mail to : %r", to_addr)

    # 3.6环境报错，修改成smtp模式
    # smtpObj = smtplib.SMTP_SSL()
    smtpObj = smtplib.SMTP()
    smtpObj.connect(mail_host)
    smtpObj.ehlo()
    smtpObj.starttls()
    smtpObj.ehlo()
    smtpObj.login(mail_user, mail_pass)
    try:
        smtpObj.sendmail(from_addr, to_addr, mmsg.as_string())
        smtpObj.quit()
        c_logger.info("邮件发送成功")
    except smtplib.SMTPException:
        c_logger.error("Error: 无法发送邮件")
    smtpObj.close()


def main():
    try:
        mailuser = get_options()
    except UnboundLocalError:
        print(usage)
        sys.exit(0) 
    jobs_uudis = get_jobs_uuid()
    c_logger.debug(jobs_uudis)
    enabled_jobs = jobs_uudis[0]
    # disabled_jobs = jobs_uudis[1]
    content = jobs_status(enabled_jobs)
    c_logger.debug('%r', content)
    msg = status_format(content)
    c_logger.debug("mail_send: %r", msg)
    send_mail(mailuser, msg)


if __name__ == "__main__":
    main()

