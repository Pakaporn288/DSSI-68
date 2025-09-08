import google.generativeai as genai
from django.conf import settings
import logging
from .models import Product

logger = logging.getLogger(__name__)

def get_ai_response(user_message):
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-pro')

        # ✅ 2. ดึงข้อมูลสินค้าทั้งหมดจากฐานข้อมูล
        products = Product.objects.all()

        # ✅ 3. แปลงข้อมูลสินค้าเป็นข้อความที่ AI จะอ่านได้
        if products:
            product_list = "\n".join(
                [f"- {p.name}: {p.description} (ราคา {p.price} บาท)" for p in products]
            )
        else:
            product_list = "ตอนนี้ยังไม่มีสินค้าในร้าน"

        # ✅ 4. นำรายการสินค้าที่ดึงได้ใส่เข้าไปใน Prompt
        full_prompt = f"""
        คุณคือ "PetJoy Bot" ผู้ช่วยอัจฉริยะของร้าน PetJoy
        หน้าที่ของคุณคือตอบคำถามและแนะนำของเล่นสัตว์เลี้ยงอย่างเป็นมิตร
        ให้ใช้ข้อมูลสินค้าจากรายการ "ที่มีอยู่จริง" ต่อไปนี้ในการแนะนำเท่านั้น:

        --- รายการสินค้าที่มีอยู่จริง ---
        {product_list}
        --- สิ้นสุดรายการสินค้า ---

        คำถามจากลูกค้า: "{user_message}"
        """

        response = model.generate_content(full_prompt)
        return response.text

    except Exception as e:
        print(f"Error from Gemini: {e}")
        return "ขออภัยค่ะ ขณะนี้ระบบมีปัญหา โปรดลองใหม่อีกครั้งนะคะ"