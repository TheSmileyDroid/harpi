# Harpi

This is the repository for Harpi, the most complete Discord Bot out there to use when making TTRPG sessions on Discord. The goal is to have music, tts, dice, map, a web ui for managing every aspect and actions of the bot, connection to obsidian and much more features to allow the GM to make the most of the session.

## Current status

Most of the basics of the bot are complete (music playing, dice rows, etc.), but we need to implment the more complex stuff. However, it needs a greate refactor to change from a svelte ui to a htmx ui. There is no current tests.

## Some thoughts from the author (SmileyDroid/Sorriso/Gabriel)

This is a big project. I wouldn't want to say it is finished so soon. I think it has a lot of potencial to be a amazing alternative to others Virtual Tabletops (VTTs). An free and opensource alternative that gives you the possibility of playing with your friends over any discord server. Even if normally other VTTs have maps and are built for strategy or dungeon crawl games, this project focuses on the narrative feel of rpg games and it means that we do not use maps because usually we focus on the imagination of the players over the scene. However, to do this, we need that all the other aspects of the game have a complete experience, from the music and the most of tecniques to playing sounds to an easy character sheet management and dice rolls.

This is a project different of anything I already seen. So do not go with the flow of existing solutions. Explore ideas.

Quick glossary:

- Bot/Harpi: This is the bot over discord, the interface we will be using to comunicate to discord.
- UI/Harpi Panel: This is the Web UI that contains options and presets for running games and playing music over the discord interface.
- me: This is SmileyDroid or Sorriso or Gabriel. The creator of this bot.

### Style

The style of UI and features should follow a Retro aesthetic based on old computers, featuring yellowish lighting that follows the style of TVA's *Tempad*.

### Don't be afraid

When planning, do not be afraid to suggest seemingly insane solutions. For example, rewriting an entire discord lib from scratch to be able to do things unseen before. Seems insane, but it's absolutely doable with modern tools.

You can add more libs along the way, but libs that are so simple that don't have a lot of users could be implemented on the project. 

### Fight for the "obvious" solution

We should avoid being clever and doing things because they seem smart. We want everything we build to be so obvious it feels kind of stupid.

When one of us prompts you, never hesitate to push back and suggest ways we could make things more obvious. Note that "simple" and "obvious" are not always aligned, sometimes the "obvious" solution is more complex.

## Some general rules

- When making a new feature make tests for it.
- Always use "make check" bash command at the root to check for lint, format, type, vulture errors.
- Use modern tools like uv.