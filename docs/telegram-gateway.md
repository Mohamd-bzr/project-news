# درگاه تلگرام بدون فیلترشکن (Telegram Gateway)

## مشکل چیست؟

`api.telegram.org` در ایران فیلتر است، برای همین «ارسال پیام تست» و ارسال خودکار
بدون فیلترشکن با خطای اتصال مواجه می‌شود. بله (`tapi.bale.ai`) داخل ایران باز است
و به هیچ درگاهی نیاز ندارد.

## راه‌حل: یک Worker رایگان کلادفلر (۵ دقیقه)

به‌جای فیلترشکن، یک درگاه شخصی می‌سازید: کلادفلر سرورهای خارج ایران دارد و
درخواست شما را به تلگرام می‌رساند. توکن ربات فقط از **درگاه خود خودتان** عبور
می‌کند — **هرگز از میرورهای عمومی استفاده نکنید** (توکن ربات لو می‌رود).

### مراحل

1. وارد [dash.cloudflare.com](https://dash.cloudflare.com) شوید و حساب رایگان بسازید.
2. از منو: **Workers & Pages → Create → Create Worker** — یک اسم بدهید (مثلاً `mohmd-tg`) و **Deploy** بزنید.
3. روی **Edit code** بزنید، تمام کد پیش‌فرض را پاک کنید و این را جایگزین کنید:

```js
// Cloudflare Worker — Telegram Bot API gateway (درگاه تلگرام بدون فیلترشکن)
// فقط این فایل را در یک Worker رایگان کلادفلر پیست کنید و Deploy بزنید.
export default {
  async fetch(request) {
    const url = new URL(request.url);
    // فقط مسیرهای Bot API (که با /bot شروع می‌شوند) پاس داده می‌شوند
    if (!url.pathname.startsWith("/bot")) {
      return new Response("not found", { status: 404 });
    }
    const upstream = "https://api.telegram.org" + url.pathname + url.search;
    const init = {
      method: request.method,
      headers: { "Content-Type": request.headers.get("Content-Type") || "application/json" },
    };
    if (request.method === "POST" || request.method === "PUT") {
      init.body = await request.arrayBuffer();
    }
    const resp = await fetch(upstream, init);
    return new Response(resp.body, {
      status: resp.status,
      headers: { "Content-Type": resp.headers.get("Content-Type") || "application/json" },
    });
  },
};
```

4. **Deploy** بزنید. آدرس Worker شما چیزی شبیه این است:
   `https://mohmd-tg.your-name.workers.dev`
5. در داشبورد، تب **پیام‌رسان‌ها → تلگرام**، آدرس را در فیلد
   **«درگاه تلگرام بدون فیلترشکن»** بگذارید و **ذخیره** کنید.
6. «ارسال پیام تست» را بزنید — باید بدون فیلترشکن برسد.

> بعد از این، همهٔ تماس‌ها (تست، ارسال خودکار اخبار، ایده‌های محتوا، تشخیص چت،
> پین) از همین درگاه می‌روند.

## نکته‌ها

- **پلن رایگان** کلادفلر روزانه ۱۰۰٬۰۰۰ درخواست می‌دهد — برای این برنامه بیش از کافی است.
- گاهی خود دامنه `workers.dev` هم محدود می‌شود؛ در آن صورت در کلادفلر یک
  **Custom Domain** (دامنه ارزان یا رایگان خودتان) به Worker وصل کنید.
- راه جایگزین: هر سرور مجازی خارج (VPS) با یک ریورس‌پراکسی ساده Nginx به
  `api.telegram.org` هم همین کار را می‌کند؛ آدرسش را در همان فیلد بگذارید.
- از طریق متغیر محیطی `MOHMD_TG_GATEWAY` هم می‌توانید درگاه را ست کنید.
- برای حذف درگاه، فیلد را خالی کنید و ذخیره بزنید (برمی‌گردد به اتصال مستقیم).
