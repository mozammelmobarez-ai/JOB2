#!/usr/bin/env python3
"""
🤖 ربات جستجوی کار هوشمند - نسخه فیکس شده
بدون nest_asyncio - سازگار با Python 3.13
"""

import os
import asyncio
import logging
import sys
import re
from datetime import datetime
from typing import List, Dict, Optional

# ===================== CONFIG =====================
BOT_TOKEN = "8025706175:AAHNqM-dW5ZVLpzXVkc0LA1ovqVTumcnddU"
GEMINI_API_KEY = "AQ.Ab8RN6ISMMWB0Owdrx5sOBsNmMLH5JNHtc3sdcN0KzfgK4x-jQ"
SCAN_INTERVAL = 18000  # 5 ساعت (ثانیه)

os.environ['TELEGRAM_BOT_TOKEN'] = BOT_TOKEN

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, ContextTypes, filters
)

# Fix for Python 3.13 compatibility
import asyncio
if hasattr(asyncio, 'ThreadedChildWatcher'):
    asyncio.set_child_watcher(asyncio.ThreadedChildWatcher())

# ===================== LOGGING =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ===================== IMPORTS =====================
from database import Database
from job_scanner import JobScanner
from gemini_ai import GeminiMatcher

db = Database()
scanner = JobScanner()
ai_matcher = GeminiMatcher(GEMINI_API_KEY)

# ===================== KEYBOARDS =====================

def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🔍 جستجوی فوری"), KeyboardButton("📋 کانال‌ها")],
        [KeyboardButton("👤 پروفایل من"), KeyboardButton("⏰ زمان‌بندی")],
        [KeyboardButton("➕ کانال جدید"), KeyboardButton("🔄 آمار")],
        [KeyboardButton("⚙️ تنظیمات")]
    ], resize_keyboard=True)


def profile_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ ویرایش بیوگرافی", callback_data="edit_bio")],
        [InlineKeyboardButton("👁️ نمایش پروفایل", callback_data="show_profile")],
        [InlineKeyboardButton("🗑️ پاک کردن", callback_data="clear_profile")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ])


def channels_keyboard(channels: list):
    buttons = []
    for ch in channels[:8]:
        buttons.append([InlineKeyboardButton(f"❌ {ch}", callback_data=f"del_ch_{ch}")])
    buttons.extend([
        [InlineKeyboardButton("➕ کانال جدید", callback_data="add_channel_inline")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ])
    return InlineKeyboardMarkup(buttons)


def time_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕐 1 ساعت", callback_data="t_3600")],
        [InlineKeyboardButton("🕐 3 ساعت", callback_data="t_10800")],
        [InlineKeyboardButton("🕐 5 ساعت", callback_data="t_18000")],
        [InlineKeyboardButton("🕐 12 ساعت", callback_data="t_43200")],
        [InlineKeyboardButton("🕐 24 ساعت", callback_data="t_86400")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ])


def settings_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 مد AI", callback_data="ai_model")],
        [InlineKeyboardButton("🔕 حالت سکوت", callback_data="set_quiet")],
        [InlineKeyboardButton("🗑️ پاکسازی", callback_data="clear_data")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ])


# ===================== HANDLERS =====================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ربات"""
    uid = str(update.effective_user.id)
    
    if not db.get_bio(uid):
        db.save_bio(uid, "")
    
    welcome = """
🤖 <b>ربات جستجوی کار هوشمند</b>

🎯 این ربات با هوش مصنوعی Gemini کار پیدا می‌کنه!

📝 <b>نحوه کار:</b>
1️⃣ اول بیوگرافی‌تون رو بفرستید
2️⃣ کانال‌های کاریابی رو اضافه کنید
3️⃣ ربات هر 5 ساعت خودکار جستجو می‌کنه
4️⃣ شغل‌های مرتبط رو براتون می‌فرسته

👇 از دکمه‌های زیر استفاده کنید:
"""
    
    await update.message.reply_text(welcome, parse_mode='HTML', reply_markup=main_keyboard())


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش دکمه‌ها"""
    text = update.message.text
    uid = str(update.effective_user.id)
    
    # اسکن فوری
    if text == "🔍 جستجوی فوری":
        await update.message.reply_text("🔍 در حال تحلیل با AI... ⏳")
        
        channels = db.get_channels(uid)
        bio = db.get_bio(uid)
        
        if not channels:
            await update.message.reply_text("❌ کانالی اضافه نکردید!", reply_markup=main_keyboard())
            return
        
        if not bio or len(bio.strip()) < 10:
            await update.message.reply_text("❌ بیوگرافی تنظیم نشده!\n👤 از «پروفایل من» استفاده کنید", reply_markup=main_keyboard())
            return
        
        messages = await scanner.scan_all_channels(channels)
        
        if not messages:
            await update.message.reply_text("🔍 پیامی یافت نشد!", reply_markup=main_keyboard())
            return
        
        await update.message.reply_text("🧠 در حال تحلیل AI...")
        matches = await ai_matcher.find_matching_jobs(bio, messages)
        
        if matches:
            await update.message.reply_text(f"🎉 <b>{len(matches)} شغل مرتبط!</b>", parse_mode='HTML')
            
            for job in matches[:10]:
                job_text = f"""
🏢 <b>{job['title']}</b>

📊 تطابق: {job.get('match_score', '?')}%
🤖 {job.get('ai_reason', '')[:100]}

🔗 <a href="{job.get('link', '#')}">مشاهده شغل</a>
"""
                await update.message.reply_text(job_text.strip(), parse_mode='HTML', disable_web_page_preview=True)
        else:
            await update.message.reply_text("🔍 شغلی مطابق پروفایلت یافت نشد!", reply_markup=main_keyboard())
        
        db.update_stats(uid, len(matches))
    
    # کانال‌ها
    elif text == "📋 کانال‌ها":
        channels = db.get_channels(uid)
        text = f"📺 کانال‌ها ({len(channels)})" if channels else "❌ هنوز کانالی نیست!"
        await update.message.reply_text(text, reply_markup=channels_keyboard(channels))
    
    # پروفایل
    elif text == "👤 پروفایل من":
        bio = db.get_bio(uid)
        
        text = "👤 <b>پروفایل شما</b>\n\n"
        if bio and len(bio.strip()) > 10:
            text += f"📝 بیوگرافی:\n{bio[:200]}...\n\n"
        else:
            text += "📝 بیوگرافی: <i>تنظیم نشده</i>\n\n"
        
        text += "✏️ بیوگرافی‌تون رو بنویسید تا AI بتونه شغل‌های مناسب رو پیدا کنه!"
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=profile_keyboard())
    
    # زمان‌بندی
    elif text == "⏰ زمان‌بندی":
        interval = db.get_setting(uid, 'scan_interval', SCAN_INTERVAL)
        hours = interval // 3600
        text = f"⏰ فاصله اسکن: <b>{hours} ساعت</b>\n\nانتخاب کنید:"
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=time_keyboard())
    
    # کانال جدید
    elif text == "➕ کانال جدید":
        context.user_data['waiting'] = 'channel'
        await update.message.reply_text("📢 یوزرنیم کانال (مثل @job_iran):", reply_markup=main_keyboard())
    
    # آمار
    elif text == "🔄 آمار":
        stats = db.get_stats(uid)
        channels = db.get_channels(uid)
        bio = db.get_bio(uid)
        
        text = f"""
📊 آمار:

🔍 تعداد جستجوها: {stats.get('total_scans', 0)}
✅ شغل‌های یافت شده: {stats.get('total_matches', 0)}
📢 کانال‌ها: {len(channels)}
👤 پروفایل: {'✅' if bio and len(bio) > 10 else '❌'}
"""
        await update.message.reply_text(text.strip(), parse_mode='HTML', reply_markup=main_keyboard())
    
    # تنظیمات
    elif text == "⚙️ تنظیمات":
        await update.message.reply_text("⚙️ تنظیمات", reply_markup=settings_keyboard())
    
    # ورودی بیوگرافی
    elif context.user_data.get('waiting') == 'bio':
        db.save_bio(uid, text)
        skills = await ai_matcher.extract_skills(text)
        if skills:
            db.save_skills(uid, skills)
            skills_text = ', '.join(skills[:5])
            await update.message.reply_text(f"✅ ذخیره شد!\n🎯 مهارت‌ها:\n{skills_text}", reply_markup=main_keyboard())
        else:
            await update.message.reply_text("✅ بیوگرافی ذخیره شد!", reply_markup=main_keyboard())
        context.user_data.pop('waiting', None)
    
    # ورودی کانال
    elif context.user_data.get('waiting') == 'channel':
        ch = text.strip()
        if not ch.startswith('@'):
            ch = '@' + ch
        if db.add_channel(uid, ch):
            await update.message.reply_text(f"✅ {ch} اضافه شد!", reply_markup=main_keyboard())
        else:
            await update.message.reply_text(f"ℹ️ {ch} قبلاً هست!", reply_markup=main_keyboard())
        context.user_data.pop('waiting', None)
    
    # بیوگرافی بلند
    elif len(text) > 50:
        db.save_bio(uid, text)
        skills = await ai_matcher.extract_skills(text)
        if skills:
            db.save_skills(uid, skills)
        await update.message.reply_text("✅ بیوگرافی ذخیره شد!", reply_markup=main_keyboard())
    
    else:
        await update.message.reply_text("❓ از دکمه‌ها استفاده کنید!", reply_markup=main_keyboard())


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش اینلاین دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    uid = str(query.from_user.id)
    data = query.data
    
    if data == "main_menu":
        await query.message.edit_text("🏠 منوی اصلی:", reply_markup=main_keyboard())
        return
    
    if data == "edit_bio":
        context.user_data['waiting'] = 'bio'
        await query.message.edit_text("✏️ بیوگرافی کامل:\n\nمثال:\nمن برنامه‌نویس پایتون هستم...", reply_markup=main_keyboard())
        return
    
    if data == "show_profile":
        bio = db.get_bio(uid)
        skills = db.get_skills(uid)
        
        text = "👤 پروفایل:\n\n"
        text += f"📝 بیوگرافی:\n{bio}\n\n" if bio else "📝 بیوگرافی: تنظیم نشده\n\n"
        text += f"🎯 مهارت‌ها:\n{', '.join(skills)}" if skills else ""
        
        await query.message.edit_text(text, parse_mode='HTML', reply_markup=profile_keyboard())
        return
    
    if data == "clear_profile":
        db.save_bio(uid, "")
        db.save_skills(uid, [])
        await query.message.edit_text("✅ پاک شد!", reply_markup=profile_keyboard())
        return
    
    if data == "add_channel_inline":
        context.user_data['waiting'] = 'channel'
        await query.message.edit_text("📢 یوزرنیم کانال:", reply_markup=main_keyboard())
        return
    
    if data.startswith("del_ch_"):
        ch = data[7:]
        db.remove_channel(uid, ch)
        channels = db.get_channels(uid)
        
        text = f"✅ حذف شد!" + (f"\n📺 باقی: {len(channels)}" if channels else "\n❌ کانالی باقی نماند!")
        await query.message.edit_text(text, reply_markup=channels_keyboard(channels))
        return
    
    if data.startswith("t_"):
        seconds = int(data[2:])
        db.set_setting(uid, 'scan_interval', seconds)
        hours = seconds // 3600
        await query.message.edit_text(f"✅ فاصله: {hours} ساعت", reply_markup=time_keyboard())
        return
    
    if data == "set_quiet":
        current = db.get_setting(uid, 'quiet', 'off')
        new_val = 'on' if current == 'off' else 'off'
        db.set_setting(uid, 'quiet', new_val)
        await query.message.edit_text(f"✅ سکوت: {'🔕' if new_val=='on' else '🔔'}", reply_markup=settings_keyboard())
        return
    
    if data == "clear_data":
        db.clear_user_data(uid)
        await query.message.edit_text("✅ همه داده‌ها پاک شد!", reply_markup=settings_keyboard())
        return
    
    if data == "ai_model":
        await query.message.edit_text("🤖 مد: Gemini 2.0 Flash\n• سریع و کم مصرف", reply_markup=settings_keyboard())
        return


# ===================== SCHEDULER =====================

async def ai_scheduler(app):
    """اسکن دوره‌ای - هر 5 ساعت"""
    logger.info(f"⏰ Scheduler شروع - هر {SCAN_INTERVAL//3600} ساعت")
    
    while True:
        try:
            users = db.get_all_users()
            logger.info(f"🔄 چک {len(users)} کاربر")
            
            for user in users:
                uid = user['user_id']
                
                channels = db.get_channels(uid)
                bio = db.get_bio(uid)
                
                if not channels or not bio or len(bio) < 10:
                    continue
                
                # اسکن کانال‌ها
                messages = await scanner.scan_all_channels(channels)
                
                if not messages:
                    continue
                
                # تحلیل AI
                matches = await ai_matcher.find_matching_jobs(bio, messages)
                
                if matches:
                    for job in matches[:5]:
                        try:
                            quiet = db.get_setting(uid, 'quiet', 'off')
                            if quiet == 'on':
                                continue
                            
                            job_text = f"""
🔔 شغل جدید!

🏢 <b>{job['title']}</b>
📊 تطابق: {job.get('match_score', '?')}%
🤖 {job.get('ai_reason', '')[:80]}

🔗 <a href="{job.get('link', '#')}">مشاهده</a>
"""
                            await app.bot.send_message(
                                int(uid),
                                job_text.strip(),
                                parse_mode='HTML',
                                disable_web_page_preview=True
                            )
                            await asyncio.sleep(2)
                        except Exception as e:
                            logger.error(f"خطا: {e}")
                    
                    db.update_stats(uid, len(matches))
            
            logger.info(f"✅ چک تمام - منتظر {SCAN_INTERVAL//3600} ساعت...")
            await asyncio.sleep(SCAN_INTERVAL)
            
        except Exception as e:
            logger.error(f"خطای Scheduler: {e}")
            await asyncio.sleep(60)


# ===================== MAIN =====================

async def post_init(app):
    app.create_task(ai_scheduler(app))
    logger.info("✅ ربات آماده!")

async def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("🤖 ربات شروع شد...")
    await app.run_polling(allowed_updates=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "loop" in str(e).lower():
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
        else:
            raise
