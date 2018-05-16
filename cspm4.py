import MySQLdb
import discord
from discord.ext import commands
import asyncio
from pokemonlist import pokemon, pokejson, pokejson_by_name
from cspm_utils import find_pokemon_id, get_team_id, get_team_name, get_team_color, get_egg_url, get_time
from config import admin_channel, log_channel2, admin_role_id, bot_channel, token, host, user, password, database, website, log_channel, instance_id, legendary_id, curfew
import datetime
import calendar
import time
import threading


bot = commands.Bot(command_prefix = '!') # Set prefix to !
bot.remove_command('help')
database = MySQLdb.connect(host,user,password,database)

cursor = database.cursor()

print('CSPM Started at ' + str(time.strftime('%I:%M %p on %m.%d.%y',  time.localtime(calendar.timegm(datetime.datetime.utcnow().timetuple())))) + ' for ' + str(instance_id))

async def incubate(ctx, gym_id, remaining_time):
    channel = discord.Object(id=bot_channel)
    current_time = datetime.datetime.utcnow()
    current_epoch_time = calendar.timegm(current_time.timetuple())
    sleep_time = remaining_time - current_epoch_time
    await bot.send_message(channel,'*Incubating Egg at Gym ID: ' + str(gym_id) + '. Will auto hatch in **' + str(sleep_time) + '** seconds.*')
    print('Auto-incubating Legendary egg at Gym ID: ' + str(gym_id) + '. Will auto hatch in ' + str(sleep_time) + ' seconds.')

    # Let's pause this thread until hatch time
    await asyncio.sleep(sleep_time)

    # Need to check if egg still exists before updating it and posting.  Otherwise, someone may have deleted it.
    cursor.execute("SELECT id FROM raids WHERE fort_id='" + str(gym_id)+ "' AND time_end>'" + str(current_epoch_time) + "';")
    raid_check = cursor.rowcount
    if ( raid_check == 1 ):
        cursor.execute("UPDATE raids SET pokemon_id='" + str(legendary_id) + "' WHERE fort_id='" + str(gym_id)+ "' AND time_end>'" + str(current_epoch_time) + "';")
        database.commit()

        cursor.execute("SELECT f.id, f.name, f.lat, f.lon, fs.team, r.level, r.pokemon_id, r.time_end FROM forts f JOIN raids r ON f.id=r.fort_id JOIN fort_sightings fs ON f.id = fs.fort_id WHERE f.id='" + str(gym_id) + "' AND r.time_end>'" + str(current_epoch_time) + "';")
        raid_data = cursor.fetchall()

        gym_id, gym_name, gym_lat, gym_lon, gym_team_id, raid_level, raid_pokemon_id, time_end = raid_data[0]
        await bot.send_message(channel,'Auto updated **Legendary Egg to ' + str(pokejson[str(raid_pokemon_id)]) + ' Raid' + '**' +
                      '\nGym: **' + str(gym_id) + ': ' + str(gym_name) + ' Gym' + '**' +
                      '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(time_end))) + '**')
        print('Legendary egg at Gym ID: ' + str(gym_id) + ' hatched into ' + str(pokejson[str(raid_pokemon_id)]))

        raid_embed=discord.Embed(
            title='**Level ' + str(raid_level) + ' ' + str(pokejson[str(raid_pokemon_id)]) + ' Raid**',
            description='Gym: **' + str(gym_name) + ' Gym**' +
                        '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(time_end))) + '**' +
                        '\nReported by: __' + str(ctx.message.author.name) + '__' +
                        '\n\nhttps://www.google.com/maps?q=loc:' + str(gym_lat) + ',' + str(gym_lon),
            color=get_team_color(gym_team_id)
        )
        thumbnail_image_url = 'https://bitbucket.org/anzmap/sprites/raw/HEAD/' + str(raid_pokemon_id) + '.png'
        raid_embed.set_thumbnail(url=thumbnail_image_url)
        await bot.send_message(discord.Object(id=log_channel), embed=raid_embed)
    else:
        print('Auto-hatch cancelled. Egg was not found, possibly deleted before hatch.')


#raid function
@bot.command(pass_context=True)
async def raid(ctx, raw_pokemon_name, raw_time_remaining, *, raw_gym_name):
    if ctx and ctx.message.channel.id == str(bot_channel):
        pokemon_name = str(raw_pokemon_name).capitalize()
        pokemon_id = find_pokemon_id(pokemon_name)
        remaining_time = get_time(int(raw_time_remaining))
        current_time = datetime.datetime.utcnow()
        current_hour = time.strftime('%H%M',  time.localtime(calendar.timegm(current_time.timetuple())))
        gym_team_id = '0'
#        raw_raid_level = 5
        database.ping(True)
        if(int(pokemon_id)== int(legendary_id)) or (pokemon_name == 'Egg'):
            raw_raid_level = '5'
        else:
            raw_raid_level = '4'

        raid_level = str(raw_raid_level)
        try:
            if ( (int(raw_time_remaining) < 1) or (int(raw_time_remaining) >= 60) ):
                raise Exception('Invalid time entered. Enter value between 1-60.')
            if ( curfew == 'true' ):
                if ( (int(current_hour) >= 1930) or (int(current_hour) <= 500) ):
                    raise Exception('Raid report is outside of the valid raid times. Raids can be reported between 5am - 7:30pm daily.')

            if raw_gym_name.isnumeric():
                cursor.execute("SELECT id, name, lat, lon FROM forts WHERE id LIKE '" + str(raw_gym_name) + "';")
            else:
                cursor.execute("SELECT id, name, lat, lon FROM forts WHERE name LIKE '%" + str(raw_gym_name) + "%';")
            gym_data = cursor.fetchall()
            count = cursor.rowcount
            raid_count = 0
            gym_names = ''
            for gym in gym_data:
                gym_names += str(gym[0]) + ': ' + gym[1] + ' (' + str(gym[2]) + ', ' + str(gym[3]) + ')\n'
                    
            # Single gym_id is returned so check if a raid exists for it
            if ( count == 1 ):
                gym_id = gym_data[0][0]
                gym_name = gym_data[0][1]
                cursor.execute("SELECT id, fort_id, time_end FROM raids WHERE fort_id='" + str(gym_id) + "' AND time_end>'" + str(calendar.timegm(current_time.timetuple())) + "';")
                raid_data = cursor.fetchall()
                raid_count = cursor.rowcount

                if (raid_count):
                    raid_id = raid_data[0][0]
                    raid_fort_id = raid_data[0][1]
                    raid_time_end = raid_data[0][2]
            elif ( count > 1 ):
                raise Exception('There are multiple gyms with the word "' + str(raw_gym_name) + '" in it:\n' + str(gym_names) + '\nBe a little more specific.')
            elif ( count == 0 ):
                raise Exception('No gym with the word "' + str(raw_gym_name) + '" in it. Use the !list command to list gyms available in the region.\n')
            else:
                raise Exception('Error. !raid "*gym_name*" *pokemon_name* *minutes_left*\n')

            if ( pokemon_name == "Egg" ):
                est_end_time = remaining_time + 2700
                
                if (raid_count):
                    cursor.execute("UPDATE raids SET level='" + str(raw_raid_level) + "', time_battle='" + str(remaining_time) + "', time_end='" + str(est_end_time) + "' WHERE id='" + str(raid_id)+ "';")
                    await bot.say('Updated **Level ' + str(raw_raid_level) + ' ' + str(pokemon_name) + '**' +
                                  '\nGym: **' + str(gym_id) + ': ' + str(gym_name) + ' Gym' + '**' +
                                  '\nHatches: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +
                                  '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(est_end_time))) + '**')
                else:
                    # Setup task to automatically hatch Legendary egg
                    if ( raw_raid_level == '5' ):
                        bot.loop.create_task(incubate(ctx, gym_id, remaining_time))
                    
                    cursor.execute("INSERT INTO raids("
                                   "id, external_id, fort_id , level, "
                                   "pokemon_id, move_1, move_2, time_spawn, "
                                   "time_battle, time_end, cp, reported_by)"
                                   "VALUES "
                                   "(null, null, " + str(gym_id) + ", "
                                   + str(raw_raid_level) + ", " + str(pokemon_id) + ", null, null, "
                                   "null, " + str(remaining_time) + ", " + str(est_end_time) + ", null, '" + str(ctx.message.author.name) + "');")
                    await bot.say('Added ' + str(pokemon_name) +
                                  '\nGym: **' + str(gym_name)  + '**' +
                                  '\nHatches: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +
                                  '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(est_end_time))) + '**' +
                                  '\nTime Left Until Hatch: **' + str(raw_time_remaining) + ' minutes**')
                    raid_embed=discord.Embed(
                        title='Hatch at: ' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))),
                        description='Gym: **' + str(gym_name) + '**'
                                    '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(est_end_time))) + '**' +
                                    '\nReported by: __' + str(ctx.message.author.name) + '__' +
                                    '\n\nhttps://www.google.com/maps?q=loc:' + str(gym_data[0][2]) + ',' + str(gym_data[0][3]),
                        color=get_team_color(gym_team_id)
                    )
                    thumbnail_image_url = get_egg_url(raw_raid_level)
                    raid_embed.set_thumbnail(url=thumbnail_image_url)
                    await bot.send_message(discord.Object(id=log_channel2), embed=raid_embed)
                    
                    print(str(ctx.message.author.name) + ' reported a ' + str(pokemon_name) + ' at ' + str(gym_id) +': ' + str(gym_name) + ' with ' + str(raw_time_remaining) + ' minutes left.')
            else:
                # Update Egg to a hatched Raid Boss
                if (raid_count):
                    cursor.execute("UPDATE raids SET pokemon_id='" + str(pokemon_id) + "', level='" + str(raw_raid_level) + "', time_battle='" + str(calendar.timegm(current_time.timetuple())) + "', time_end='" + str(remaining_time) + "' WHERE id='" + str(raid_id)+ "';")
                    await bot.say('Updated Egg to ' + str(pokemon_name) + ' Raid' +
                                  '\nGym: **' + str(gym_id) + ': ' + str(gym_name) + '**' +
                                  '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**')

                    raid_embed=discord.Embed(
                        title=str(pokemon_name) + ' Raid',
                        description='Gym: **' + str(gym_name) + '**' +
                                    '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +'\nReported by: __' + str(ctx.message.author.name) + '__' +
                                    '\n\nhttps://www.google.com/maps?q=loc:' + str(gym_data[0][2]) + ',' + str(gym_data[0][3]),
                        color=get_team_color(gym_team_id)
                    )
                    thumbnail_image_url = 'https://bitbucket.org/anzmap/sprites/raw/HEAD/' + str(pokemon_id) + '.png'
                    raid_embed.set_thumbnail(url=thumbnail_image_url)
                    await bot.send_message(discord.Object(id=log_channel), embed=raid_embed)

                    print(str(ctx.message.author.name) + ' updated ' + str(raw_raid_level) + ' Egg to ' + str(pokemon_name) + ' Raid at ' + str(gym_name) + ' with ' + str(raw_time_remaining) + ' minutes left.')

                else:
                    cursor.execute("INSERT INTO raids("
                                   "id, external_id, fort_id , level, "
                                   "pokemon_id, move_1, move_2, time_spawn, "
                                   "time_battle, time_end, cp, reported_by)"
                                   "VALUES "
                                   "(null, null, " + str(gym_id) + ", "
                                   + str(raw_raid_level) + ", " + str(pokemon_id) + ", null, null, "
                                   "null, " + str(calendar.timegm(current_time.timetuple())) + ", " + str(remaining_time) + ", null, '" + str(ctx.message.author.name) + "');")
                    await bot.say('Added ' + str(pokemon_name) + ' Raid' +
                                  '\nGym: **' + str(gym_id) + ': ' + str(gym_name) + '**' +
                                  '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +
                                  '\nTime Left: **' + str(raw_time_remaining) + ' minutes**')

                    raid_embed=discord.Embed(
                        title=str(pokemon_name) + ' Raid',
                        description='Gym: **' + str(gym_name) + '**' +
                                    '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +
                                    '\nReported by: __' + str(ctx.message.author.name) + '__' +
                                    '\n\nhttps://www.google.com/maps?q=loc:' + str(gym_data[0][2]) + ',' + str(gym_data[0][3]),
                        color=get_team_color(gym_team_id)
                    )
                    thumbnail_image_url = 'https://bitbucket.org/anzmap/sprites/raw/HEAD/' + str(pokemon_id) + '.png'
                    raid_embed.set_thumbnail(url=thumbnail_image_url)
                    await bot.send_message(discord.Object(id=log_channel), embed=raid_embed)
                    print(str(ctx.message.author.name) + ' reported a ' + str(pokemon_name) + ' raid at ' + str(gym_name) + ' with ' + str(raw_time_remaining) + ' minutes left.')
                    
            # Check if fort_id exists in fort_sightings.  If so update the entry, otherwise enter as a new entry.
            cursor.execute("SELECT id, fort_id, team FROM fort_sightings WHERE fort_id='" + str(gym_id) + "';")
            fs_count = cursor.rowcount
            if (fs_count):
                cursor.execute("UPDATE fort_sightings SET team='" + str(gym_team_id) + "' WHERE fort_id='" + str(gym_id) + "';")
            else:
                cursor.execute("INSERT INTO fort_sightings(fort_id, team, last_modified) VALUES (" + str(gym_id) + ", " + str(gym_team_id) + ", " + str(calendar.timegm(current_time.timetuple())) + ");")

            database.commit()

        except Exception as e:
            message = e.args[0]
            await bot.say(message)
            print(message)

        except:
            database.rollback()

@raid.error
async def handle_missing_raid_arg(ctx, error):
    await bot.say('**Error** - Missing arguments. !raid  "*gym_name*"  *pokemon_name*  *minutes_left*\n')

@bot.command(pass_context=True)
async def list(ctx, *, raw_gym_name):
  
    if ctx and ( (ctx.message.channel.id == str(bot_channel)) or ((ctx.message.channel.id == str(admin_channel)))):
        database.ping(True)
        try:
            if raw_gym_name.isnumeric():
                cursor.execute("SELECT id, name, lat, lon FROM forts WHERE id LIKE '" + str(raw_gym_name) + "';")
            else:
                cursor.execute("SELECT id, name, lat, lon FROM forts WHERE name LIKE '%" + str(raw_gym_name) + "%';")
            data = cursor.fetchall()
            count = cursor.rowcount
            gym_names = ''
            for gym in data:
                gym_names += str(gym[0]) + ': ' + gym[1] + ' <https://www.google.com/maps?q=loc:' + str(gym[2]) + ',' + str(gym[3]) + '>'
            await bot.say('There are ' + str(count) + ' gyms with the word(s) "' + str(raw_gym_name) + '" in it:\n' + str(gym_names))
            database.commit()
        except:
            database.rollback()
            await bot.say('No gym with the word "' + str(raw_gym_name) + '" in it OR too many to list. Try narrowing down your search.')

@list.error
async def handle_missing_arg(ctx, error):
    try:
        cursor.execute("SELECT id, name, lat, lon FROM forts;")
        data = cursor.fetchall()
        count = cursor.rowcount
        gym_names = ''
        for gym in data:
            gym_names += str(gym[0]) + ': ' + gym[1] + '<https://www.google.com/maps?q=loc:' + str(gym[2]) + ', ' + str(gym[3]) + '>\n'
        database.commit()
        await bot.say('There are ' + str(count) + ' gyms in the region:\n' + str(gym_names))
    except:
        database.rollback()
        await bot.say('No gyms found OR too many to list.  Try narrowing down your search.')

@bot.command(pass_context=True)
async def deleteraid(ctx, fort_id):
    if ctx and ctx.message.channel.id == str(bot_channel):
        try:
            database.ping(True)
            current_time = datetime.datetime.utcnow()
            valid_user_query = "SELECT fort_id FROM raids WHERE fort_id='" + str(fort_id) + "' AND time_end>'" + str(calendar.timegm(current_time.timetuple())) + "' AND reported_by='" + str(ctx.message.author.name) +  "';"
            print(str(valid_user_query) + " : ")
            cursor.execute(valid_user_query)
            valid_user_count = cursor.rowcount
            print("count - " + str(valid_user_count) + " : ")
            # Check if command is coming from original raid reporter or an admin
            if ( (valid_user_count == 0) and (admin_role_id not in [role.id for role in ctx.message.author.roles]) ):
                raise Exception('Raid can only be deleted by original reporter or an Admin.')

            if fort_id.isnumeric():
                print("fort id" + str(fort_id) + " : ")
                cursor.execute("SELECT id, name, lat, lon FROM forts WHERE id='" + str(fort_id) + "';")
                gym_data = cursor.fetchall()
                count = cursor.rowcount
                fort_id = gym_data[0][0]
                gym_name = gym_data[0][1]
                gym_lat = gym_data[0][2]
                gym_lon = gym_data[0][3]
                # Gym id is valid and returned 1 result
                
                if ( count == 1 ):
                    print(str(fort_id) + ":" + str(gym_name))
                    cursor.execute("SELECT id, fort_id, level, pokemon_id, time_battle, time_end FROM raids WHERE fort_id='" + str(fort_id) + "' AND time_end>'" + str(calendar.timegm(current_time.timetuple())) + "';")
                    raid_data = cursor.fetchall()
                    raid_count = cursor.rowcount
						
                    raid_id, raid_fort_id, raid_level, raid_pokemon_id, raid_time_battle, raid_time_end = raid_data[0]
#                    print("raid data " + raid_pokemon_id)
                    if ( raid_pokemon_id == 0 ):
                        raid_pokemon_name = 'Egg (Umkonwn)'
                        thumbnail_image_url = get_egg_url(raid_level)
                    else:
                        raid_pokemon_name = pokejson[str(raid_pokemon_id)]
                        thumbnail_image_url = 'https://bitbucket.org/anzmap/sprites/raw/HEAD/' + str(raid_pokemon_id) + '.png'

                    await bot.say('**Deleted Raid**' +
                                  '\nGym: **' + str(fort_id) + ': ' + str(gym_name) + '**' +
                                  '\nPokemon: ** ' + str(raid_pokemon_name).capitalize() + '**' +
                                  '\nStart\Hatch Time: **' + str(time.strftime('%I:%M %p',  time.localtime(raid_time_battle))) + '**' +
                                  '\nEnd Time: **' + str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + '**')
                    delete_raid_query = "DELETE FROM raids WHERE fort_id='" + str(fort_id) + "' AND time_end>'" + str(calendar.timegm(current_time.timetuple())) + "';"
                    cursor.execute(delete_raid_query)

                    gym_team_id = 0
                    raid_embed=discord.Embed(
                        title='~~' + str(raid_pokemon_name).capitalize() + '~~ **RAID DELETED**',
                        description='Gym: ~~' + str(gym_name) + ' Gym~~' +
                                    '\nRaid Ends: ~~' + str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + '~~' +
                                    '\nDeleted by: __' + str(ctx.message.author.name) + '__',
                        color=get_team_color(gym_team_id)
                    )
                    raid_embed.set_thumbnail(url=thumbnail_image_url)
                    await bot.send_message(discord.Object(id=log_channel), embed=raid_embed)

                    print(str(ctx.message.author.name) + ' deleted raid at ' + str(fort_id) + ': ' + str(gym_name) + '.')
                else:
                    raise Exception('Gym ID provided is not valid.')
        
            else:
                raise Exception('Enter the numeric ID of the gym where the raid is located.')

            database.commit()
        except Exception as e:
            message = e.args[0]
            await bot.send_message(discord.Object(id=bot_channel), message)
        except:
            database.rollback()
            await bot.say('Raid at **' + str(fort_id) + ': ' + str(gym_name) +  '** does not exist.')

@bot.command(pass_context=True)
async def activeraids(ctx):
    if ctx and ctx.message.channel.id == str(bot_channel):
        database.ping(True)
        current_time = datetime.datetime.utcnow()
        try:
            cursor.execute("SELECT f.id, f.name, r.level, r.pokemon_id, r.time_battle, r.time_end FROM forts f JOIN raids r ON f.id=r.fort_id WHERE r.time_end>'" + str(calendar.timegm(current_time.timetuple())) + "' ORDER BY r.level DESC, r.time_end;")
            raid_data = cursor.fetchall()
            raid_count = cursor.rowcount

            await bot.say('There are currently ' + str(raid_count) + ' active raids.')
            active_raids_l5 = ''
            active_raids_l4 = ''
            active_raids_l3 = ''
            active_raids_l2 = ''
            active_raids_l1 = ''
            for raid in raid_data:
                fort_id, gym_name, raid_level, raid_pokemon_id, raid_time_battle, raid_time_end = raid
                if ( raid_pokemon_id == 0 ):
                    raid_pokemon_name = 'Egg - Legendary'
                else:
                    raid_pokemon_name = pokejson[str(raid_pokemon_id)]

                if ( raid_level == 5 ):
                    active_raids_l5 += str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + ' : ' + str(raid_pokemon_name) + ' : ' + str(gym_name) + ' Gym (' +  str(fort_id) + ')\n'
                elif ( raid_level == 4 ):
                    active_raids_l4 += str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + ' : ' + str(raid_pokemon_name) + ' : ' + str(gym_name) + ' Gym (' +  str(fort_id) + ')\n'
                elif ( raid_level == 3 ):
                    active_raids_l3 += str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + ' : ' + str(raid_pokemon_name) + ' : ' + str(gym_name) + ' Gym (' +  str(fort_id) + ')\n'
                elif ( raid_level == 2 ):
                    active_raids_l2 += str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + ' : ' + str(raid_pokemon_name) + ' : ' + str(gym_name) + ' Gym (' +  str(fort_id) + ')\n'
                else:
                    active_raids_l1 += str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + ' : ' + str(raid_pokemon_name) + ' : ' + str(gym_name) + ' Gym (' +  str(fort_id) + ')\n'

            raid_report = ''
            if ( active_raids_l5 != '' ):
                raid_report += '**Legendary**\n' + active_raids_l5
            if ( active_raids_l4 != '' ):
                raid_report += '\n**Other**\n' + active_raids_l4
            if ( active_raids_l3 != '' ):
                raid_report += '\n**LEVEL 3**\n' + active_raids_l3
            if ( active_raids_l2 != '' ):
                raid_report += '\n**LEVEL 2**\n' + active_raids_l2
            if ( active_raids_l1 != '' ):
                raid_report += '\n**LEVEL 1**\n' + active_raids_l1

            if ( raid_report != '' ):
                await bot.say('**Active Raids**\n' + str(raid_report))

            database.commit()
        except:
            database.rollback()
            await bot.say('There are no active raids.')

@bot.command(pass_context=True)
async def updategymname(ctx, fort_id, new_gym_name):
    if ( admin_channel == 'disabled'):
        await bot.say('The !updategymname command is disabled')
        pass
    else:
        database.ping(True)
        if ctx and ctx.message.channel.id == str(admin_channel):
            try:
                cursor.execute("SELECT id, name FROM forts WHERE id='" + str(fort_id) + "';")
                gym_data = cursor.fetchall()
                gym_count = cursor.rowcount

                if ( gym_count == 1 ):
                    fort_id, gym_name = gym_data[0]

                    cursor.execute("UPDATE forts SET name='" + str(new_gym_name) + "' WHERE id='" + str(fort_id) + "';")
                    cursor.execute("SELECT name FROM forts WHERE id='" + str(fort_id) + "';")
                    updated_gym_data = cursor.fetchall()
                    updated_gym_name = updated_gym_data[0][0]
                    await bot.say('Changed the name of:\n__' + str(fort_id) + ': ' + str(gym_name) + '__\nto:\n**' + str(fort_id) + ': ' + str(updated_gym_name) + '**')
                else:
                    await bot.say('There are multiple gyms with gym_id: ' + str(fort_id) + '.  Delete all of the duplicate gym_ids before proceeding.')
                database.commit()
            except:
                database.rollback()

@updategymname.error
async def handle_missing_fort_id(ctx, error):
    if ctx:
        try:
            await bot.say('Missing arugment(s).\n`!updategymname <gym_id> <new_gym_name>`')
        except:
            await bot.say('Exception reached.')

@bot.command(pass_context=True)
async def help(ctx):
    if ctx and ctx.message.channel.id == str(bot_channel):
        help_embed1=discord.Embed(
            title='Cloud2 - Raid reporting bot modified from RobTwoThree/cspm',
            description='**Report a raid:**\n'
                    '```!raid <gym_name> <pokemon> <minutes remaining>\n'
                    'Example: !raid "Liberty Way" absol 30\n'
                    'Example: !raid Liberty absol 30`\n'
                    'The full gym name is not required.\n'
                    '*To report a Legendary egg type "egg" in pokemon field. Legendary Eggs will automatically hatch.*```\n'
                    '**List Gyms:**\n'
                    '`!list "<gym_name>" searches for a gym and location`\n'
                    'Example: `!list liberty`\n'
                    '**List Active Raids:**\n'
                    'Generate a list of all active raids.\n'
                    '`!activeraids lists all active raids'
                    '**Delete Raids**\n'
                    'This will allow you to delete a raid by gym id\n'
                    '`!deleteraid <gym_id>`\n'
                    'Example: `!deleteraid 55`\n\n',
            color=3447003
        )
        help_embed2=discord.Embed(
            title='Cloud2 CSPM Help - Administrative Commands',
            description='**Modify Gym Name** (*only available on an admin channel*)\n'
                    'Use this command to modify a gym name to help with identifying gyms with the same name, like Starbucks.  Use in conjunction with '
                    '!list to help you identify the gym_id.\n'
                    '`!updategymname 55 <new name of gym>`\n'
                    'Example: `!updategymname 55 "Starbucks Thomasville rd.`\n\n',
            color=3447003
        )
        await bot.say(embed=help_embed1)
        if ( admin_channel == 'disabled'):
            pass
        else:
            await bot.say(embed=help_embed2)

bot.run(token)
