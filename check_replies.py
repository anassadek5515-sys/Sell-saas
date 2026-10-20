import sqlite3
import imaplib
import email
import os

# --- الإعدادات الأساسية ---
DB_FILE = "companies.db"

# بيانات استقبال البريد (IMAP) - سحب من متغيرات البيئة أو جيت هب
IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = 993  # البورت الصحيح والآمن لاستقبال الإيميلات عبر SSL
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "your_email@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "your_app_password")

def check_inbox_replies():
    """
    فحص البريد الوارد للبحث عن ردود من الشركات وتحديث حالتها في قاعدة البيانات
    """
    if not os.path.exists(DB_FILE):
        print("⚠️ قاعدة البيانات غير موجودة محلياً!")
        return

    try:
        # الاتصال بسيرفر IMAP باستخدام SSL والبورت الصحيح 993
        print("🔍 جاري الاتصال بسيرفر البريد لفحص الردود...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        # فتح صندوق الوارد (Inbox)
        mail.select("inbox")

        # البحث عن كل الرسائل غير المقروءة أو كل الرسائل الواردة
        status, messages = mail.search(None, 'UNSEEN')
        
        if status != 'OK':
            print("ℹ️ لم يتم العثور على رسائل جديدة.")
            mail.logout()
            return

        email_ids = messages[0].split()
        if not email_ids:
            print("📭 لا توجد ردود جديدة في صندوق الوارد حالياً.")
            mail.logout()
            return

        print(جاري فحص {len(email_ids)} رسالة جديدة...)

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # استخراج إيميل المرسل وصندوق الموضوع
                    from_header = msg.get('From')
                    subject_header = msg.get('Subject', '')
                    
                    # استخراج البريد الصافي للمرسل
                    sender_email = ""
                    if '<' in from_header and '>' in from_header:
                        sender_email = from_header.split('<')[1].split('>')[0].strip()
                    else:
                        sender_email = from_header.strip()

                    # استخراج نص الرسالة (Body)
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

                    # مطابقة الإيميل الوارد مع الشركات المسجلة في قاعدة البيانات
                    cursor.execute("SELECT id, name FROM companies WHERE email = ?", (sender_email,))
                    lead = cursor.fetchone()

                    if lead:
                        lead_id, company_name = lead[0], lead[1]
                        
                        # تحديث الحالة إلى Replied وحفظ نص الرد
                        cursor.execute("""
                            UPDATE companies 
                            SET status = 'Replied', reply_text = ? 
                            WHERE id = ?
                        """, (body[:500], lead_id)) # حفظ أول 500 حرف من الرد كحد أقصى
                        conn.commit()
                        
                        print(f"🎉 تم العثور على رد من الشركة: {company_name} ({sender_email})!")

        conn.close()
        mail.logout()
        print("✨ انتهى فحص الردود بنجاح!")

    except Exception as e:
        print(f"❌ خطأ أثناء الاتصال بمزود البريد لفحص الردود: {e}")

if __name__ == "__main__":
    check_inbox_replies()
