#!/usr/bin/env python3

import os
import re
import smtplib
import argparse
import json
import time
import requests
from fake_useragent import UserAgent
from copy import copy
from lxml import html
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urljoin
import threading
import random
ua = UserAgent()
error = 0


def send_email(price, url, email_info):
    try:
        s = smtplib.SMTP(email_info['smtp_url'])
        s.starttls()
        s.login(email_info['user'], email_info['password'])
    except smtplib.SMTPAuthenticationError:
        print('Failed to login')
    else:
        print('Logged in! Composing message..')
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Price Alert - %s' % price
        msg['From'] = email_info['user']
        msg['To'] = email_info['user']
        text = 'The price is currently %s !! URL to salepage: %s' % (
            price, url)
        part = MIMEText(text, 'plain')
        msg.attach(part)
        s.sendmail(email_info['user'], email_info['user'], msg.as_string())
        print('Email has been sent.')


def get_price(url, selector):
    with requests.get(url, allow_redirects=False, headers={'User-Agent': ua.random}) as r:
        tree = html.fromstring(r.text)
        try:
            price_string = re.findall(
                '\d+.\d+', tree.xpath(selector)[0].text)[0]
            print(price_string)
            return float(price_string.replace(',', ''))
        except (IndexError, TypeError) as e:
            print('Didn\'t find the price')
            print('Sleeping for %d seconds' % args.poll_interval)
            time.sleep(args.poll_interval)


def get_config(config):
    with open(config, 'r') as f:
        return json.loads(f.read())


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config',
                        default='%s/config.json' % os.path.dirname(
                            os.path.realpath(__file__)),
                        help='Configuration file path')
    parser.add_argument('-t', '--poll-interval', type=int, default=30,
                        help='Time in seconds between checks')
    return parser.parse_args()


def main(i):
    global error
    args = parse_args()
    config = get_config(args.config)
    items = config['items'][i]
    while 1:
        print('Checking price for %s (should be lower than %s)' %
              (items[0], items[1]))
        item_page = urljoin(config['base_url'], items[0])
        price = get_price(item_page, config['xpath_selector'])
        if not price:
            error += 1
        if price and price <= items[1]:
            print('Price of %s is %s!! Trying to send email.' %
                  (items[0], price))
            send_email(price, item_page, config['email'])
            break
        elif price:
            print('Price of %s is %s!! Ingore.' % (items[0], price))
            print('Sleeping for %d seconds' % args.poll_interval)
            time.sleep(args.poll_interval)
        if error == 12:
            print('Too much error! Sleeping for %d seconds' %
                  (args.poll_interval*30))
            time.sleep(args.poll_interval*30)


if __name__ == '__main__':
    args = parse_args()
    config = get_config(args.config)
    threads = [threading.Thread(daemon=True, target=main, args=(n,))
               for n in range(0, len(config['items']))]
    [thread.start() for thread in threads]
    # [thread.join() for thread in threads]
    while 1:
        alive = False
        for i in range(0, len(config['items'])):
            alive = alive or threads[i].isAlive()
        if not alive:
            print('Price alert triggered for all items, exiting.')
            break
