import os
import discord
import asyncio #More time
from datetime import datetime, timedelta #Time
from dotenv import load_dotenv #Enviromental Variable
import pytz #Timezone
import json #Stores event data


load_dotenv()

TOKEN = os.environ.get("TOKEN_KEY")
JSON_FILE_PATH = "events.json"

intents = discord.Intents.default()
bot = discord.Bot(intents = intents)

events = {}
def load_events():
    print("starting load") 
    try:
        with open(JSON_FILE_PATH, "r") as f:
            loaded_events = json.load(f)
            #event_details takes in dictionary of the details
            for event_id, event_details in loaded_events.items():
                #Converts iso formatted date back into datetime object with timezone
                event_details["time"] = datetime.fromisoformat(event_details["time"]).replace(tzinfo=pytz.timezone("America/New_York"))
            print("finished load")
            return loaded_events
    except(FileNotFoundError, json.JSONDecodeError):
        print ("Error Decoding Saved Events JSON")
        return {}
    

events = load_events()


def save_events():
    print(f"Saving, {events}")
    saved_events = {
        event_id: {
            "time": event_details["time"].isoformat(),
            "channel": event_details["channel"],
            "user": event_details["user"],
            "message": event_details["message"]
        }
        for event_id, event_details in events.items()

    }
    
    try:
        with open(JSON_FILE_PATH, "w+") as f:
            json.dump(saved_events, f, indent=4)
    except Exception as e:
        print(f"Error saving events: {e}") 


def calculate_reminders(event_time):
    return {
        "two_hours": event_time-timedelta(hours=2),
        "twenty_minutes": event_time-timedelta(minutes=20),
        "five_minutes": event_time-timedelta(minutes=5)
    }

async def send_reminder(channel, message):
    await channel.send(message)


async def schedule_reminder(event_time, channel, message, role_ids):
    reminders = calculate_reminders(event_time)

    now = datetime.now(pytz.timezone('America/New_York'))

    role_mentions = " "
    formatted_role_mentions = []
    for role_id in role_ids:
        mention_string = f"<@&{role_id}>"
        formatted_role_mentions.append(mention_string)
    role_mentions = ", ".join(formatted_role_mentions)

    #Two hour announcement
    two_hour_announcement = (reminders['two_hours'] - now).total_seconds()
    if two_hour_announcement > 0:
        await asyncio.sleep(two_hour_announcement)
        await send_reminder(channel, f"{message} {role_mentions}")

    #Twenty minute announcement
    twenty_minute_announcement = (reminders['twenty_minutes'] - now).total_seconds()
    if twenty_minute_announcement > 0:
        await asyncio.sleep(twenty_minute_announcement)
        await send_reminder(channel, f"{message} {role_mentions}")

    #Five minute announcement
    five_minute_announcement = (reminders['five_minutes'] - now).total_seconds()
    if five_minute_announcement > 0:
        await asyncio.sleep(five_minute_announcement)
        await send_reminder(channel, f"{message} {role_mentions}")


@bot.slash_command(name="announce", description="Schedule an event and get reminders periodically before event occurs.")
async def announce(ctx, day: int, month: int, time: str, message: str, roles: str):
    #print(events)
    await ctx.respond("Processing your request...")
    try:
        hour, minute = map(int, time.split(":"))
        timezone = pytz.timezone('America/New_York')
        now = datetime.now(timezone)
        
        event_time = timezone.localize(datetime(year=now.year, month=month, day=day, hour=hour, minute=minute))

        if event_time < now:
            await ctx.send("Event time has already passed.")
            return
        
        event_id = f"{ctx.user.id}_{event_time.timestamp()}"

        role_ids = []
        role_mentions = roles.split(",")
        for role in role.mentions:
            stripped_role = role.strip()
            if stripped_role and stripped_role.startswith("<@&") and stripped_role.endswith(">"):
                role_ids.append(stripped_role[3:-1])

        events[event_id] = {
            "time": event_time,
            "channel": ctx.channel.id,
            "user": ctx.user.name,
            "message": message,
            "roles": role_ids
        }

        save_events()
        
        await ctx.send(f"Event **[{event_id}]** scheduled for *{event_time.strftime('%Y-%m-%d %H:%M %Z')}*.")
        
        await schedule_reminder(event_time, ctx.channel, message, role_ids)

    except ValueError:
        await ctx.send("Invalid input. Please use the format: `/announce day month hour:minute`")
    

@bot.slash_command(description="Deletes event.")
async def deleteannouncement(ctx, event_id: str):
    await ctx.respond("Processing your request...")
    if event_id in events:
        del events[event_id]
        save_events()
        await ctx.send(f"Event **{event_id}** has been deleted.")
    else:
        await ctx.send(f"Event **{event_id}** does not exist.")


@bot.slash_command(description="Edits event.")
async def editannouncement(ctx, event_id: str, day: int, month: int, time: str, message: str):
    await ctx.respond("Processing your request...")
    if event_id in events:
        try:
            hour, minute = map(int, time.split(":"))
            timezone = pytz.timezone("America/New_York")
            now = datetime.now(timezone)
            event_time = timezone.localize(datetime(year=now.year, month=month, day=day, hour=hour, minute=minute))

            if event_time < now:
                await ctx.send("Updated event time has already passed.")
                return

            events[event_id]["time"] = event_time
            await ctx.send(f"Event **{event_id}** has been updated to *{event_time.strftime('%Y-%m-%d %H:%M %Z')}*")
        except:
            await ctx.send(f"Invalid input. Please use the format: `hour:minute` in military time.")

        save_events()
    else:
        await ctx.send(f"Event {event_id} does not exist")


@bot.slash_command(description="Lists all upcoming events.")
async def listannouncements(ctx):
    await ctx.respond("Processing your request...")
    if not events:
        await ctx.send("There are no scheduled events.")
        return
    
    event_list = []
    for event_id, event_details in events.items():
        event_time = event_details["time"].strftime('%Y-%m-%d %H:%M %Z')
        custom_message = event_details.get("message", "No Message Found")
        
        roles = []
        for role_id in event_details.get("roles", []):
            role_mention = f"<@&{role_id}>"
            roles.append(role_mention)
        
        roles_string = " ,".join(roles)

        event_list.append(f"Event ID: **{event_id}**, Time: {event_time}, User: {event_details['user']}, Message: '{custom_message}', Roles: {roles}.")

    message = "\n".join(event_list)
    await ctx.send(f"Scheduled Events:\n {message}")


@bot.event
async def on_ready():
    print(f'{bot.user} is now running.')

    for event_id, event_details in events.items():
        event_time = event_details["time"]
        now = datetime.now(pytz.timezone('America/New_York'))

        if event_time > now:
            channel = bot.get_channel(event_details["channel"])
            role_ids = event_details.get("roles", [])
            asyncio.create_task(schedule_reminder(event_time, channel, event_details["message"], role_ids))
        else:
            print(f"Event {event_id} has passed.")

@bot.command(description="Gives bot ping.")
async def ping(ctx):
    await ctx.respond(f"Latency is {bot.latency}")


@bot.command(description="Gives time.")
async def time(ctx):
    await ctx.respond(datetime.now(pytz.timezone('America/New_York')))


bot.run(TOKEN)






# //Mentions, roles, meeting events, delete events
# //5 minute before, 30 minutes, and 2 hours before
# //Commands that lists all upcoming meetings

# //Token from enviromental variables
#     -Make sure to ingore env file when uploading

# //Only client event should be for making events

# //Blueprint Announcments