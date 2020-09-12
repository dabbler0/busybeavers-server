#!/usr/bin/env python3

import discord
import requests
import re
import json
import asyncio
import csv

client = discord.Client()

command_regex = re.compile('!kerberos ([a-zA-Z0-9]+)')
alt_command_regex = re.compile('!kerberos {([a-zA-Z0-9]+)}')
link_follow_regex = re.compile('\"/bin/cgicso\?query=([^\"]*)\"')
class_year_regex = re.compile('year: (\d|G)')

psr = re.compile('!register ([a-zA-Z0-9_-]+) (.*)')
rsr = re.compile('!replace ([a-zA-Z0-9_-]+) (.*)')
label = re.compile('!label (.*)')
whois = re.compile('!whois (.*)')

deletion_queue = []

someone_is_retrying = False

async def getdirectoryentry(m):
    global someone_is_retrying
    search_result = requests.get('https://web.mit.edu/bin/cgicso?options=general&query=%s' % m).content.decode()

    my_responsibility = False
    if not someone_is_retrying:
        my_responsibility = True
        someone_is_retrying = True
    while 'exceeded alloted time' in search_result:
        await asyncio.sleep(10)
        if my_responsibility or not someone_is_retrying:
            search_result = requests.get('https://web.mit.edu/bin/cgicso?options=general&query=%s' % m).content.decode()
            print('BLOCKED, RETRYING')
        else:
            print('Someone else\'s responsibility.')
    someone_is_retrying = False

    if (':%s@MIT.EDU' % m) in search_result:
        return search_result
    else:
        # Try all links
        while True:
            link_to_follow = link_follow_regex.search(search_result)
            if link_to_follow is not None:
                print('Following', link_to_follow[0])
                new_result =\
                    requests.get('https://web.mit.edu' + link_to_follow[0][1:-1]).content.decode()
                if (':%s@MIT.EDU' % m) in new_result:
                    return new_result
                search_result = search_result[link_to_follow.span()[1]:]
            else:
                break
    return None

async def getclassyear(m):
    entry = await getdirectoryentry(m)
    if entry is None:
        return None
    elif class_year_regex.search(entry) is None:
        return -1
    else:
        return class_year_regex.search(entry)[1]

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_member_update(old_member, member):
    year_to_role_map = {
        '4': discord.utils.get(member.guild.roles, name='2020'),
        '3': discord.utils.get(member.guild.roles, name='2021'),
        '2': discord.utils.get(member.guild.roles, name='2022'),
        '1': discord.utils.get(member.guild.roles, name='2023'),
        'G': discord.utils.get(member.guild.roles, name='Grad Student'),
        'unknown': discord.utils.get(member.guild.roles, name='Non-Current Student'),
        -1: discord.utils.get(member.guild.roles, name='Non-Student'),
    }

    if not any(role.name == 'Beavers' for role in member.roles):
        print('%s is not a beaver' % str(member))
        return

    if any(role.name in ('2020', '2021', '2022', '2023', 'Grad Student', 'Non-Current Student', 'Non-Student') for role in member.roles):
        print('%s is already labelled' % str(member))
        return

    unknown_file = open('unknown-members.txt', 'a')
    print('REQUESTING ON UPDATE', str(member), member.id)
    result = requests.get('http://busy-beavers-community.com/approval/whois-id/', params = {
        'discord_id': member.id
    }).content.decode()
    result = json.loads(result)

    if result['success']:
        class_year = await getclassyear(result['kerberos'])
        if class_year is None:
            class_year = 'unknown'
            #unknown_file.write('%s, %s not real kerberos\n' % (str(member), result['kerberos']))
            #print('%s, %s not real kerberos\n' % (str(member), result['kerberos']))
            #print(await getdirectoryentry(result['kerberos']))
        if class_year in year_to_role_map:
            print('USER', result['kerberos'], 'AS', str(member), 'IS YEAR', class_year)
            print('ADDING ROLE', year_to_role_map[class_year], 'TO', member)
            await member.add_roles(year_to_role_map[class_year])
            print('SUCCESSFULLY ADDED ROLE.')
        else:
            print('USER', result['kerberos'], 'HAS NO INTELLIGIBLE CLASS YEAR')
            unknown_file.write('%s, %s unintelligible\n' % (str(member), result['kerberos']))
    else:
        unknown_file.write('%s no associated kerberos\n' % (str(member)))
        print('I DO NOT KNOW WHO USER', member.name, 'IS')

@client.event
async def on_message(message):
    # Ignore  anything not from the front door channel.
    if (message.channel.name != 'classifier-control-panel'):
        return

    print('seen message', message.content)
    print('match', whois.match(message.content))

    if message.content == '!rerun-class-assignments':
        year_to_role_map = {
            '4': discord.utils.get(message.guild.roles, name='2020'),
            '3': discord.utils.get(message.guild.roles, name='2021'),
            '2': discord.utils.get(message.guild.roles, name='2022'),
            '1': discord.utils.get(message.guild.roles, name='2023'),
            'G': discord.utils.get(message.guild.roles, name='Grad Student'),
            'unknown': discord.utils.get(message.guild.roles, name='Non-Current Student'),
            -1: discord.utils.get(message.guild.roles, name='Non-Student'),
        }

        total = len(message.guild.members)
        for i, member in enumerate(message.guild.members):
            if not any(role.name == 'Beavers' for role in member.roles):
                print('%s is not a beaver' % str(member))
                continue

            if any(role.name in ('2020', '2021', '2022', '2023', 'Grad Student', 'Non-Current Student', 'Non-Student') for role in member.roles):
                print('%s is already labelled' % str(member))
                continue

            unknown_file = open('unknown-members.txt', 'a')
            print('REQUESTING', i, 'OF', total, member.id)
            result = requests.get('http://busy-beavers-community.com/approval/whois-id/', params = {
                'discord_id': member.id
            }).content.decode()
            result = json.loads(result)

            if result['success']:
                class_year = await getclassyear(result['kerberos'])
                if class_year is None:
                    class_year = 'unknown'
                    '''
                    unknown_file.write('%s, %s not real kerberos\n' % (str(member), result['kerberos']))
                    print(await getdirectoryentry(result['kerberos']))
                    '''
                if class_year in year_to_role_map:
                    print('USER', result['kerberos'], 'AS', str(member), 'IS YEAR', class_year)
                    print('ADDING ROLE', year_to_role_map[class_year], 'TO', member)
                    await member.add_roles(year_to_role_map[class_year])
                    print('SUCCESSFULLY ADDED ROLE.')
                else:
                    print('USER', result['kerberos'], 'HAS NO INTELLIGIBLE CLASS YEAR')
                    unknown_file.write('%s, %s unintelligible\n' % (str(member), result['kerberos']))
            else:
                unknown_file.write('%s no associated kerberos\n' % (str(member)))
                print('I DO NOT KNOW WHO USER', member.name, 'IS')
            await asyncio.sleep(1)

    if message.content == '!import-csv':
        total = len(message.guild.members)
        for row in csv.reader(open('mappings.csv')):
            if row[2] != '':
                matches = [member for member in message.guild.members if str(member) == row[1]]
                print(row[1], matches)
                if len(matches) > 0:
                    member = matches[0]
                else:
                    member = None
                if member is None:
                    print('CANNOT FIND MEMBER', row[1])
                    continue
                result = requests.get('http://busy-beavers-community.com/approval/register-preapproved/', params = {
                    'kerb': row[2],
                    'discord_id':  member.id,
                    'discord_name': row[1],
                    'server': message.guild.id
                }).content.decode()
                print(result)
                result = json.loads(result)

                print(result)
                print('Associated', member.id, row[2])

                await asyncio.sleep(0.5)

    if psr.match(message.content):
        m = psr.match(message.content)
        row = [None, m[2], m[1]]
        matches = [member for member in message.guild.members if str(member) == row[1]]
        print(row[1], matches)
        if len(matches) > 0:
            member = matches[0]
        else:
            member = None

        if member is None:
            print('CANNOT FIND MEMBER', row[1])
            return
        result = requests.get('http://busy-beavers-community.com/approval/register-preapproved/', params = {
            'kerb': row[2],
            'discord_id':  member.id,
            'discord_name': row[1],
            'server': message.guild.id
        }).content.decode()
        print(result)
        result = json.loads(result)

        print(result)
        print('Associated', member.id, row[2])

        await asyncio.sleep(0.5)

    if rsr.match(message.content):
        m = rsr.match(message.content)
        row = [None, m[2], m[1]]
        matches = [member for member in message.guild.members if str(member) == row[1]]
        print(row[1], matches)
        if len(matches) > 0:
            member = matches[0]
        else:
            member = None

        if member is None:
            print('CANNOT FIND MEMBER', row[1])
            return
        result = requests.get('http://busy-beavers-community.com/approval/replace-kerberos/', params = {
            'kerb': row[2],
            'discord_id':  member.id,
            'discord_name': row[1],
            'server': message.guild.id
        }).content.decode()
        result = json.loads(result)

        await message.channel.send('Modified %d records.' % result['count'])

    if label.match(message.content):
        m = label.match(message.content)

        matches = [member for member in message.guild.members if str(member) == m[1]]

        if len(matches) > 0:
            member = matches[0]
        else:
            member = None

        if member is None:
            print('CANNOT FIND MEMBER', m[1])
            return

        year_to_role_map = {
            '4': discord.utils.get(member.guild.roles, name='2020'),
            '3': discord.utils.get(member.guild.roles, name='2021'),
            '2': discord.utils.get(member.guild.roles, name='2022'),
            '1': discord.utils.get(member.guild.roles, name='2023'),
            'G': discord.utils.get(member.guild.roles, name='Grad Student'),
            'unknown': discord.utils.get(member.guild.roles, name='Non-Current Student'),
            -1: discord.utils.get(member.guild.roles, name='Non-Student'),
        }

        if not any(role.name == 'Beavers' for role in member.roles):
            print('%s is not a beaver' % str(member))
            return

        if any(role.name in ('2020', '2021', '2022', '2023', 'Grad Student', 'Non-Current Student', 'Non-Student') for role in member.roles):
            print('%s is already labelled' % str(member))
            return

        unknown_file = open('unknown-members.txt', 'a')
        print('REQUESTING ON UPDATE', str(member), member.id)
        result = requests.get('http://busy-beavers-community.com/approval/whois-id/', params = {
            'discord_id': member.id
        }).content.decode()
        result = json.loads(result)

        if result['success']:
            class_year = await getclassyear(result['kerberos'])
            if class_year is None:
                class_year = 'unknown'
                #unknown_file.write('%s, %s not real kerberos\n' % (str(member), result['kerberos']))
                #print('%s, %s not real kerberos\n' % (str(member), result['kerberos']))
                #print(await getdirectoryentry(result['kerberos']))
            if class_year in year_to_role_map:
                print('USER', result['kerberos'], 'AS', str(member), 'IS YEAR', class_year)
                print('ADDING ROLE', year_to_role_map[class_year], 'TO', member)
                await member.add_roles(year_to_role_map[class_year])
                print('SUCCESSFULLY ADDED ROLE.')
            else:
                print('USER', result['kerberos'], 'HAS NO INTELLIGIBLE CLASS YEAR')
                unknown_file.write('%s, %s unintelligible\n' % (str(member), result['kerberos']))
        else:
            unknown_file.write('%s no associated kerberos\n' % (str(member)))
            print('I DO NOT KNOW WHO USER', member.name, 'IS')

    if whois.match(message.content):
        m = whois.match(message.content)

        matches = [member for member in message.guild.members if str(member) == m[1]]

        if len(matches) > 0:
            member = matches[0]
        else:
            member = None

        if member is None:
            await message.channel.send('No such member.')
            return

        result = requests.get('http://busy-beavers-community.com/approval/whois-id/', params = {
            'discord_id': member.id
        }).content.decode()
        result = json.loads(result)

        if result['success']:
            await message.channel.send('Member `%s` is associated with kerberos `%s`.' % (member, result['kerberos']))
        else:
            await message.channel.send('Member `%s` is not associated with a kerberos.' % (member, result['kerberos']))

    if message.content == '!unlabelled-people':
        results = [member for member in message.guild.members if
            any(role.name == 'Beavers' for role in member.roles) and
            not any(role.name in 
            ('2020', '2021', '2022', '2023', 'Grad Student', 'Non-Current Student', 'Non-Student') for role in member.roles)]

        tmp = open('tmp.txt', 'w')
        tmp.write('\n'.join(str(result) for result in results))
        tmp.flush()
        
        await message.channel.send('Here is a list of unclassified members.', file=discord.File('tmp.txt'))

    if message.content == '!no-directory-entry':
        results = [member for member in message.guild.members if
            any(role.name == 'Non-Current Student' for role in member.roles)]

        tmp = open('tmp.txt', 'w')
        tmp.write('\n'.join(str(result) for result in results))
        tmp.flush()
        
        await message.channel.send('Here is a list of unclassified members.', file=discord.File('tmp.txt'))

    if message.content == '!blanks':
        results = json.loads(requests.get('http://busy-beavers-community.com/approval/count').content.decode())

        response_message = '```'

        for name, did in results['blanks']:
            members = [member for member in message.guild.members if member.id == did]
            if len(members) == 0:
                response_message += 'No member %s ' % name + '\n'
            else:
                members = [member for member in members if
                        any(role.name == 'Beavers' for role in member.roles)]
                if len(members) == 0:
                    response_message += '%s not a beaver' % name + '\n'
                else:
                    response_message += '%s NEEDS ATTENTION' % name + '\n'

        tmp = open('tmp.txt', 'w')
        tmp.write(response_message)
        tmp.flush()

    if message.content == '!nonbeaver-dynos':
        results = [member for member in message.guild.members if
            len(member.roles) > 1 and
            not any(role.name == 'Beavers' for role in member.roles)]

        tmp = open('tmp.txt', 'w')
        tmp.write('\n'.join(str(result) + ': ' + (str(result.roles)) for result in results))
        tmp.flush()
        
        await message.channel.send('Here is a list of non-Beavers with roles.', file=discord.File('tmp.txt'))

print('Running now')
with open('classifier-token.txt') as f:
    client.run(f.read())
