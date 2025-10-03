from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import qrcode
import io
import json
import os
import uuid

app = FastAPI(title="نظام مغسلة السيارات")

# إعداد CORS للسماح بطلبات من جميع المصادر
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# إعداد القوالب والملفات الثابتة
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ملف JSON لتخزين العملاء
CUSTOMERS_FILE = "customers.json"

def init_customers_file():
    """إنشاء ملف العملاء إذا لم يكن موجوداً"""
    if not os.path.exists(CUSTOMERS_FILE):
        with open(CUSTOMERS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def load_customers():
    """تحميل العملاء من ملف JSON"""
    try:
        with open(CUSTOMERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_customers(customers):
    """حفظ العملاء في ملف JSON"""
    with open(CUSTOMERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(customers, f, ensure_ascii=False, indent=2)

# استدعاء عند البدء
init_customers_file()

# الصفحة الرئيسية
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# إضافة عميل جديد
@app.post("/add_customer")
async def add_customer(request: Request):
    try:
        data = await request.json()
        name = data.get('name')
        phone = data.get('phone')
        months = data.get('months', 1)
        
        if not name or not phone:
            return JSONResponse({
                "success": False,
                "error": "الاسم ورقم الهاتف مطلوبان"
            }, status_code=400)
        
        # حساب تواريخ الاشتراك
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30 * months)
        
        # تحميل العملاء الحاليين
        customers = load_customers()
        
        # إنشاء عميل جديد
        customer_id = str(uuid.uuid4())[:8]
        qr_data = f"customer_{customer_id}"
        
        new_customer = {
            "id": customer_id,
            "name": name,
            "phone": phone,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "qr_code": qr_data,
            "is_active": True
        }
        
        customers.append(new_customer)
        save_customers(customers)
        
        return JSONResponse({
            "success": True,
            "message": "تم إضافة العميل بنجاح!",
            "customer_id": customer_id,
            "qr_code": qr_data
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=400)

# جلب جميع العملاء
@app.get("/customers")
async def get_customers():
    try:
        customers = load_customers()
        
        # تحديث حالة الاشتراك
        for customer in customers:
            end_date = datetime.fromisoformat(customer['end_date'])
            customer['is_active'] = datetime.now() < end_date
        
        return customers
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

# مسح كود العميل
@app.get("/scan/{qr_data}")
async def scan_customer(qr_data: str):
    try:
        customers = load_customers()
        
        for customer in customers:
            if customer['qr_code'] == qr_data:
                end_date = datetime.fromisoformat(customer['end_date'])
                is_active = datetime.now() < end_date
                
                return {
                    "found": True,
                    "name": customer['name'],
                    "phone": customer['phone'],
                    "start_date": customer['start_date'],
                    "end_date": customer['end_date'],
                    "active": is_active,
                    "message": "✅ تم العثور على العميل"
                }
        
        return {
            "found": False, 
            "message": "❌ العميل غير موجود"
        }
        
    except Exception as e:
        return {"error": f"خطأ في المسح: {str(e)}"}

# إنشاء صورة QR Code
@app.get("/qrcode/{customer_id}")
async def generate_qr_code(customer_id: str):
    try:
        customers = load_customers()
        
        for customer in customers:
            if customer['id'] == customer_id:
                qr_data = customer['qr_code']
                
                # إنشاء QR Code
                qr = qrcode.make(qr_data)
                img_io = io.BytesIO()
                qr.save(img_io, 'PNG')
                img_io.seek(0)
                
                return FileResponse(img_io, media_type="image/png", filename=f"qrcode_{customer_id}.png")
        
        raise HTTPException(status_code=404, detail="العميل غير موجود")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# حذف جميع العملاء (للتطوير)
@app.delete("/customers")
async def delete_all_customers():
    try:
        save_customers([])
        return {"message": "تم حذف جميع العملاء"}
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

# API للصحة
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "التطبيق يعمل بشكل صحيح"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
    import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
