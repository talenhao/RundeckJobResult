# RundeckJobResult
收集rundeck任务运行结果并做个报表,日报,发送邮件给指定联系人.

rundeck 日报发送脚本使用指南

Created by 天飞, last modified on 08/29, 2017


rundeck服务器：192.168.1.1xx
python	3.x	python3.6.1/bin/python3.6

usage	 	

用法：
RdJobResult.py [--命令选项] [参数]

命令选项：

    --help, -h                      帮助。

    --version, -V                   输出版本号。

    --mailaddr, -m 用户名@邮件域名,用户名@邮件域名,...   接收邮件的地址。

eg: python3.6 rundeck_job_status.py -m tianfei@in66.com,tianfei2@in66.com,...
log	 	

/tmp/rundeck_job_status.py.log.${date},${hour.min}

eg: /tmp/rundeck_job_status.py.log.2017-06-27,16.22

####可添加到rundeck上做成一个job
![image](https://github.com/talenhao/RundeckJobResult/blob/master/img/RdJobResult.png?raw=true)
任务位于rundeck执行平台in-jobs project的in/yunwei目录下
* 常规订阅：	
如果需要添加日报订阅者，直接rundeck_result.start任务，option上添加订阅者邮箱即可，使用","号分割。

* 临时订阅：	
如果是临时订阅，在任务运行界面mailto参数上点击"New Value"，输入订阅者邮件地址。

 


