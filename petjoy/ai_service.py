import google.generativeai as genai
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def get_ai_response(user_message):
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-pro')

        # สร้าง Prompt ที่ดี เพื่อสอน AI ว่าต้องทำอะไร
        full_prompt = f"""
        คุณคือ "PetJoy Bot" ผู้ช่วยของร้าน PetJoy ที่เชี่ยวชาญเรื่องของเล่นสัตว์เลี้ยง
        หน้าที่ของคุณคือตอบคำถามและแนะนำของเล่นอย่างเป็นมิตรและสุภาพ
        ให้ใช้ข้อมูลสินค้าจากรายการนี้ในการแนะนำเท่านั้น:

        --- รายการสินค้า ---
        - Cat Ball: บอลสำหรับแมว
        - Cat Teaser: ไม้ตกแมว
        - Dog Ball: บอลยางสำหรับสุนัข
        - Dog rubber teeth: ของเล่นยางขัดฟันสุนัข
        --- สิ้นสุดรายการสินค้า ---

        คำถามจากลูกค้า: "{user_message}"

        จงตอบคำถามของลูกค้าโดยอิงจากข้อมูลสินค้าที่มีให้เท่านั้น
        """

        response = model.generate_content(full_prompt)
        return response.text

    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return "ขออภัยค่ะ ขณะนี้ระบบมีปัญหา โปรดลองใหม่อีกครั้งนะคะ"