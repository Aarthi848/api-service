#july31
# aug 04
from fastapi import APIRouter, Query, HTTPException, Body, Request, Response
from typing import Optional
from pydantic import BaseModel, Field
from database import get_connection
from logger import get_logger
from config import PAYROLL_DB_CONFIG
import csv
from io import StringIO

logger = get_logger("BankMaster")
router = APIRouter()

# ============================================================
# PYDANTIC MODELS
# ============================================================

class BankAddRequest(BaseModel):
    Bankcode: str
    BankName: str
    Branch: str
    Address1: str
    Address2: Optional[str] = None
    Address3: Optional[str] = None
    Telephone: Optional[str] = None
    FAX: Optional[str] = None
    Contact: Optional[str] = None
    Extension: Optional[str] = None
    PsAlias: Optional[str] = None
    SlipF: Optional[str] = None
    ESTMember: Optional[str] = None

class BankUpdateRequest(BankAddRequest):
    pass   # same fields for update (Bankcode is the key)

class DeleteRequest(BaseModel):
    BankCode: str



# ============================================================
# 7. GET /bankMaster/estOptions – Static dropdown for EST Member
# ============================================================
@router.get("/bankMaster/estOptions")
def get_est_member_options():
    """
    Returns the static options for EST Member dropdown (TRUE/FALSE).
    """
    return {
        "status": 0,
        "message": "Success",
        "options": ["TRUE", "FALSE"]
    }
@router.get("/bankMaster")
def get_bank_master(
    Fcode: Optional[str] = Query(None, description="Filter by Bank Code (partial match)"),
    Fname: Optional[str] = Query(None, description="Filter by Bank Name (partial match)"),
    Fname1: Optional[str] = Query(None, description="Filter by Branch Name (partial match)")
):
    """
    Returns all banks with optional search filters.
    Latest created bank is displayed first.
    """

    con = None
    stmt = None

    try:
        con = get_connection(PAYROLL_DB_CONFIG)
        stmt = con.cursor()

        # --------------------------------------------------
        # WHERE CONDITION
        # --------------------------------------------------

        where = "WHERE BD_FLAG_STATUS <> 2"
        params = []

        if Fcode:
            where += " AND BD_BANK_CODE LIKE %s"
            params.append(f"%{Fcode}%")

        if Fname:
            where += " AND UPPER(BD_BANK_NAME1) LIKE %s"
            params.append(f"%{Fname.upper()}%")

        if Fname1:
            where += " AND UPPER(BD_BRACH_NAME1) LIKE %s"
            params.append(f"%{Fname1.upper()}%")

        # --------------------------------------------------
        # FETCH DATA
        # --------------------------------------------------

        sql = f"""
            SELECT
                BD_BANK_CODE,
                BD_BANK_NAME1,
                BD_BRACH_NAME1,
                BD_ADDRESS1,
                BD_ADDRESS2,
                BD_ADDRESS3,
                BD_TELEPHONE,
                BD_FAX,
                BD_CONTACT,
                BD_EXTENSION,
                BD_ALIAS,
                BD_SLIP_FORMATE,
                BD_EST_MEMBER
            FROM GP_BANK_DETAILS
            {where}
            ORDER BY
                BD_CREATED_DATE DESC,
                CAST(BD_BANK_CODE AS UNSIGNED) DESC
        """

        stmt.execute(sql, params)
        rows = stmt.fetchall()

        bank_list = []

        for idx, row in enumerate(rows, start=1):

            bank_list.append({
                "sno": idx,
                "Bankcode": row["BD_BANK_CODE"],
                "BankName": row["BD_BANK_NAME1"],
                "Branch": row["BD_BRACH_NAME1"],
                "Address1": row["BD_ADDRESS1"],
                "Address2": row["BD_ADDRESS2"],
                "Address3": row["BD_ADDRESS3"],
                "Telephone": row["BD_TELEPHONE"],
                "FAX": row["BD_FAX"],
                "Contact": row["BD_CONTACT"],
                "Extension": row["BD_EXTENSION"],
                "PsAlias": row["BD_ALIAS"],
                "SlipF": row["BD_SLIP_FORMATE"],
                "ESTMember": row["BD_EST_MEMBER"]
            })

        return {
            "status": 0,
            "message": "Success",
            "total_records": len(bank_list),
            "data": bank_list
        }

    except Exception as e:

        logger.error(f"Error in get_bank_master: {str(e)}")

        return {
            "status": 1,
            "message": str(e)
        }

    finally:

        if stmt:
            stmt.close()

        if con:
            con.close()


@router.get("/bankMasteroneview")
def get_bank_master(
    Fcode: Optional[str] = Query(None, description="Filter by Bank Code (partial match)"),
    Fname: Optional[str] = Query(None, description="Filter by Bank Name (partial match)"),
    Fname1: Optional[str] = Query(None, description="Filter by Branch Name (partial match)")
):
    """
    Returns all banks with optional search filters (no pagination).
    Replicates BankMaster.jsp.
    """
    con = None
    stmt = None
    try:
        con = get_connection(PAYROLL_DB_CONFIG)
        stmt = con.cursor()

        # ---- Build WHERE clause ----
        where = "WHERE BD_FLAG_STATUS <> 2"
        params = []
        if Fcode:
            where += " AND BD_BANK_CODE LIKE %s"
            params.append(f"%{Fcode}%")
        if Fname:
            where += " AND UPPER(BD_BANK_NAME1) LIKE %s"
            params.append(f"%{Fname.upper()}%")
        if Fname1:
            where += " AND UPPER(BD_BRACH_NAME1) LIKE %s"
            params.append(f"%{Fname1.upper()}%")

        # ---- Fetch all data ----
        data_sql = f"""
            SELECT BD_BANK_CODE, BD_BANK_NAME1, BD_BRACH_NAME1,
                   BD_CONTACT, BD_TELEPHONE
            FROM GP_BANK_DETAILS
            {where}
            ORDER BY BD_BANK_CODE DESC
        """
        stmt.execute(data_sql, params)
        rows = stmt.fetchall()

        # Build serial number
        bank_list = []
        for idx, row in enumerate(rows, start=1):
            bank_list.append({
                "sno": idx,
                "bank_code": row["BD_BANK_CODE"],
                "bank_name": row["BD_BANK_NAME1"],
                "branch_name": row["BD_BRACH_NAME1"],
                "contact": row["BD_CONTACT"],
                "telephone": row["BD_TELEPHONE"]
            })

        stmt.close()
        con.close()

        return {
            "status": 0,
            "message": "Success",
            "data": {
                "banks": bank_list,
                "total_records": len(bank_list)
            }
        }

    except Exception as e:
        logger.error(f"Error in get_bank_master: {str(e)}")
        return {"status": 1, "message": str(e)}

# ============================================================
# 2. GET /bankMaster/{bank_code} – View single bank
# ============================================================
@router.get("/bankMaster/{bank_code}")
def get_bank_by_code(bank_code: str):
    con = None
    stmt = None

    try:
        con = get_connection(PAYROLL_DB_CONFIG)
        stmt = con.cursor()

        stmt.execute("""
            SELECT
                BD_BANK_NAME1,
                BD_BRACH_NAME1,
                BD_ADDRESS1,
                BD_ADDRESS2,
                BD_ADDRESS3,
                BD_TELEPHONE,
                BD_FAX,
                BD_CONTACT,
                BD_EXTENSION,
                BD_SLIP_FORMATE,
                BD_ALIAS,
                BD_EST_MEMBER
            FROM GP_BANK_DETAILS
            WHERE BD_FLAG_STATUS <> 2
            AND BD_BANK_CODE=%s
        """, (bank_code,))

        row = stmt.fetchone()

        print("ROW =", row)

        if row:
            print("TYPE =", type(row))

            try:
                print("KEYS =", row.keys())
            except Exception:
                pass

        if not row:
            raise HTTPException(status_code=404, detail="Bank not found")

        return {
            "status": 0,
            "data": {
                "bank_code": bank_code,
                "bank_name": row["BD_BANK_NAME1"],
                "branch": row["BD_BRACH_NAME1"],
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()      # <-- VERY IMPORTANT
        logger.exception(e)
        raise
# ============================================================
# 3. POST /bankMaster – Add new bank
# ============================================================

@router.post("/bankMaster")
def add_bank(req: BankAddRequest, request: Request):

    con = None
    stmt = None

    try:
        con = get_connection(PAYROLL_DB_CONFIG)
        stmt = con.cursor()
        con.autocommit(False)

        UserCode = "1"  # Replace with logged-in user if available
        ip_add = request.client.host

        BankCode = req.Bankcode.strip()
        BankName = req.BankName.strip()
        Branch = req.Branch.strip()
        Address1 = req.Address1.strip()

        Address2 = req.Address2.strip() if req.Address2 else ""
        Address3 = req.Address3.strip() if req.Address3 else ""
        TelPhone = req.Telephone.strip() if req.Telephone else ""
        Fax = req.FAX.strip() if req.FAX else ""
        Contact = req.Contact.strip() if req.Contact else ""
        Extension = req.Extension.strip() if req.Extension else ""
        Alias = req.PsAlias.strip() if req.PsAlias else ""

        # Default values
        Slip = req.SlipF.strip().upper() if req.SlipF and req.SlipF.strip() else "Y"
        EST = req.ESTMember.strip().upper() if req.ESTMember and req.ESTMember.strip() else "Y"

        # --------------------------------------------------
        # Duplicate Bank Code Check
        # --------------------------------------------------

        stmt.execute("""
            SELECT COUNT(*) AS CNT
            FROM GP_BANK_DETAILS
            WHERE BD_BANK_CODE = %s
            AND BD_FLAG_STATUS <> 2
        """, (BankCode,))

        if stmt.fetchone()["CNT"] > 0:
            con.rollback()
            return {
                "status": 1,
                "message": "Bank Code Already Exists"
            }

        # --------------------------------------------------
        # Duplicate Bank Name Check
        # --------------------------------------------------

        stmt.execute("""
            SELECT COUNT(*) AS CNT
            FROM GP_BANK_DETAILS
            WHERE UPPER(BD_BANK_NAME1)=UPPER(%s)
            AND BD_FLAG_STATUS <> 2
        """, (BankName,))

        if stmt.fetchone()["CNT"] > 0:
            con.rollback()
            return {
                "status": 1,
                "message": "Bank Name Already Exists"
            }

        # --------------------------------------------------
        # Get Reference ID
        # --------------------------------------------------

        stmt.execute("""
            SELECT IFNULL(MAX(HR_REF_ID),0)+1 AS MAXID
            FROM GP_VIEW_HISTORY
        """)

        ref_id = stmt.fetchone()["MAXID"]

        # --------------------------------------------------
        # Insert Master
        # --------------------------------------------------

        stmt.execute("""
            INSERT INTO GP_BANK_DETAILS
            (
                BD_BANK_CODE,
                BD_BANK_NAME1,
                BD_BRACH_NAME1,
                BD_ADDRESS1,
                BD_ADDRESS2,
                BD_ADDRESS3,
                BD_TELEPHONE,
                BD_FAX,
                BD_CONTACT,
                BD_EXTENSION,
                BD_SLIP_FORMATE,
                BD_ALIAS,
                BD_EST_MEMBER,
                BD_FLAG_STATUS,
                BD_CREATED_DATE,
                BD_CREATED_USER_CODE
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                0,
                NOW(),
                %s
            )
        """, (
            BankCode,
            BankName,
            Branch,
            Address1,
            Address2,
            Address3,
            TelPhone,
            Fax,
            Contact,
            Extension,
            Slip,
            Alias,
            EST,
            UserCode
        ))

        # --------------------------------------------------
        # Insert View History
        # --------------------------------------------------

        stmt.execute("""
            INSERT INTO GP_VIEW_HISTORY
            (
                HR_REF_ID,
                HR_ID,
                HR_MODULE,
                HR_MASTER,
                HR_IP_ADDRESS,
                HR_CREATED_DATE,
                HR_CREATED_USER_CODE,
                HR_STATUS
            )
            VALUES
            (
                %s,
                %s,
                '01',
                '10',
                %s,
                NOW(),
                %s,
                1
            )
        """, (
            ref_id,
            BankCode,
            ip_add,
            UserCode
        ))

        # --------------------------------------------------
        # Insert History
        # --------------------------------------------------

        stmt.execute("""
            INSERT INTO GP_BANK_DETAILS_HIS
            (
                BD_BANK_CODE,
                BD_BANK_NAME1,
                BD_BRACH_NAME1,
                BD_ADDRESS1,
                BD_ADDRESS2,
                BD_ADDRESS3,
                BD_TELEPHONE,
                BD_FAX,
                BD_CONTACT,
                BD_EXTENSION,
                BD_SLIP_FORMATE,
                BD_ALIAS,
                BD_EST_MEMBER,
                BD_FLAG_STATUS,
                BD_CREATED_DATE,
                BD_CREATED_USER_CODE,
                BD_REF_ID,
                BD_IP_ADD
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                0,
                NOW(),
                %s,
                %s,
                %s
            )
        """, (
            BankCode,
            BankName,
            Branch,
            Address1,
            Address2,
            Address3,
            TelPhone,
            Fax,
            Contact,
            Extension,
            Slip,
            Alias,
            EST,
            UserCode,
            ref_id,
            ip_add
        ))

        con.commit()

        return {
            "status": 0,
            "message": "Added Successfully",
            "bank_code": BankCode
        }

    except Exception as e:

        if con:
            con.rollback()

        logger.exception("Error in add_bank")

        return {
            "status": 1,
            "message": str(e)
        }

    finally:

        if stmt:
            stmt.close()

        if con:
            con.close()


# ============================================================
# 4. PUT /bankMaster/{bank_code} – Update bank
# ============================================================
@router.put("/bankMaster/{bank_code}")
def update_bank(bank_code: str, req: BankUpdateRequest, request: Request):
    """
    Updates an existing bank record.
    Replicates BankMasterEditResp.jsp
    """

    con = None
    stmt = None

    try:
        con = get_connection(PAYROLL_DB_CONFIG)
        stmt = con.cursor()
        con.autocommit = False

        UserCode = "1"

        BankCode = bank_code.strip()
        BankName = req.BankName.strip() if req.BankName else ""
        Branch = req.Branch.strip() if req.Branch else ""
        Address1 = req.Address1.strip() if req.Address1 else ""
        Address2 = req.Address2.strip() if req.Address2 else ""
        Address3 = req.Address3.strip() if req.Address3 else ""
        TelPhone = req.Telephone.strip() if req.Telephone else ""
        Fax = req.FAX.strip() if req.FAX else ""
        Contact = req.Contact.strip() if req.Contact else ""
        Extension = req.Extension.strip() if req.Extension else ""
        Alias = req.PsAlias.strip() if req.PsAlias else ""
        Slip = req.SlipF.strip() if req.SlipF else ""
        EST = req.ESTMember.strip() if req.ESTMember else ""

        count = 0

        # -------------------------------------------------
        # Check Record Exists
        # -------------------------------------------------
        stmt.execute(
            """
            SELECT 1
            FROM GP_BANK_DETAILS
            WHERE BD_BANK_CODE=%s
            AND BD_FLAG_STATUS<>2
            """,
            (BankCode,)
        )

        if not stmt.fetchone():
            raise HTTPException(status_code=404, detail="Bank not found")

        # -------------------------------------------------
        # UPDATE GP_BANK_DETAILS
        # -------------------------------------------------
        sql = """
        UPDATE GP_BANK_DETAILS
        SET
            BD_BANK_NAME1=%s,
            BD_BRACH_NAME1=%s,
            BD_ADDRESS1=%s,
            BD_ADDRESS2=%s,
            BD_ADDRESS3=%s,
            BD_TELEPHONE=%s,
            BD_FAX=%s,
            BD_CONTACT=%s,
            BD_EXTENSION=%s,
            BD_SLIP_FORMATE=%s,
            BD_ALIAS=%s,
            BD_EST_MEMBER=%s,
            BD_FLAG_STATUS=1,
            BD_MODIFIED_DATE=NOW(),
            BD_MODIFIED_USER_CODE=%s
        WHERE BD_BANK_CODE=%s
        """

        count += stmt.execute(sql, (
            BankName,
            Branch,
            Address1,
            Address2,
            Address3,
            TelPhone,
            Fax,
            Contact,
            Extension,
            Slip,
            Alias,
            EST,
            UserCode,
            BankCode
        ))

        # -------------------------------------------------
        # GET NEXT REF ID
        # -------------------------------------------------
        stmt.execute(
            "SELECT IFNULL(MAX(HR_REF_ID),0)+1 AS MAXID FROM GP_VIEW_HISTORY"
        )

        ref_row = stmt.fetchone()
        ref_id = ref_row["MAXID"]

        ip_add = request.client.host

        # -------------------------------------------------
        # INSERT GP_VIEW_HISTORY
        # -------------------------------------------------
        sql = """
        INSERT INTO GP_VIEW_HISTORY
        (
            HR_REF_ID,
            HR_ID,
            HR_MODULE,
            HR_MASTER,
            HR_IP_ADDRESS,
            HR_CREATED_DATE,
            HR_CREATED_USER_CODE,
            HR_STATUS
        )
        VALUES
        (
            %s,%s,'01','10',%s,NOW(),%s,2
        )
        """

        count += stmt.execute(sql, (
            ref_id,
            BankCode,
            ip_add,
            UserCode
        ))

        # -------------------------------------------------
        # INSERT GP_BANK_DETAILS_HIS
        # -------------------------------------------------
        sql = """
        INSERT INTO GP_BANK_DETAILS_HIS
        (
            BD_BANK_CODE,
            BD_BANK_NAME1,
            BD_BRACH_NAME1,
            BD_ADDRESS1,
            BD_ADDRESS2,
            BD_ADDRESS3,
            BD_TELEPHONE,
            BD_FAX,
            BD_CONTACT,
            BD_EXTENSION,
            BD_SLIP_FORMATE,
            BD_ALIAS,
            BD_EST_MEMBER,
            BD_FLAG_STATUS,
            BD_CREATED_DATE,
            BD_CREATED_USER_CODE,
            BD_REF_ID,
            BD_IP_ADD
        )
        VALUES
        (
            %s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            1,
            NOW(),
            %s,%s,%s
        )
        """

        count += stmt.execute(sql, (
            BankCode,
            BankName,
            Branch,
            Address1,
            Address2,
            Address3,
            TelPhone,
            Fax,
            Contact,
            Extension,
            Slip,
            Alias,
            EST,
            UserCode,
            ref_id,
            ip_add
        ))

        # -------------------------------------------------
        # SAME JSP LOGIC
        # -------------------------------------------------
        if count == 3:
            con.commit()

            return {
                "status": 0,
                "message": "Updated Successfully"
            }

        else:
            con.rollback()

            return {
                "status": 1,
                "message": "Updation Failed"
            }

    except HTTPException:
        if con:
            con.rollback()
        raise

    except Exception as e:
        if con:
            con.rollback()

        logger.exception("Update Bank Error")

        return {
            "status": 1,
            "message": str(e)
        }

    finally:
        if stmt:
            stmt.close()

        if con:
            con.close()


# ============================================================
# 5. DELETE /bankMaster/{bank_code} – Soft delete
# ============================================================
@router.delete("/bankMaster/{bank_code}")
def delete_bank(bank_code: str, request: Request):
    """
    Soft deletes a bank by setting BD_FLAG_STATUS = 2.
    Replicates BankMasterDelete.jsp.
    """
    con = None
    stmt = None
    try:
        con = get_connection(PAYROLL_DB_CONFIG)
        stmt = con.cursor()
        con.autocommit = False

        UserCode = "1"
        BankCode = bank_code.strip()

        # ---- Check if exists ----
        stmt.execute("SELECT 1 FROM GP_BANK_DETAILS WHERE BD_BANK_CODE = %s AND BD_FLAG_STATUS <> 2",
                     (BankCode,))
        if not stmt.fetchone():
            raise HTTPException(status_code=404, detail="Bank not found or already deleted")

        # ---- Get next reference ID ----
        stmt.execute("SELECT IFNULL(MAX(HR_REF_ID),0)+1 AS MAXID FROM GP_VIEW_HISTORY")
        ref_id = stmt.fetchone()["MAXID"]

        # ---- Insert into GP_VIEW_HISTORY (delete status=3) ----
        ip_add = request.client.host
        sql1 = """
            INSERT INTO GP_VIEW_HISTORY
            (HR_REF_ID, HR_ID, HR_MODULE, HR_MASTER, HR_IP_ADDRESS,
             HR_CREATED_DATE, HR_CREATED_USER_CODE, HR_STATUS)
            VALUES (%s, %s, '01', '10', %s, NOW(), %s, 3)
        """
        stmt.execute(sql1, (ref_id, BankCode, ip_add, UserCode))

        # ---- Soft delete from GP_BANK_DETAILS ----
        sql2 = """
            UPDATE GP_BANK_DETAILS
            SET BD_FLAG_STATUS = 2,
                BD_MODIFIED_DATE = NOW(),
                BD_MODIFIED_USER_CODE = %s
            WHERE BD_BANK_CODE = %s
        """
        stmt.execute(sql2, (UserCode, BankCode))

        # ---- Select data for history ----
        stmt.execute("""
            SELECT BD_BANK_NAME1, BD_BRACH_NAME1, BD_ADDRESS1, BD_ADDRESS2, BD_ADDRESS3,
                   BD_TELEPHONE, BD_FAX, BD_CONTACT, BD_EXTENSION,
                   BD_SLIP_FORMATE, BD_ALIAS, BD_EST_MEMBER
            FROM GP_BANK_DETAILS
            WHERE BD_BANK_CODE = %s
        """, (BankCode,))
        row = stmt.fetchone()
        if row:
            # ---- Insert into GP_BANK_DETAILS_HIS with flag 2 ----
            sql3 = """
                INSERT INTO GP_BANK_DETAILS_HIS
                (BD_BANK_CODE, BD_BANK_NAME1, BD_BRACH_NAME1, BD_ADDRESS1,
                 BD_ADDRESS2, BD_ADDRESS3, BD_TELEPHONE, BD_FAX,
                 BD_CONTACT, BD_EXTENSION, BD_SLIP_FORMATE, BD_ALIAS,
                 BD_EST_MEMBER, BD_FLAG_STATUS, BD_CREATED_DATE,
                 BD_CREATED_USER_CODE, BD_REF_ID, BD_IP_ADD)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, 2, NOW(), %s, %s, %s)
            """
            params3 = (BankCode, row["BD_BANK_NAME1"], row["BD_BRACH_NAME1"], row["BD_ADDRESS1"], row["BD_ADDRESS2"], row["BD_ADDRESS3"],
                       row["BD_TELEPHONE"], row["BD_FAX"], row["BD_CONTACT"], row["BD_EXTENSION"], row["BD_SLIP_FORMATE"], row["BD_ALIAS"], row["BD_EST_MEMBER"],
                       UserCode, ref_id, ip_add)
            stmt.execute(sql3, params3)

        con.commit()
        stmt.close()
        con.close()

        logger.info(f"Deleted bank {BankCode} by user {UserCode}")
        return {"status": 0, "message": "Deleted Successfully"}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in delete_bank: {str(e)}")
        if con:
            con.rollback()
        return {"status": 1, "message": "Deletion Failed"}


# ============================================================
# 6. GET /bankMaster/export – CSV Export
# ============================================================
@router.get("/bankMaster/export")
def export_banks():
    """
    Exports all active banks (ID, Name, Branch, Contact, Telephone) as CSV.
    Replicates BankMasterExport.jsp.
    """
    con = None
    stmt = None
    try:
        con = get_connection(PAYROLL_DB_CONFIG)
        stmt = con.cursor()

        stmt.execute("""
            SELECT BD_BANK_CODE, BD_BANK_NAME1, BD_BRACH_NAME1,
                   BD_CONTACT, BD_TELEPHONE
            FROM GP_BANK_DETAILS
            WHERE BD_FLAG_STATUS <> 2
            ORDER BY BD_BANK_CODE
        """)
        rows = stmt.fetchall()

        stmt.close()
        con.close()

        # ---- Generate CSV ----
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Bank Code", "Bank Name", "Branch", "Contact", "Telephone"])
        for row in rows:
            writer.writerow([
                row["BD_BANK_CODE"],
                row["BD_BANK_NAME1"],
                row["BD_BRACH_NAME1"],
                row["BD_CONTACT"] or "",
                row["BD_TELEPHONE"] or ""
            ])

        csv_content = output.getvalue()
        output.close()

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=bank_master.csv"}
        )

    except Exception as e:
        logger.error(f"Error in export_banks: {str(e)}")
        return {"status": 1, "message": str(e)}



