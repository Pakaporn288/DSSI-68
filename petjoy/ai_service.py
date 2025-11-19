import os
import google.generativeai as genai
from .models import Product
import logging

logger = logging.getLogger(__name__)

#  1. ตั้งค่า API Key ที่นี่
# ดึง API Key จากตัวแปรแวดล้อม (ไฟล์ .env)
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.error("GEMINI_API_KEY is not set in the environment variables.")

def get_ai_response(user_message):
    # ตรวจสอบว่า API Key ถูกตั้งค่าเรียบร้อยหรือไม่
    if not api_key:
        return "ขออภัยค่ะ ขณะนี้ระบบ AI ไม่พร้อมใช้งาน (API Key not configured)"

    try:
        model = genai.GenerativeModel('models/gemini-pro-latest')

        products = Product.objects.all()
        if products:
            product_list = "\n".join(
                [f"- {p.name}: {p.description} (ราคา {p.price} บาท)" for p in products]
            )
        else:
            product_list = "ตอนนี้ยังไม่มีสินค้าในร้าน"

        full_prompt = f"""
        คุณคือ "PetJoy Bot" ผู้ช่วยอัจฉริยะของร้าน PetJoy
        ตอบคำถามและแนะนำสินค้าให้สั้น กระชับ ได้ใจความ ไม่เกิน 2-3 ประโยค
        ให้ใช้ข้อมูลสินค้าจากรายการ "ที่มีอยู่จริง" ต่อไปนี้ในการแนะนำเท่านั้น:

        --- รายการสินค้าที่มีอยู่จริง ---
        {product_list}
        --- สิ้นสุดรายการสินค้า ---

        คำถามจากลูกค้า: "{user_message}"
        """

        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        # ใช้ logger เพื่อบันทึก error ที่เกิดขึ้นจริงลงใน console
        logger.error(f"Error from Gemini API: {e}")
        return "ขออภัยค่ะ ขณะนี้ระบบมีปัญหา โปรดลองใหม่อีกครั้งนะคะ"