"""
🔍 اسکنر کانال‌های تلگرام
دریافت پیام‌ها و استخراج اطلاعات شغل
"""

import asyncio
import re
from typing import List, Dict, Optional
from telegram import Bot


class JobScanner:
    """اسکن کانال‌های تلگرام"""
    
    def __init__(self, bot_token: str = None):
        if bot_token is None:
            from main import BOT_TOKEN
            bot_token = BOT_TOKEN
        self.bot = Bot(token=bot_token)
    
    async def fetch_channel_messages(
        self,
        channel_username: str,
        limit: int = 50
    ) -> List[Dict]:
        """دریافت پیام‌های اخیر کانال"""
        try:
            chat = await self.bot.get_chat(channel_username)
            
            messages = await self.bot.get_chat_history(
                chat_id=chat.id,
                limit=limit
            )
            
            results = []
            for msg in messages:
                if msg.text or msg.caption:
                    # ساخت لینک پیام
                    link = f"https://t.me/{channel_username.replace('@', '')}/{msg.message_id}"
                    
                    results.append({
                        'message_id': str(msg.message_id),
                        'text': msg.text or msg.caption,
                        'date': str(msg.date) if msg.date else None,
                        'link': link,
                        'source': channel_username,
                        'chat_id': chat.id
                    })
            
            return results
            
        except Exception as e:
            print(f"❌ خطا در اسکن {channel_username}: {e}")
            return []
    
    async def scan_all_channels(
        self,
        channels: List[str],
        limit_per_channel: int = 30
    ) -> List[Dict]:
        """اسکن همه کانال‌ها"""
        all_messages = []
        
        for channel in channels:
            print(f"🔍 اسکن: {channel}")
            messages = await self.fetch_channel_messages(channel, limit_per_channel)
            all_messages.extend(messages)
            
            # کمی صبر بین کانال‌ها
            await asyncio.sleep(1)
        
        return all_messages
    
    def extract_job_info(self, text: str, source: str, link: str) -> Optional[Dict]:
        """استخراج اطلاعات شغل از متن"""
        
        # الگوهای شناسایی شغل
        job_patterns = [
            r'(?:استخدام|نیازمندی|فرصت\s*شغلی|همکاری)',
            r'(?:position|job|hire|vacancy)',
        ]
        
        has_job = False
        for pattern in job_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                has_job = True
                break
        
        if not has_job:
            return None
        
        # استخراج عنوان
        title = ""
        title_patterns = [
            r'(?:استخدام|نیازمندی)\s*(?:به\s*)?(?:یک|یکی\s*از)?\s*([^\n,]{3,50})',
            r'(?:عنوان\s*شغل|پست):\s*([^\n]{3,50})',
            r'^([^\n]{5,60})',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                break
        
        if not title:
            title = text.split('\n')[0][:80] if text else "شغل نامشخص"
        
        # استخراج شرکت
        company = ""
        company_patterns = [
            r'(?:شرکت|کانون|گروه|سازمان|تیم)\s*:?\s*([^\n,]{2,40})',
            r'(?:company|corp|inc):\s*([^\n,]{2,40})',
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                break
        
        # استخراج موقعیت
        location = ""
        locations = [
            'تهران', 'اصفهان', 'شیراز', 'مشهد', 'تبریز', 'کرج',
            'قم', 'اهواز', 'رشت', 'کیش', 'سمنان', 'یزد',
            'کرمان', 'بندرعباس', 'اراک', 'ارومیه', 'زنجان'
        ]
        
        for loc in locations:
            if loc in text:
                location = loc
                break
        
        # بررسی ریموت
        if re.search(r'(?:ریموت|دورکاری|remote|work from home)', text, re.IGNORECASE):
            location = location + " (ریموت)" if location else "ریموت"
        
        # استخراج نوع کار
        job_type = "تمام وقت"
        if re.search(r'(?:پاره\s*وقت|part[\s-]*time)', text, re.IGNORECASE):
            job_type = "پاره وقت"
        elif re.search(r'(?:فریلنسر|freelance)', text, re.IGNORECASE):
            job_type = "فریلنسری"
        
        # استخراج حقوق
        salary = ""
        salary_patterns = [
            r'(?:از|حداقل|بین)\s*([\d۰-۹,]+)\s*(?:تا|و|-)\s*([\d۰-۹,]+)\s*(?:تومان|هزار)?',
            r'([\d۰-۹,]+)\s*(?:تومان|هزار)',
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, text)
            if match:
                salary = match.group(0).strip()
                break
        
        return {
            'title': title[:100],
            'company': company,
            'location': location,
            'salary': salary,
            'type': job_type,
            'text': text[:500],
            'source': source,
            'link': link
        }
    
    def is_job_related(self, text: str) -> bool:
        """آیا متن مرتبط با کار هست؟"""
        keywords = [
            'استخدام', 'نیازمندی', 'فرصت شغلی', 'همکاری',
            'position', 'job', 'hire', 'vacancy', 'کار',
            'developer', 'programmer', 'designer', 'marketing',
            'manager', 'engineer', 'سازمان', 'شرکت'
        ]
        
        text_lower = text.lower()
        for kw in keywords:
            if kw.lower() in text_lower:
                return True
        
        return False