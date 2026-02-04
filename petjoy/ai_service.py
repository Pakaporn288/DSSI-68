import os
from dotenv import load_dotenv
import google.generativeai as genai
from .models import Product
import logging

logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

user_memory = {}

def get_ai_response(user_message, user_id):
    if not api_key:
        return "ขออภัยค่ะ ระบบ AI ยังไม่ได้ตั้งค่า API Key"

    try:
        # 1. จัดการความจำ (Memory)
        memory_context = ""
        if user_id:
            if user_id not in user_memory:
                user_memory[user_id] = []
            user_memory[user_id].append(user_message)
            memory_context = "\n".join(user_memory[user_id][-5:])
        else:
            memory_context = "ผู้ใช้งานทั่วไป (ไม่จำประวัติ)"

        # 2. ดึงสินค้า
        products = Product.objects.all()
        if products.exists():
            product_list = []
            for p in products:
                status = "✅มีของ" if p.stock > 0 else "❌หมด"
                product_list.append(f"- {p.name} (ราคา {p.price}.-) [{status}] จุดเด่น: {p.description}")
            product_context = "\n".join(product_list)
        else:
            product_context = "ขณะนี้ไม่มีสินค้าในร้าน"

        # 3. Prompt (เพิ่มกฎห้ามใช้ ##)
        system_instruction = f"""
        คุณคือ 'PetJoy Bot' ผู้ช่วยขายของร้าน PetJoy
        
        ข้อมูลสินค้าที่มี:
        {product_context}

        ประวัติการคุย:
        {memory_context}

        กฎเหล็กในการตอบ:
        1. **ห้ามใช้เครื่องหมายหัวข้อใหญ่ (เช่น ## หรือ ###) เด็ดขาด** ให้ใช้ตัวหนา (**) แทน
        2. ห้ามตอบยาวเป็นพืด ให้ตอบสั้นกระชับ แยกบรรทัด
        3. ใช้ Bullet point (-) เมื่อแนะนำรายการสินค้า
        4. ใช้ **ตัวหนา** ตรงชื่อสินค้าและราคา
        5. ตอบด้วยน้ำเสียงสดใส น่ารัก มีอีโมจิ 🐶
        """

        model = genai.GenerativeModel(
            model_name='models/gemini-2.5-flash',
            system_instruction=system_instruction
        )

        response = model.generate_content(user_message)
        ai_text = response.text.strip()
        
        if user_id:
            user_memory[user_id].append(f"AI: {ai_text}")
        
        return ai_text

    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "ขออภัยค่ะ น้อง Joy มึนหัวนิดหน่อย ถามใหม่อีกทีนะคะ 🐶"