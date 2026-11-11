import re
from groq import Groq
from config import config

client = Groq(api_key=config.GROQ_API_KEY)

def to_roman_urdu_if_needed(text: str) -> str:
    has_urdu = any('\u0600' <= c <= '\u06FF' for c in text)
    has_hindi = any('\u0900' <= c <= '\u097F' for c in text)
    if not (has_urdu or has_hindi):
        return text
    
    resp = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {'role': 'system', 'content': "You are a translator. Transliterate Urdu or Hindi text into natural Roman Urdu using English alphabets (e.g. 'kya haal he', 'brightness 25 kardo'). Keep English words in English. Return ONLY the Roman Urdu text without explanations or quotation marks."},
            {'role': 'user', 'content': text}
        ],
        temperature=0.0,
        max_tokens=60
    )
    res = resp.choices[0].message.content.strip()
    res = re.sub(r'<think>.*?</think>', '', res, flags=re.DOTALL).strip('\"\' ')
    return res

test_str = "کیا حال ہے بھائی جان برائٹنس 25 کردو"
print("Input:", test_str)
print("Output:", to_roman_urdu_if_needed(test_str))

