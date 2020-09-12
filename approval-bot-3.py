#!/usr/bin/env python3

import discord
import requests
import re
import json
import asyncio

client = discord.Client()
command_regex = re.compile('!kerberos ([a-zA-Z0-9_-]+)')
alt_command_regex = re.compile('!kerberos {([a-zA-Z0-9_-]+)}')
code_regex = re.compile('!code ([abcdef0-9]{4})')

deletion_queue = []

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    # Ignore  anything not from the front door channel.
    if (message.channel.name != 'front-door'):
        return

    # Our own messages we delete after 10 seconds
    elif message.author == client.user:
        deletion_queue.append((message, 10))
        return

    else:
        deletion_queue.append((message, 10))
        m = command_regex.match(message.content)
        
        if m is None:
            m = alt_command_regex.match(message.content)

        if m is not None:
            print('Requesting an email for %s %s' % (message.author, m[1]))
            requests.get('http://busy-beavers-community.com/approval/request', params={
                'kerb': m[1],
                'discord_id': message.author.id,
                'discord_name': str(message.author),
                'server': message.guild.id
            })
            await message.channel.send(
                '%s: We sent an email with your verification code to %s@mit.edu. The email will be from front-door@busy-beavers-community.com. Make sure to check your spam folder!\n\nOnce you get the email, send a message to this channel with the text `!code {your code}` (with no curly braces, like `!code 3a92`).\n\nIf you do not get the email within 5 minutes (or encounter any other trouble), email us at busybeavers@mit.edu from your MIT email with your Discord username and we\'ll add you manually.'
                % (message.author, m[1]))
        else:
            m = code_regex.match(message.content)

            if m is not None:
                response = requests.get('http://busy-beavers-community.com/approval/approve-by-discord/', params={
                    'discord_id': message.author.id,
                    'code': m[1]
                }).content.decode()
                print(response)
                response = json.loads(response)

                if response['success']:
                    await message.channel.send('%s: Success! If you\'re still not a Beaver, please email us.' % str(message.author))
                else:
                    await message.channel.send('%s: Your code was not correct. Make sure you\'ve copied and entered it correctly.' % str(message.author))

async def upkeep():
    global deletion_queue
    while True:
        try:
            approvals = json.loads(
                requests.get('http://busy-beavers-community.com/approval/get-outstanding').content
            )
            for approval_id, approval_server, approval_discord in approvals:
                print(approval_server, approval_discord)
                server = client.get_guild(approval_server)
                if server is None:
                    print('No server.')
                    continue
                member = server.get_member(approval_discord)
                if member is None:
                    print('No member.')
                    continue
                role = discord.utils.get(server.roles, name='Beavers')
                if role is None:
                    print('No role.')
                    continue
                print('Successfully adding role to member', member)
                await member.add_roles(role)

                requests.get('http://busy-beavers-community.com/approval/confirm', params={
                    'id': approval_id
                })
            new_deletion_queue = []
            for message, timer in deletion_queue:
                try:
                    if timer <= 0:
                        print('Deleting message', message.content)
                        await message.delete()
                    else:
                        new_deletion_queue.append((message, timer - 1))
                except Exception as e:
                    print(e)
            deletion_queue = new_deletion_queue
        except Exception as e:
            print(e)
        await asyncio.sleep(1)

client.loop.create_task(upkeep())
with open('approval-bot-token.txt') as f:
    token = f.read()
    client.run(token)
