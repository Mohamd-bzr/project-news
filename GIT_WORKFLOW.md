# Git Workflow — قواعد مدیریت این مخزن

این سند، چرخهٔ رسمی هر تغییر در پروژه است. عاملِ تغییر (انسان یا ایجنت) موظف است
دقیقاً همین ترتیب را اجرا کند.

## چرخهٔ هر تغییر

```
تغییر فایل
   ↓
git status
   ↓
بررسی فایل‌های حساس
   ↓
git add
   ↓
git commit
   ↓
git push origin main
   ↓
git status
   ↓
تأیید موفقیت
```

## قواعد (الزامی)

1. **قبل از هر تغییر**، وضعیت Git بررسی شود (`git status`, branch فعلی، remote).
2. **بعد از تغییرات**، `git status` اجرا شود.
3. فقط فایل‌هایی commit شوند که **مربوط به همان task** هستند — نه `git add .` کورکورانه.
4. قبل از commit مطمئن شو فایل‌های حساس وارد commit نشده‌اند:
   `.env`، API keys، passwords، credentials، private keys، secrets.
   در این پروژه این‌ها همیشه باید gitignored بمانند:
   `settings.json`، `data/api_keys.json`، `data/tv_alerts.json`، `logs/`،
   `.mohmd_news.db`، کش‌های `.json` روت.
5. اگر فایل حساسی پیدا شد: **commit نمی‌شود** و به اپراتور اعلام می‌شود.
6. پیام commit: **کوتاه و واضح**، بر اساس تغییرات واقعی.
7. commit روی branch **`main`** انجام می‌شود.
8. بعد از commit: `git push origin main`.
9. **هرگز `git push --force` یا `git reset --hard` مگر با درخواست صریح اپراتور.**
10. در خطای push: هیچ چیزی حذف یا overwrite نمی‌شود؛ خطا همان‌طور که هست گزارش می‌شود.
11. بعد از push موفق، با `git status` بررسی می‌شود که working tree clean باشد.
12. در پایان: **خلاصهٔ تغییرات + commit hash + نتیجهٔ push** اعلام می‌شود.

## بازرسی سکرت (گام ۳) — حداقل این‌ها

```bash
# نام فایل‌های حساسِ ترَک‌شده
git ls-files | grep -iE "\.env$|secret|credential|password|api_key|token|\.pem|\.key$|id_rsa"
# الگوی توکن تلگرام / کلید OpenAI در محتوای ترَک‌شده
git grep -lIE "\d{8,10}:[A-Za-z0-9_-]{30,}" -- .
git grep -lE "sk-(or-)?[A-Za-z0-9]{20,}" -- .
# مقادیر واقعی فقط در فایل‌های ignore باشند
git check-ignore settings.json data/api_keys.json
```

## مخزن

- **remote:** `git@github.com:Mohamd-bzr/project-news.git` (SSH)
- **branch:** `main`
- سرور پیش‌فرض اجرا: `python app.py --port 5055` → `http://localhost:5055`
