#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import boto3
from jinja2 import Template
import json
import os
import requests


def get_identity_doc():
    id_doc = requests.get(
        'http://169.254.169.254/latest/dynamic/instance-identity/document')
    return id_doc.json()


def get_vpc_data(region='us-east-1'):
    interface = requests.get(
        'http://169.254.169.254/latest/meta-data/network/interfaces/macs/').text
    vpc_id = requests.get(
        'http://169.254.169.254/latest/meta-data/network/interfaces/macs/{}/vpc-id'.format(interface)).text
    client = boto3.client('ec2', region_name=region)
    vpc_name = client.describe_vpcs(VpcIds=[vpc_id])[
        'Vpcs'][0]['Tags'][0]['Value']
    return {'vpc_id': vpc_id, 'vpc_name': vpc_name}


def ec2_info():
    info = get_identity_doc()
    info.update(get_vpc_data(info['region']))
    return {'ec2': info}


def parse_template(template, context):
    t = Template(json.dumps(template))
    parsed = t.render(**context)
    return json.loads(parsed)


def send(webhook_url, payload):
    payload = json.dumps(payload)
    return requests.post(webhook_url, data=payload)


def load_templates(abspath):
    template_dict = {}
    if not os.path.exists(abspath):
        return False
    for dirpath, dirnames, filenames in os.walk(abspath):
        for filename in filenames:
            with open(os.path.join(dirpath, filename), 'r') as file:
                template_dict.update(json.load(file))
    return template_dict


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--text",
                        help="Notification text")
    parser.add_argument("--username",
                        help="Notification display name")
    parser.add_argument("--channel",
                        help="the #slack_channel to notify.")
    parser.add_argument("--icon-emoji",
                        help="the :emoji: code to use as a slack icon")
    parser.add_argument("--color",
                        help="Can either be one of 'good', 'warning', 'danger', or any hex color code")

    parser.add_argument("-url", "--webhook-url",
                        dest='webhook_url',
                        help="the webhook url")
    parser.add_argument("--template-dir",
                        help="directory containing templates to load",
                        default='/etc/slack-notifier/templates.d')
    parser.add_argument("--template",
                        help="named template to use")
    parser.add_argument("-l", "--list-templates", action='store_true',
                        help="list available template names from loaded templates")
    args = parser.parse_args()

    templates = load_templates(args.template_dir)
    if args.list_templates:
        print "The following templates are available:"
        for template in templates.keys():
            print "{}".format(template)
        exit()

    if not args.template or (args.template not in templates.keys()):
        print "you must specify a valid template name: see --list-templates for available names."
        exit(1)

    template = templates[args.template]
    context = ec2_info()

    webhook_url = template.pop('webhook_url', None)
    if args.webhook_url:
        webhook_url = args.webhook_url
    if not webhook_url:
        print "A URL for webhook must be specified either in a template or on the command line."
        exit(1)

    payload = parse_template(template, context)

    if args.icon_emoji:
        payload['icon_emoji'] = args.icon_emoji
    if args.username:
        payload['username'] = args.username
    if args.color:
        if 'attachments' in payload:
            for attachment in payload['attachments']:
                attachment['color'] = args.color

    # Some potential logic for this option:
    # if no template is specified:
    # url is required. everything else is optional
    # if template is specified
    #   and there is no attachment,
    #       override the text field
    #   else # there's an attachment
    #       override fallback
    #       if fields are on the attachment, override the field text?
    # This introduces lots of ambiguity when there is more than one attachment or field
    # Probably best to make this mutually exclusive with templates.
    if args.text:
        if args.template:
            print "Overriding text is not compatible with using templates. (ambiguous override)"
            exit(1)
        else:
            payload['text'] = args.text

    notification = send(webhook_url, payload)
    if notification.status_code == requests.codes.ok:
        print "{} OK".format(requests.codes.ok)
    else:
        notification.raise_for_status()
