import MySQLdb
import discord
from discord.ext import commands
import asyncio
#from pokemonlist import pokemon, pokejson, pokejson_by_name
from cspm_utils import get_time
from config import admin_channel, log_channel2, admin_role_id, bot_channel, token, host, user, password, database, log_channel, instance_id
import datetime
import calendar
import time
import threading

bot = commands.Bot(command_prefix = '!') # Set prefix to !

database = MySQLdb.connect(host,user,password,database)

cursor = database.cursor()

print('mysql translator running ' + str(time.strftime('%I:%M %p on %m.%d.%y',  time.localtime(calendar.timegm(datetime.datetime.utcnow().timetuple())))) + ' for ' + str(instance_id))

@bot.group(pass_context=True)
async def msql(ctx):
    if ctx.invoked_subcommand is None:
        await bot.say('Invalid msql command.')

@msql.command()
async def select(raw_table, raw_field_list, raw_condition):
        sql_table = str(raw_table)
        field_list = str(raw_field_list)
        sql_condition = str(raw_condition)
        current_time = datetime.datetime.utcnow()
        current_hour = time.strftime('%H%M',  time.localtime(calendar.timegm(current_time.timetuple())))
        database.ping(True)
 #       print (sql_state + ":" + server)
        try:    
            strsql = "SELECT " + str (field_list) + " FROM " + str(sql_table) + " WHERE " + str(sql_condition) + " limit 10;"
#                cursor.execute(strsql)
#                sql_data = cursor.fetchall()
#                count = cursor.rowcount
            await bot.say(strsql)
#            sql_count = 0
#            sql_result = ''
#            for sql in sql_result:
#                sql_result += str(sql[0]) + ': ' + sql[1] + ' (' + str(gym[2]) + ', ' + str(gym[3]) + ')\n'
                    
        except Exception as e:
            message = e.args[0]
            await bot.say(message)
            print(message)

        except:
            database.rollback()			
@select.error
async def handle_missing_table(ctx, error):
    await bot.say('Missing arguments. !msql select <table> <column name> <condition>\n')

@msql.command()
async def update(raw_table, raw_field_list, raw_values, raw_condition):
        sql_table = str(raw_table)
        field_list = str(raw_field_list)
        str_values = raw_values
        sql_condition = str(raw_condition)
        current_time = datetime.datetime.utcnow()
        current_hour = time.strftime('%H%M',  time.localtime(calendar.timegm(current_time.timetuple())))
        database.ping(True)
 #       print (sql_state + ":" + server)
        try:    
            strsql = "UPDATE " + str (sql_table) + " SET (" + str(field_list) + ") VALUES (" + str(str_values) + ") WHERE " + str(sql_condition) + ";"
#                cursor.execute(strsql)
#                sql_data = cursor.fetchall()
#                count = cursor.rowcount
            await bot.say(strsql)
#            sql_count = 0
#            sql_result = ''
#            for sql in sql_result:
#                sql_result += str(sql[0]) + ': ' + sql[1] + ' (' + str(gym[2]) + ', ' + str(gym[3]) + ')\n'
                    
        except Exception as e:
            message = e.args[0]
            await bot.say(message)
            print(message)

        except:
            database.rollback()			
@update.error
async def handle_missing_table(ctx, error):
    await bot.say('Missing arguments. !msql update <table> <column name> <value> <condition>\n')	
	
bot.run(token)