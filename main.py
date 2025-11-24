import logging
import os
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ConversationHandler
)
from io import BytesIO
from PIL import Image
from pdf2docx import Converter
from docx2pdf import convert

# =================================================================
# GLOBAL SOZLAMALAR
# =================================================================

# !!! DIQQAT: TOKENINGIZNI BU YERGA KIRITING !!!
# Render'ga yuklaganingiz uchun bu qator to'g'ri bo'lishi kerak.
TOKEN = "8153725473:AAEO5Vj1IMPQj9PNjNCTgRifyRbzHFzS4YI" 

# === WEBHOOK SOZLAMALARI (TO'G'RILANGAN QISM) ===
# Render portini avtomatik olish uchun
PORT = int(os.environ.get('PORT', '8000')) 

#!!! DIQQAT !!! Sizning haqiqiy Render URL manzilingiz kiritildi.
WEBHOOK_URL = 'https://telegram-converter-bot-ygj1.onrender.com/' 

# =========================================

# Rasm konvertatsiyasi uchun suhbat holatlari
GET_PDF_NAME = 1

# Loglarni sozlash
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# =================================================================
# 1. FUNKSIYALAR TA'RIFLARI
# =================================================================

async def start(update: Update, context: Application) -> None:
    """Foydalanuvchi /start buyrug'ini yuborganda ishlaydi."""
    user = update.effective_user
    await update.message.reply_html(
        f"Assalomu alaykum, {user.mention_html()}! 👋\n"
        "Men Universal Konvertor Botiman. Men 24/7 ishlayman!\n\n"
        "🔸 **Rasm (JPG/PNG)** yuboring, PDF uchun nom so'rayman.\n"
        "🔸 **PDF** yuboring, uni Word (DOCX) ga aylantiraman.\n"
        "🔸 **Word (DOCX)** yuboring, uni PDF ga aylantiraman."
    )

# --- Rasm Konvertatsiyasi Funksiyalari ---

async def start_img_conversion(update: Update, context: Application) -> int:
    """Rasmni qabul qiladi, xotiraga saqlaydi va foydalanuvchidan nom so'raydi."""
    
    photo_file = await update.message.photo[-1].get_file()
    photo_data = BytesIO()
    await photo_file.download_to_memory(photo_data)
    photo_data.seek(0)
    
    context.user_data['photo_bytes'] = photo_data 
    
    await update.message.reply_text(
        "PDF uchun nom kiriting (Masalan: Diplom_ishi). Nom oxiriga '.pdf' qo'shish shart emas:"
    )
    
    return GET_PDF_NAME


async def convert_and_send_pdf(update: Update, context: Application) -> int:
    """Kiritilgan nomni oladi, PDF ga aylantiradi va yuboradi."""
    
    pdf_name = update.message.text.strip()
    if not pdf_name:
        await update.message.reply_text("Nom kiritilmadi. Iltimos, nom kiriting.")
        return GET_PDF_NAME 

    photo_data = context.user_data.get('photo_bytes')
    if not photo_data:
        await update.message.reply_text("Rasm ma'lumotlari topilmadi. Iltimos, rasmni qayta yuboring.")
        context.user_data.clear()
        return ConversationHandler.END

    try:
        photo_data.seek(0)
        img = Image.open(photo_data).convert('RGB')

        pdf_buffer = BytesIO()
        img.save(pdf_buffer, format='PDF', quality=95)
        pdf_buffer.seek(0)
        
        await update.message.reply_document(
            document=pdf_buffer, 
            filename=f"{pdf_name}.pdf",
            caption=f"✅ Rasm '{pdf_name}.pdf' nomida muvaffaqiyatli saqlandi!"
        )
        
    except Exception as e:
        await update.message.reply_text(f"Konvertatsiya jarayonida xatolik yuz berdi: {e}")
        
    context.user_data.clear() 
    return ConversationHandler.END


# --- Hujjat Konvertatsiyasi Funksiyasi (PDF ↔ Word) ---

async def document_converter(update: Update, context: Application) -> None:
    """DOCX ni PDFga va PDF ni DOCXga aylantiradi."""
    await update.message.reply_text("⏳ Fayl yuklanmoqda va qayta ishlanmoqda...")
    
    temp_pdf_name = ""
    temp_docx_name = ""
    
    try:
        document = update.message.document
        
        # Faylni yuklab olish (To'g'ri funksiya)
        file_data = await context.bot.get_file(document.file_id)
        file_bytes = BytesIO()
        await file_data.download_to_memory(file_bytes)
        file_bytes.seek(0)
        
        file_name = document.file_name.lower()
        
        temp_file_base = "temp_" + str(document.file_id)


        if file_name.endswith('.pdf'):
            # ====================================
            # PDF -> WORD (DOCX)
            # ====================================
            await update.message.reply_text("PDF → Word (DOCX) konvertatsiya boshlandi...")
            
            temp_pdf_name = temp_file_base + ".pdf"
            temp_docx_name = temp_file_base + ".docx"
            
            with open(temp_pdf_name, 'wb') as f:
                f.write(file_bytes.getvalue())
            
            try:
                cv = Converter(temp_pdf_name)
                cv.convert(temp_docx_name, start=0, end=None)
                cv.close()

                with open(temp_docx_name, 'rb') as f:
                    docx_buffer = BytesIO(f.read())
                
                await update.message.reply_document(
                    document=docx_buffer, 
                    filename=document.file_name.replace(".pdf", ".docx"),
                    caption="✅ PDF fayli DOCX formatiga muvaffaqiyatli o'tkazildi!"
                )
            except Exception as pdf_e:
                await update.message.reply_text(f"Konvertatsiya jarayonida xatolik yuz berdi: {pdf_e}")

        
        elif file_name.endswith(('.docx', '.doc')):
            # ====================================
            # WORD (DOCX) -> PDF
            # ====================================
            await update.message.reply_text("Word → PDF konvertatsiya boshlandi...")
            
            temp_docx_name = temp_file_base + ".docx"
            temp_pdf_name = temp_file_base + ".pdf"
            
            with open(temp_docx_name, 'wb') as f:
                f.write(file_bytes.getvalue())
            
            try:
                # docx2pdf uchun kerakli buyruq
                convert(temp_docx_name, temp_pdf_name)

                with open(temp_pdf_name, 'rb') as f:
                    pdf_buffer = BytesIO(f.read())
                
                await update.message.reply_document(
                    document=pdf_buffer, 
                    filename=document.file_name.replace(".docx", ".pdf").replace(".doc", ".pdf"),
                    caption="✅ Word fayli PDF formatiga muvaffaqiyatli o'tkazildi!"
                )
            except Exception as docx_e:
                await update.message.reply_text(f"⚠️ Word → PDF konvertatsiyasi xatolik yuz berdi:\n\n"
                                                f"Ehtimol, serverda **Microsoft Word** yoki **LibreOffice** o'rnatilmagan. Xatolik: {docx_e}")

        
        else:
            await update.message.reply_text("⚠️ Noto'g'ri fayl formati. Faqat PDF, DOCX yoki rasm (PHOTO) fayllarini yuboring.")
        
    
    except Exception as e:
        await update.message.reply_text(f"Kutilmagan xatolik yuz berdi: {e}")

    # Faylni qayta ishlash tugaganidan keyin vaqtinchalik fayllarni o'chirish
    finally:
        if os.path.exists(temp_pdf_name):
            os.remove(temp_pdf_name)
        if os.path.exists(temp_docx_name):
            os.remove(temp_docx_name)

# =================================================================
# 2. MAIN FUNKSIYA
# =================================================================

def main() -> None:
    """Botni Webhook rejimida ishga tushirish uchun asosiy funksiya."""
    
    application = Application.builder().token(TOKEN).build()
    
    # --- Handlerlarni registratsiya qilish ---

    application.add_handler(CommandHandler("start", start))

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO & ~filters.COMMAND, start_img_conversion)],
        states={
            GET_PDF_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, convert_and_send_pdf)],
        },
        fallbacks=[CommandHandler("cancel", convert_and_send_pdf)]
    )
    application.add_handler(conv_handler) 
    
    application.add_handler(MessageHandler(filters.Document.ALL & ~filters.PHOTO & ~filters.COMMAND, document_converter)) 

    # Botni WEBHOOK rejimida ishga tushirish (Render manzilini ishlatadi)
    WEBHOOK_ADDRESS = WEBHOOK_URL + TOKEN
    
    print(f"Bot Webhook rejimida ishga tushmoqda. Port: {PORT}")
    
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=WEBHOOK_ADDRESS
    )
    


if __name__ == '__main__':
    main()
