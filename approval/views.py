from django.shortcuts import render
from django.http import HttpResponse
from django.utils import timezone
from approval.models import ApprovalRecord
import random
import requests
import json

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

with open('sendgrid-token.txt') as f:
    sendgrid_token = f.read()

def request(request):
    kerb = request.GET.get('kerb')
    discord_id = request.GET.get('discord_id')
    discord_name = request.GET.get('discord_name')
    server = request.GET.get('server')
    token = hex(random.getrandbits(64 * 4))[2:]
    record = ApprovalRecord(
        kerberos = kerb,
        discord_id = discord_id,
        discord_name = discord_name,
        discord_server = server,
        token = token,
        approved = False,
        approval_received = False,
        timestamp = timezone.now())
    record.save()

    message = Mail(
            from_email = 'front-door@busy-beavers-community.com',
            to_emails = '%s@mit.edu' % kerb,
            subject = 'MIT Discord join code',

            html_content = '''
            Your join code is %s.
            ''' % (token[:4]))
    try:
        sg = SendGridAPIClient(sendgrid_token)
        response = sg.send(message)
        print(response.status_code)
        return HttpResponse(json.dumps({
            'success': True
        }))
    except Exception as e:
        return HttpResponse(json.dumps({
            'success': False
        }))

def approve_by_discord(request):
    discord_id = request.GET.get('discord_id')
    code = request.GET.get('code')
    
    try:
        record = ApprovalRecord.objects.get(discord_id = discord_id, token_iexact = code)
        record.approved = True
        record.save()

        return HttpResponse(json.dumps({'success': True}))
    except Exception as e:
        return HttpResponse(json.dumps({'success': False}))

def verify(request):
    try:
        with open('/home/dab1998/approval-bot/approvalbot/approval/approved.html', 'r') as r:
            response_string = r.read()

        token = request.GET.get('token')
        
        record = ApprovalRecord.objects.get(token = token)
        record.approved = True
        record.save()

        return HttpResponse(response_string)

    except Exception as e:
        token = request.GET.get('token')
        
        record = ApprovalRecord.objects.get(token = token)
        record.approved = True
        record.save()

        return HttpResponse('If you are still not a Beaver, email <a href=\'busybeavers@mit.edu>busybeavers@mit.edu</a> as something must be broken.')

def get_approvals(request):
    records = ApprovalRecord.objects.filter(approved = True, approval_received = False)

    discord_ids = [(record.id, record.discord_server, record.discord_id) for record in records]
    return HttpResponse(json.dumps(discord_ids))

def confirm(request):
    record_id = request.GET.get('id')

    record = ApprovalRecord.objects.get(id = record_id)
    record.approval_received = True
    record.save()

    return HttpResponse(json.dumps({'success': True}))

def whois_by_id(request):
    discord_id = request.GET.get('discord_id')

    try:
        record = ApprovalRecord.objects\
                .filter(discord_id = int(discord_id), approved = True).first()
        return HttpResponse(json.dumps({'success': True, 'kerberos': record.kerberos}))
    except Exception as e:
        return HttpResponse(json.dumps({'success': False}))

def register_preapproved(request):
    kerb = request.GET.get('kerb')
    discord_id = request.GET.get('discord_id')
    discord_name = request.GET.get('discord_name')
    server = request.GET.get('server')
    token = hex(random.getrandbits(64 * 4))[2:]

    already_exists = ApprovalRecord.objects\
        .filter(
            discord_id = int(discord_id),
            discord_server = int(server),
            kerberos = kerb,
            approved = True
        ).first()
    if already_exists is not None:
        return HttpResponse(json.dumps({
            'success': True,
            'reason': 'Already exists.',
            'token': already_exists.token
        }))
    else:
        record = ApprovalRecord(
            kerberos = kerb,
            discord_id = discord_id,
            discord_name = discord_name,
            discord_server = server,
            token = token,
            approved = True,
            approval_received = True,
            timestamp = timezone.now())

        record.save()

        return HttpResponse(json.dumps({
            'success': True,
            'token': token
        }))

def replace_kerberos(request):
    kerb = request.GET.get('kerb')
    discord_id = request.GET.get('discord_id')
    discord_name = request.GET.get('discord_name')
    server = request.GET.get('server')
    token = hex(random.getrandbits(64 * 4))[2:]

    already_exists = ApprovalRecord.objects\
        .filter(
            discord_id = int(discord_id),
            discord_server = int(server),
            approved = True
        )

    for record in already_exists:
        record.kerberos = kerb
        record.save()

    return HttpResponse(json.dumps({
        'success': True,
        'token': token,
        'count': already_exists.count()
    }))

def how_many_kerbs(request):
    result = set((record.discord_name, record.discord_id) for record in ApprovalRecord.objects.filter(approved = True))

    result_dict = {
            x[0]: (x[1], [record.kerberos for record in ApprovalRecord.objects.filter(discord_id = x[1], approved = True)])
            for x in result
        }

    result_dict = {x: result_dict[x] for x in result_dict if not all(y == '' for y in result_dict[x][1])}
    return HttpResponse(json.dumps({
        'count': len(result_dict),
        'set': result_dict,
        'blanks': [(x, result_dict[x][0]) for x in result_dict if all(y == '' for y in result_dict[x][1])]
    }))
    '''
    result = set(record.kerberos for record in ApprovalRecord.objects.filter(approved = True))
    return HttpResponse(json.dumps({
        'count': len(result),
        'set': {
            x: [record.discord_name for record in ApprovalRecord.objects.filter(kerberos = x)]
            for x in result
        }
    }))
    '''
