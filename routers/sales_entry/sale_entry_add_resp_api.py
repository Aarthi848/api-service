import traceback
from typing import Any, Dict, List, Optional

import pymysql.cursors
from fastapi import APIRouter, HTTPException, Body, Query, Request
from pydantic import BaseModel

from database import get_connection
from logger import get_logger

logger = get_logger("sale_entry_add_resp_api")
router = APIRouter()


# ----------------------------------------------------------------------
# 📦 REQUEST & RESPONSE MODELS (1:1 with SaleEntryAddResp.jsp)
# ----------------------------------------------------------------------
class SaveItemRow(BaseModel):
    item_code: str
    qty: float
    rate: float = 0.0
    sel_price: Optional[float] = None
    discount: float = 0.0
    amount: float = 0.0
    sgst_per: float = 0.0
    cgst_per: float = 0.0
    igst_per: float = 0.0
    stock_flag: str = "Y"
    unit_code: str = ""


class SaleEntryAddRespRequest(BaseModel):
    outlet_id: Optional[str] = "0135010108"
    outletId: Optional[str] = None           # Alias for outlet_id (from JSP form input)
    date: Optional[str] = ""                 # e.g. "2026-08-12" or "12-Aug-2026"
    date1: Optional[str] = None              # Alias for date (from JSP form input)
    group_code: Optional[str] = "0100"       # Party group code
    GroupCode: Optional[str] = None          # Alias for group_code (from JSP form input)
    user_code: Optional[str] = "656"
    UserCode: Optional[str] = None
    customer_name: Optional[str] = ""
    CustomerName: Optional[str] = None
    cus_mobile_no: Optional[str] = ""
    CusMobileNo: Optional[str] = None
    grand_total: Optional[float] = 0.0
    grandTot: Optional[float] = None
    discount_per: Optional[float] = 0.0
    SelDiscount: Optional[float] = None
    items: List[SaveItemRow] = []


class SaleEntryAddRespResponse(BaseModel):
    status: int
    message: str
    bill_no: str
    ref_no: int
    tran_no: str
    grand_total: float
    total_items_saved: int


# ----------------------------------------------------------------------
# 🛠️ CORE TRANSACTION LOGIC (1:1 with SaleEntryAddResp.jsp DB logic)
# ----------------------------------------------------------------------
def execute_sale_entry_save(conn: Any, req: SaleEntryAddRespRequest) -> SaleEntryAddRespResponse:
    """Executes the atomic DB save transaction from SaleEntryAddResp.jsp."""
    conn.autocommit(False)
    try:
        outlet_id = req.outlet_id or req.outletId or "0135010108"
        date1 = req.date or req.date1 or ""
        group_code = req.group_code or req.GroupCode or "0100"
        user_code = req.user_code or req.UserCode or "656"
        customer_name = req.customer_name or req.CustomerName or ""
        cus_mobile_no = req.cus_mobile_no or req.CusMobileNo or ""
        grand_tot_input = req.grand_total if req.grand_total is not None else (req.grandTot or 0.0)

        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            # 1. Check local calendar date condition matching JSP
            sql_check_date = """
                SELECT count(*) AS cnt 
                FROM LOCAL_CALENDAR 
                WHERE CALENDAR_DATE >= '2020-04-01' AND CALENDAR_DATE = %s
            """
            cur.execute(sql_check_date, (date1,))
            row_date = cur.fetchone()
            del_date = row_date["cnt"] if row_date else 0

            if del_date == 0:
                cur.execute("""
                    SELECT IFNULL(MAX(KM_REF_NO)+1, 1) AS CNT 
                    FROM SS_KOT_MAIN 
                    WHERE KM_OUTLET_ID = %s AND km_tran_date < '2020-04-01'
                """, (outlet_id,))
            else:
                cur.execute("""
                    SELECT IFNULL(MAX(KM_bill_NO)+1, 1) AS CNT 
                    FROM SS_KOT_MAIN 
                    WHERE km_tran_date >= '2020-04-01' AND KM_OUTLET_ID = %s
                """, (outlet_id,))

            row_ref = cur.fetchone()
            km_ref_no = row_ref["CNT"] if row_ref else 1

            # Format Bill No (5-digit padded)
            cur.execute("SELECT LPAD(%s, 5, 0) AS BILLNO FROM DUAL", (km_ref_no,))
            row_bill = cur.fetchone()
            bill_no = row_bill["BILLNO"] if row_bill else f"{km_ref_no:05d}"

            # Generate Transaction No
            cur.execute("SELECT DATE_FORMAT(NOW(), '%%d%%m%%Y%%H%%i%%s') AS TRAN_NO FROM DUAL")
            row_tran = cur.fetchone()
            tran_no_raw = row_tran["TRAN_NO"] if row_tran else ""
            tran_no1 = f"{outlet_id}{tran_no_raw}"

            tot_sgst = 0.0
            tot_cgst = 0.0
            tot_discount = 0.0
            items_saved_count = 0

            # 2. Insert rows into SS_KOT_ITEMS for items with qty > 0
            for item in req.items:
                if item.qty > 0:
                    items_saved_count += 1
                    sel_price = item.sel_price if item.sel_price is not None else (item.rate or 0.0)
                    discount = item.discount or 0.0
                    amount = item.amount if item.amount > 0 else ((sel_price * item.qty) - discount)

                    sgst_val = ((item.qty * sel_price) - discount) * item.sgst_per / 100.0
                    cgst_val = ((item.qty * sel_price) - discount) * item.cgst_per / 100.0

                    tot_sgst += sgst_val
                    tot_cgst += cgst_val
                    tot_discount += discount

                    sql_kot_item = """
                        INSERT INTO SS_KOT_ITEMS (
                            KI_TABLE_NO, KI_BILL_NO, KI_REF_NO, KI_MAIN_ITEM_CODE, KI_SUB_ITEM_CODE, 
                            KI_ITEM_AMOUNT, KI_ITEM_DISCOUNT, KI_TRAN_DATE, KI_ITEM_QTY, KI_NET_AMOUNT, 
                            KI_ITEM_TAX1, KI_OUTLET_ID, KI_CREATED_USER_CODE, KI_CREATED_DATE, 
                            KI_FLAG_STATUS, KI_RECV_DATE_TIME, KI_KOT_NO, KI_KOT_TRANNO, 
                            KI_SELL_TYPE, KI_ITEM_TAX2, KI_ITEM_TAX3, KI_ITEM_TAX_PER2, KI_ITEM_TAX_PER3
                        ) VALUES (
                            '0101', %s, %s, %s, %s, 
                            %s, %s, %s, %s, %s, 
                            0, %s, %s, NOW(), 
                            0, NOW(), '1', %s, 
                            '0', %s, %s, %s, %s
                        )
                    """
                    cur.execute(sql_kot_item, (
                        bill_no, km_ref_no, item.item_code, item.item_code,
                        sel_price, discount, date1, item.qty, amount,
                        outlet_id, user_code, tran_no1,
                        sgst_val, cgst_val, item.sgst_per, item.cgst_per
                    ))

            # 3. Master Insert: SS_KOT_MAIN
            sql_kot_main = """
                INSERT INTO SS_KOT_MAIN (
                    KM_TABLE_NO, KM_BILL_NO, KM_REF_NO, KM_OUTLET_ID,
                    KM_TRAN_DATE, KM_CREATED_USER_CODE, KM_FLAG_STATUS,
                    KM_CREATED_DATE, KM_RECV_DATE_TIME, KM_KOT_NO, KM_TRAN_NO, KM_TA_CUST_REMARKS
                ) VALUES ('0101', %s, %s, %s, %s, %s, 0, NOW(), NOW(), '1', %s, 'WEB BILL')
            """
            cur.execute(sql_kot_main, (bill_no, km_ref_no, outlet_id, date1, user_code, tran_no1))

            # 4. Net amount & Rounding calculations
            calc_net_amt = grand_tot_input if grand_tot_input > 0 else (sum(i.amount for i in req.items if i.qty > 0))
            max_amount = round(calc_net_amt)
            min_amount = max_amount - calc_net_amt

            pay_code = "0203"
            group_code1 = group_code
            if group_code1 and len(group_code1) == 4:
                pay_code = group_code1
                group_code1 = "0"

            # 5. Master Insert: SS_BILL_MAIN
            sql_bill_main = """
                INSERT INTO SS_BILL_MAIN (
                    BM_TABLE_NO, BM_BILL_NO, BM_REF_NO, BM_NET_AMOUNT, BM_TRAN_DATE, 
                    BM_OUTLET_ID, BM_CREATED_USER_CODE, BM_CREATED_DATE, BM_FLAG_STATUS, 
                    BM_RECV_DATE_TIME, BM_ROUND_OFF_AMT, BM_BILL_TRANNO, BM_TAX2, BM_TAX3, 
                    BM_PARTY_GROUP_ID, BM_EMPLOYEE_CODE, BM_DISCOUNT, BM_EMPLOYEE_ID
                ) VALUES (
                    '0101', %s, %s, %s, %s, 
                    %s, %s, NOW(), 0, 
                    NOW(), %s, %s, %s, %s, 
                    %s, '624', %s, '23'
                )
            """
            cur.execute(sql_bill_main, (
                bill_no, km_ref_no, max_amount, date1,
                outlet_id, user_code, min_amount, tran_no1, tot_sgst, tot_cgst,
                group_code1, tot_discount
            ))

            # 6. Master Insert: SS_BILL_PAYMENT
            sql_bill_pay = """
                INSERT INTO SS_BILL_PAYMENT (
                    BP_BILL_NO, BP_REF_NO, BP_TRAN_DATE, BP_OUTLET_ID, 
                    BP_CREATED_USER_CODE, BP_CREATED_DATE, BP_FLAG_STATUS, 
                    BP_AMOUNT_PAID, BP_RECV_DATE, BP_PAY_TRANNO, BP_PAY_CODE, BP_PARTY_GROUP_CODE
                ) VALUES (%s, %s, %s, %s, %s, NOW(), 0, %s, NOW(), %s, %s, %s)
            """
            cur.execute(sql_bill_pay, (
                bill_no, km_ref_no, date1, outlet_id, user_code, max_amount, tran_no1, pay_code, group_code1
            ))

            # 7. Customer details if provided
            if customer_name or cus_mobile_no:
                sql_cust = """
                    INSERT INTO SS_ORDERED_CUSTOMER_DETAILS (
                        OCD_OUTLET_ID, OCD_TABLE_NO, OCD_REF_NO, OCD_BILL_NO, 
                        OCD_CUSTOMER_NAME, OCD_MOBILE_NO, OCD_TRAN_DATE, OCD_RECV_DATE_TIME
                    ) VALUES (%s, '1111', %s, %s, %s, %s, %s, NOW())
                """
                cur.execute(sql_cust, (
                    outlet_id, km_ref_no, bill_no, customer_name, cus_mobile_no, date1
                ))

        conn.commit()
        return SaleEntryAddRespResponse(
            status=1,
            message="Sales entry saved successfully",
            bill_no=bill_no,
            ref_no=km_ref_no,
            tran_no=tran_no1,
            grand_total=float(max_amount),
            total_items_saved=items_saved_count,
        )
    except Exception as exc:
        conn.rollback()
        logger.error(f"Error executing sales entry save: {exc}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to save sales entry: {exc}")


# ----------------------------------------------------------------------
# 📡 ENDPOINTS (1:1 Replica of SaleEntryAddResp.jsp)
# ----------------------------------------------------------------------
@router.post(
    "/sale-entry-add-resp",
    response_model=SaleEntryAddRespResponse,
    tags=["Sales Entry – Save Response"],
)
def save_sales_entry_response_post(
    payload: SaleEntryAddRespRequest = Body(...),
):
    """POST Target action endpoint corresponding to `SaleEntryAddResp.jsp`."""
    conn = get_connection()
    try:
        return execute_sale_entry_save(conn, payload)
    finally:
        conn.close()


@router.put(
    "/sale-entry-add-resp",
    response_model=SaleEntryAddRespResponse,
    tags=["Sales Entry – Save Response"],
)
def save_sales_entry_response_put(
    payload: SaleEntryAddRespRequest = Body(...),
):
    """PUT Target action endpoint corresponding to `SaleEntryAddResp.jsp`."""
    conn = get_connection()
    try:
        return execute_sale_entry_save(conn, payload)
    finally:
        conn.close()

