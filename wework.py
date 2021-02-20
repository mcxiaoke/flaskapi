#!/usr/bin/env python
import json
import os
import redis
import requests
import logging
from flask import request, Flask
from datetime import datetime
from config import WX_WORK_CORP_ID, WX_WORK_APP_ID, WX_WORK_SECRET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('wework')

ACCESS_TOKEN_URL = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={}&corpsecret={}'

SEND_MSG_URL = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}'

TOKEN_KEY = 'wework_token_{}'.format(WX_WORK_APP_ID)

REDIS_HOST = 'localhost' if 'HOST_REDIS' in os.environ else 'redis'
_redis = redis.StrictRedis(host=REDIS_HOST, port=6379, decode_responses=True)

logger.info('init with app:%s, corp:%s', WX_WORK_APP_ID, WX_WORK_CORP_ID)

def _set_token(new_token):
    _redis.set(TOKEN_KEY, new_token, ex=7200)
    logger.info('token saved to redis, token:%s', new_token[:8])


def _get_token():
    return _redis.get(TOKEN_KEY) or _request_token()


def _request_token():
    token_url = ACCESS_TOKEN_URL.format(WX_WORK_CORP_ID, WX_WORK_SECRET)
    try:
        r = requests.get(token_url)
        if r.status_code == 200:
            rj = r.json()
            logger.debug('_request_token, res:%s', rj)
            if rj['errcode'] == 0:
                _set_token(rj['access_token'])
                return rj['access_token']
    except Exception:
        logger.exception('_request_token')


def send_message(content):
    logger.debug('send_message: [%s]', content)
    tk = _get_token()
    send_url = SEND_MSG_URL.format(tk)
    suffix = ' <{}>'.format(datetime.strftime(
        datetime.now(), '%Y-%m-%d %H:%M:%S'))
    data = {
        'touser': '@all',
        'msgtype': 'text',
        'agentid': WX_WORK_APP_ID,
        'text': {
            'content': '{}\n{}'.format(content, suffix)
        }
    }
    try:
        r = requests.post(send_url, data=json.dumps(data))
        logger.info('send_message: %d %s', r.status_code, r.json())
        return r.json(), 200
    except Exception as e:
        logger.exception('send_message')
        return json.dumps({'error': str(e)}), 400


def wework_send():
    logger.debug('wework_send: args=%s', request.values)
    title = request.values.get('title')
    desp = request.values.get('desp')
    if not title:
        return json.dumps({'error': 'missing title'}), 400
    if desp:
        return send_message('{}\n{}'.format(title, desp))
    else:
        return send_message(title)


if __name__ == '__main__':
    app = Flask(__name__)
    app.add_url_rule('/wework/api/u5bs0CnW.send',
                     view_func=wework_send, methods=['GET', 'POST'])
    app.run('0.0.0.0', 8008, debug=True)
