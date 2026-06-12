"""
🧠 ماژول هوش مصنوعی Gemini
تحلیل و تطابق شغل‌ها با پروفایل کاربر

Model: gemini-2.0-flash (کم مصرف و سریع)
API: AQ.Ab8RN6ISMMWB0Owdrx5sOBsNmMLH5JNHtc3sdcN0KzfgK4x-jQ
"""

import asyncio
import json
import logging
from typing import List, Dict, Optional

import requests

logger = logging.getLogger(__name__)

# API Configuration
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_API_KEY = "AQ.Ab8RN6ISMMWB0Owdrx5sOBsNmMLH5JNHtc3sdcN0KzfgK4x-jQ"


class GeminiMatcher:
    """تطبیق شغل‌ها با پروفایل کاربر با استفاده از AI"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = "gemini-2.0-flash"
    
    def _call_gemini(self, prompt: str, temperature: float = 0.3) -> Optional[str]:
        """فراخوانی API Gemini"""
        try:
            url = f"{GEMINI_API_URL}?key={self.api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": 2048,
                    "topP": 0.8,
                    "topK": 40
                }
            }
            
            response = requests.post(
                url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and len(data['candidates']) > 0:
                    return data['candidates'][0]['content']['parts'][0]['text']
            
            logger.error(f"Gemini API Error: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Gemini Error: {e}")
            return None
    
    async def find_matching_jobs(
        self,
        user_bio: str,
        messages: List[Dict],
        max_jobs: int = 10
    ) -> List[Dict]:
        """
        پیدا کردن شغل‌های مناسب بر اساس بیوگرافی کاربر
        
        Args:
            user_bio: بیوگرافی کاربر
            messages: لیست پیام‌های کانال‌ها
            max_jobs: حداکثر تعداد شغل‌های خروجی
        
        Returns:
            لیست شغل‌های مطابق با امتیاز تطابق
        """
        
        if not messages:
            return []
        
        # فیلتر پیام‌های مرتبط با کار
        job_messages = []
        for msg in messages:
            text = msg.get('text', '')
            # ساده‌ترین فیلتر - فقط پیام‌های کوتاه تا متوسط
            if 50 < len(text) < 2000:
                job_messages.append(msg)
        
        if not job_messages:
            return []
        
        # آماده‌سازی داده‌ها برای AI
        messages_text = "\n---\n".join([
            f"[کانال: {msg.get('source', '')}]\n{msg.get('text', '')[:500]}"
            for msg in job_messages[:20]  # حداکثر 20 پیام
        ])
        
        # ساخت پرامپت
        prompt = f"""تو یک متخصص منابع انسانی هستی. کاربر زیر به دنبال شغل مناسب می‌گردد:

📝 <b>پروفایل کاربر:</b>
{user_bio}

📋 <b>آگهی‌های شغلی:</b>
{messages_text}

🎯 وظیفه تو:
1. هر آگهی را با پروفایل کاربر مقایسه کن
2. شغل‌های مرتبط را انتخاب کن (حداکثر {max_jobs} شغل)
3. برای هر شغل امتیاز تطابق (0-100%) بده

⚠️ قوانین:
- فقط شغل‌های واقعاً مرتبط را انتخاب کن
- اگه شغلی نامربوطه، انتخاب نکن
- امتیاز پایین یعنی شغل کمتر مناسب

📤 خروجی JSON:
```json
[
  {{
    "index": 0,
    "title": "عنوان شغل از آگهی",
    "match_score": 85,
    "reason": "دلیل تطابق در یک جمله",
    "source": "نام کانال"
  }},
  ...
]
```

اگه هیچ شغلی مناسب نیست، خروجی بده: []
"""
        
        # فراخوانی AI
        result = self._call_gemini(prompt)
        
        if not result:
            return []
        
        # پارس JSON
        try:
            # پیدا کردن بخش JSON
            json_start = result.find('[')
            json_end = result.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = result[json_start:json_end]
                matches = json.loads(json_str)
                
                # اضافه کردن اطلاعات کامل شغل
                results = []
                for match in matches[:max_jobs]:
                    idx = match.get('index', 0)
                    if idx < len(job_messages):
                        msg = job_messages[idx]
                        
                        # استخراج عنوان از متن
                        text = msg.get('text', '')
                        lines = text.split('\n')
                        title = lines[0][:100] if lines else "شغل"
                        
                        # حذف کاراکترهای اضافی از عنوان
                        for prefix in ['استخدام ', 'نیازمندی ', 'فرصت شغلی ']:
                            if title.startswith(prefix):
                                title = title[len(prefix):]
                        
                        results.append({
                            'title': match.get('title', title),
                            'match_score': match.get('match_score', 50),
                            'ai_reason': match.get('reason', ''),
                            'source': msg.get('source', ''),
                            'link': msg.get('link', ''),
                            'text': text[:300],
                            'message_id': msg.get('message_id', '')
                        })
                
                return results
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {e}")
            logger.info(f"Raw response: {result[:500]}")
        
        return []
    
    async def extract_skills(self, bio: str) -> List[str]:
        """استخراج مهارت‌ها از بیوگرافی"""
        
        prompt = f"""از این بیوگرافی، مهارت‌ها و تخصص‌های اصلی را استخراج کن:

{bio}

📤 خروجی فقط یک لیست JSON:
```json
["مهارت 1", "مهارت 2", "مهارت 3", ...]
```

فقط مهارت‌های واقعی را بنویس. حداکثر 10 مهارت."""
        
        result = self._call_gemini(prompt)
        
        if not result:
            return []
        
        try:
            json_start = result.find('[')
            json_end = result.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                return json.loads(result[json_start:json_end])
                
        except:
            pass
        
        return []
    
    async def analyze_job(self, job_text: str, user_bio: str) -> Dict:
        """تحلیل یک شغل خاص"""
        
        prompt = f"""این یک آگهی شغلی است:
{job_text}

و این پروفایل کاربر:
{user_bio}

آیا این شغل برای این کاربر مناسب است؟
مقایسه کن و توضیح بده چرا."""
        
        result = self._call_gemini(prompt)
        
        return {
            'analysis': result if result else "تحلیل نشد",
            'suitable': bool(result)
        }
    
    async def generate_search_keywords(self, bio: str) -> List[str]:
        """تولید کلمات کلیدی جستجو بر اساس بیوگرافی"""
        
        prompt = f"""بر اساس این پروفایل، کلمات کلیدی مناسب برای جستجوی شغل پیشنهاد بده:

{bio}

فقط کلمات کلیدی فارسی یا انگلیسی مرتبط."""
        
        result = self._call_gemini(prompt)
        
        if not result:
            return []
        
        # استخراج کلمات
        keywords = []
        for line in result.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # حذف شماره و علامت
                line = re.sub(r'^[\d\.\-\*\•\▶\s]+', '', line)
                if line and len(line) > 2:
                    keywords.append(line[:50])
        
        return keywords[:10]


# کمکی برای regex
import re