#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: blinking.yan
# @Date:   2016-03-03 21:56:26
# @Last Modified by:   blinking.yan
# @Last Modified time: 2016-03-03 22:45:18
# @Description: 获取腾讯企业邮箱通讯录
import requests
import re
import rsa
import sys
import base64
import time
import argparse
reload(sys)

sys.setdefaultencoding('utf8')


# 打印部门人员信息
def print_tree(id, department_infos, level, staff_infors, f):
    prefix = '----' * level
    text = prefix + department_infos[id]['name'] + prefix
    print text
    f.write(text + '\n')
    for key, value in department_infos.items():
        if value['pid'] == id:
            print_tree(
                value['id'], department_infos, level + 1, staff_infors, f)
    prefix = '    ' * level
    for staff in staff_infors:
        if staff['pid'] == id:
            text = prefix + staff['name'] + '  ' + staff['alias']
            print text
            f.write(text + '\n')


# 提取RSA算法的公钥
def get_public_key(content):
    regexp = r'var\s*PublicKey\s*=\s*"(\w+?)";'
    results = re.findall(regexp, content)
    if results:
        return results[0]


# 获取ts参数
def get_ts(content):
    regexp = r'PublicTs\s*=\s*"([0-9]+)"'
    results = re.findall(regexp, content)
    if results:
        return results[0]


# 计算p参数
def get_p(public_key, password, ts):
    public_key = rsa.PublicKey(int(public_key, 16), 65537)
    res_tmp = rsa.encrypt(
        '{password}\n{ts}\n'.format(password=password, ts=ts), public_key)
    return base64.b64encode(res_tmp)


def msg():
    return 'python get_tencent_exmail_contacts.py -u name@domain.com -p passw0rd'

if __name__ == "__main__":
    description = "获取腾讯企业邮箱通讯录"
    parser = argparse.ArgumentParser(description=description, usage=msg())
    parser.add_argument(
        "-u", "--email", required=True, dest="email", help="邮箱名")
    parser.add_argument(
        "-p", "--password", required=True, dest="password", help="邮箱密码")
    parser.add_argument(
        "-l", "--limit", required=False, dest="limit", default=10000, help="通讯录条数")
    parser.add_argument(
        "-e", "--efile", required=False, dest="emailfile", default="emails.txt", help="邮箱保存文件")
    parser.add_argument(
        "-d", "--dfile", required=False, dest="departfile", default="departments.txt", help="部门信息保存文件")
    args = parser.parse_args()
    email = args.email
    password = args.password
    limit = args.limit
    emailfile = args.emailfile
    departfile = args.departfile
    session = requests.Session()

    headers = {'Connection': 'keep-alive',
               'Cache-Control': 'max-age=0',
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
               'Upgrade-Insecure-Requests': 1,
               'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36',
               'DNT': 1,
               'Accept-Encoding': 'gzip, deflate, sdch',
               'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4',
               }
    resp = session.get('http://exmail.qq.com/login', headers=headers)
    content = resp.content

    public_key = get_public_key(content)

    ts = get_ts(content)

    p = get_p(public_key, password, ts)

    # print ts
    # print public_key
    # print p

    uin = email.split('@')[0]
    domain = email.split('@')[1]
    # print uin
    # print domain

    post_data = {}
    post_data['sid'] = ''
    post_data['firstlogin'] = False
    post_data['domain'] = domain
    post_data['aliastype'] = 'other'
    post_data['errtemplate'] = 'dm_loginpage'
    post_data['first_step'] = ''
    post_data['buy_amount'] = ''
    post_data['year'] = ''
    post_data['company_name'] = ''
    post_data['is_get_dp_coupon'] = ''
    post_data['starttime'] = int(time.time() * 1000)
    post_data['redirecturl'] = ''
    post_data['f'] = 'biz'
    post_data['uin'] = uin
    post_data['p'] = p
    post_data['delegate_url'] = ''
    post_data['ts'] = ts
    post_data['from'] = ''
    post_data['ppp'] = ''
    post_data['chg'] = 0
    post_data['loginentry'] = 3
    post_data['s'] = ''
    post_data['dmtype'] = 'bizmail'
    post_data['fun'] = ''
    post_data['inputuin'] = email
    post_data['verifycode'] = ''

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    url = 'https://exmail.qq.com/cgi-bin/login'
    resp = session.post(url, headers=headers, data=post_data)

    regexp = r'sid=(.*?)"'

    sid = re.findall(regexp, resp.content)[0]
    url = 'http://exmail.qq.com/cgi-bin/laddr_biz?action=show_party_list&sid={sid}&t=contact&view=biz'
    resp = session.get(url.format(sid=sid))

    text = resp.text
    regexp = r'{id:"(\S*?)", pid:"(\S*?)", name:"(\S*?)", order:"(\S*?)"}'
    results = re.findall(regexp, text)
    department_ids = []
    department_infor = dict()
    root_department = None
    for item in results:
        department_ids.append(item[0])
        department = dict(id=item[0], pid=item[1], name=item[2], order=item[3])
        department_infor[item[0]] = department
        if item[1] == 0 or item[1] == '0':
            root_department = department

    regexp = r'{uin:"(\S*?)",pid:"(\S*?)",name:"(\S*?)",alias:"(\S*?)",sex:"(\S*?)",pos:"(\S*?)",tel:"(\S*?)",birth:"(\S*?)",slave_alias:"(\S*?)",department:"(\S*?)",mobile:"(\S*?)"}'

    all_emails = []
    staff_infors = []
    for department_id in department_ids:
        url = 'http://exmail.qq.com/cgi-bin/laddr_biz?t=memtree&limit={limit}&partyid={partyid}&action=show_party&sid={sid}'
        resp = session.get(
            url.format(limit=limit, sid=sid, partyid=department_id))
        text = resp.text
        results = re.findall(regexp, text)

        for item in results:
            all_emails.append(item[3])
            print item[3]
            staff = dict(uin=item[0], pid=item[1], name=item[2], alias=item[3], sex=item[4], pos=item[
                         5], tel=item[6], birth=item[7], slave_alias=item[8], department=item[9], mobile=item[10])
            staff_infors.append(staff)

    with open(emailfile, 'w') as f:
        for item in all_emails:
            f.write(item + '\n')

    with open(departfile, 'w') as f:
        print_tree(root_department['id'], department_infor, 0, staff_infors, f)

    print("total email count: %i" % len(all_emails))
    print("total department count: %i" % len(department_ids))
