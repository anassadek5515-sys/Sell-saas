import sqlite3
import imaplib
import email
from email.header import decode_header
import os

# --- 1. إعدادات البريد المركزي أو حساب الإرسال ---
IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.gmail.com")
IMAP_USER = os.environ.get("EMAIL_USER", "your_email@gmail.com")
IMAP_PASS = os.environ.get("EMAIL_PASS", "your_app_password")

DB_FILE = "companies.db"

def process_inbox():
    if not os.path.exists(DB_FILE):
        print("⚠️ قاعدة البيانات غير موجودة محلياً!")
        return

    try:
        # الاتصال بسيرفر البريد عبر IMAP
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(IMAP_USER, IMAP_PASS)
        mail.select("inbox")

        # البحث عن كافة الرسائل غير المقروءة (UNSEEN)
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()

        if not email_ids:
            print("✅ لا توجد ردود جديدة غير مقروءة حالياً.")
            return

        print(f"📩 تم العثور على {len(email_ids)} رسالة جديدة! جاري الفحص والتحديث...")

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # التأكد من وجود أعمدة الردود في قاعدة البيانات
        cursor.execute("PRAGMA table_info(companies)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'reply_text' not in columns:
            cursor.execute("ALTER TABLE companies ADD COLUMN reply_text TEXT")

        for e_id in email_ids:
            _, msg_data = mail.fetch(e_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # استخراج إيميل الراسل
                    from_header = msg.get("From")
                    sender_email = email.utils.parseaddr(from_header)[1].lower()

                    # استخراج محتوى الرسالة
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                except:
                                    pass
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except:
                            pass

                    # البحث في قاعدة البيانات عن الإيميل وتحديث حالته
                    cursor.execute("SELECT id FROM companies WHERE email = ?", (sender_email,))
                    row = cursor.fetchone()

                    if row:
                        cursor.execute("""
                            UPDATE companies 
                            SET status = 'Replied', reply_text = ? 
                            WHERE email = ?
                        """, (body.strip()[:1000], sender_email))
                        print(f"🎯 تم اكتشاف رد من الشركة: {sender_email} وتحديث الحالتين بنجاح!")

        conn.commit()
        conn.close()
        mail.logout()
        print("🚀 اكتملت عملية معالجة الردود بنجاح!")

    except Exception as e:
        print(f"❌ خطأ أثناء الاتصال بمزود البريد: {e}")

if __name__ == "__main__":
    process_inbox()
