import config
import messages
import telebot
from telebot import types
import vk_api
from vk_api.keyboard import VkKeyboard
from pymessenger import Button
from pymessenger.bot import Bot
import gspread
import datetime
import re
import time
import random
import sys
import sqlite3 as sql
import json
import requests

# Telegram bot
bot = telebot.TeleBot(config.tg_token, skip_pending=True)


def send_msg_to_tg(message_data):
    bot.send_message(config.group_id, message_data)


def get_email_from_message(message):




    lines = message.split('\n')
    email = ""

    for line in lines:
        if line.startswith("email:"):
            email = line.split(":")[1].strip()
            break

    return email


def send_msg_to_tg(message_data):
    bot.send_message(config.group_id, message_data)


def get_email_from_message(message):
    lines = message.split('\n')
    email = ""

    for line in lines:
        if line.startswith("email:"):
            email = line.split(":")[1].strip()
            break

    return email


def replace_endl(text):
    return text.replace('\n', "")
