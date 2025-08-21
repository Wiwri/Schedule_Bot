import os
import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import pytz

intents = discord.Intents.default()
intents.message_content = True  # also enable this in the Developer Portal

bot = commands.Bot(command_prefix="!", intents=intents)

# In-memory store (use a DB later if you want persistence)
scheduled_matches = []

@bot.event
async def on_ready():
    print(f"{bot.user} is online!")

async def schedule_reminder(channel, player1, player2, wait_seconds):
    await asyncio.sleep(wait_seconds)
    await channel.send(
        f"🔔 Reminder! {player1.mention} vs {player2.mention}, "
        f"your chess match is starting now. Please meet on Lichess!"
    )

@bot.command()
async def schedule(ctx, opponent: discord.Member, match_time: str, timezone: str = "UTC"):
    """
    Schedule a match at a specific local time.
    Usage: !schedule @opponent 20:30 Asia/Karachi
    """
    try:
        hh, mm = map(int, match_time.split(":"))
    except ValueError:
        await ctx.send("❌ Use HH:MM (24h). Example: `!schedule @user 20:30 Asia/Karachi`")
        return

    try:
        tz = pytz.timezone(timezone)
    except Exception:
        await ctx.send("❌ Unknown timezone. Try e.g. `UTC`, `Asia/Karachi`, `Europe/London`.")
        return

    now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
    local_now = datetime.now(tz)
    scheduled_local = tz.localize(datetime(local_now.year, local_now.month, local_now.day, hh, mm))
    if scheduled_local < local_now:
        scheduled_local += timedelta(days=1)

    scheduled_utc = scheduled_local.astimezone(pytz.UTC)
    wait_seconds = max(0, int((scheduled_utc - now_utc).total_seconds()))

    scheduled_matches.append({
        "player1": ctx.author,
        "player2": opponent,
        "time": scheduled_utc,
        "channel_id": ctx.channel.id
    })

    await ctx.send(
        f"📅 Match scheduled: {ctx.author.mention} vs {opponent.mention}\n"
        f"⏰ **{scheduled_local.strftime('%H:%M %Z')}** ({scheduled_utc.strftime('%H:%M UTC')})"
    )

    channel = ctx.channel
    bot.loop.create_task(schedule_reminder(channel, ctx.author, opponent, wait_seconds))

@bot.command()
async def reschedule(ctx, opponent: discord.Member, new_time: str, timezone: str = "UTC"):
    """
    Reschedule an existing match with the same opponent.
    Usage: !reschedule @opponent 21:00 Asia/Karachi
    """
    match = None
    for m in scheduled_matches:
        if (m["player1"].id == ctx.author.id and m["player2"].id == opponent.id) or \
           (m["player2"].id == ctx.author.id and m["player1"].id == opponent.id):
            match = m
            break

    if not match:
        await ctx.send("❌ No existing match with that opponent to reschedule.")
        return

    try:
        hh, mm = map(int, new_time.split(":"))
    except ValueError:
        await ctx.send("❌ Use HH:MM (24h). Example: `!reschedule @user 21:00 Asia/Karachi`")
        return

    try:
        tz = pytz.timezone(timezone)
    except Exception:
        await ctx.send("❌ Unknown timezone.")
        return

    now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
    local_now = datetime.now(tz)
    scheduled_local = tz.localize(datetime(local_now.year, local_now.month, local_now.day, hh, mm))
    if scheduled_local < local_now:
        scheduled_local += timedelta(days=1)

    scheduled_utc = scheduled_local.astimezone(pytz.UTC)
    wait_seconds = max(0, int((scheduled_utc - now_utc).total_seconds()))
    match["time"] = scheduled_utc

    await ctx.send(
        f"♻️ Match rescheduled: {ctx.author.mention} vs {opponent.mention}\n"
        f"⏰ **{scheduled_local.strftime('%H:%M %Z')}** ({scheduled_utc.strftime('%H:%M UTC')})"
    )

    channel = ctx.channel
    bot.loop.create_task(schedule_reminder(channel, ctx.author, opponent, wait_seconds))

@bot.command()
async def matches_list(ctx):
    if not scheduled_matches:
        await ctx.send("No matches scheduled.")
        return
    lines = []
    for m in scheduled_matches:
        lines.append(f"- <@{m['player1'].id}> vs <@{m['player2'].id}> at {m['time'].strftime('%H:%M UTC')}")
    await ctx.send("🎯 Upcoming Matches:\n" + "\n".join(lines))

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERROR: Set DISCORD_TOKEN env var in your host settings.")
else:
    bot.run(TOKEN)
