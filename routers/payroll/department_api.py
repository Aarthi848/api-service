#july31
# aug 04
from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional

from pydantic.v1 import BaseModel
from database import get_connection
from config import PAYROLL_DB_CONFIG
from logger import get_logger
import pymysql

logger = get_logger("department_api")

router = APIRouter()

# -------------------------------
# MODELS
# -------------------------------
from pydantic import BaseModel

class DepartmentCreate(BaseModel):
    department_name: str
    user_code: str
    
    
class DepartmentUpdate(BaseModel):
    department_id: str
    department_name: str
    user_code: str = "1"   

class DepartmentDelete(BaseModel):
    department_id: str
    user_code: str = "1"     

# -------------------------------
# GET → FETCH ALL
# -------------------------------
@router.get("/department")
def get_departments(
    dept_name: Optional[str] = Query(None, description="Search Department Name")
):
    con = None
    stmt = None

    try:
        con = get_connection(PAYROLL_DB_CONFIG)
        stmt = con.cursor()

        where = "WHERE DM_FLAG_STATUS <> 2"
        params = []

        if dept_name and dept_name.strip():
            where += " AND UPPER(DM_DEPARTMENT_NAME) LIKE %s"
            params.append(f"%{dept_name.strip().upper()}%")

        sql = f"""
            SELECT
                DM_DEPARTMENT_ID,
                DM_DEPARTMENT_NAME
            FROM GP_EMP_DEPARTMENT_MASTER
            {where}
            ORDER BY CAST(DM_DEPARTMENT_ID AS UNSIGNED) DESC
        """

        stmt.execute(sql, params)
        rows = stmt.fetchall()

        departments = []

        sno = 1

        for row in rows:
            departments.append({
                "sno": sno,
                "department_id": row["DM_DEPARTMENT_ID"],
                "department_name": row["DM_DEPARTMENT_NAME"]
            })
            sno += 1

        return {
            "status": 0,
            "message": "Success",
            "total_records": len(departments),
            "data": departments
        }

    except Exception as e:
        logger.exception("Error in get_departments")

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
# ADD  – POST 
# ============================================================  

@router.post("/department")
def add_department(req: DepartmentCreate, request: Request):

    con = None
    stmt = None

    try:
        con = get_connection(PAYROLL_DB_CONFIG)
        stmt = con.cursor()
        con.autocommit(False)

        count = 0

        DepartmentName = req.department_name.strip()
        UserCode = req.user_code.strip()

        # --------------------------------------------------
        # AUTO GENERATE DEPARTMENT ID
        # --------------------------------------------------

        stmt.execute("""
            SELECT
                IFNULL(MAX(CAST(DM_DEPARTMENT_ID AS UNSIGNED)), 0) + 1 AS NEXT_ID
            FROM GP_EMP_DEPARTMENT_MASTER
            WHERE CAST(DM_DEPARTMENT_ID AS UNSIGNED) < 1000
        """)

        row = stmt.fetchone()

        DepartmentId = str(row["NEXT_ID"])

        print("Generated Department ID :", DepartmentId)

        # --------------------------------------------------
        # DUPLICATE NAME CHECK
        # --------------------------------------------------

        stmt.execute("""
            SELECT COUNT(*) AS CNT
            FROM GP_EMP_DEPARTMENT_MASTER
            WHERE UPPER(DM_DEPARTMENT_NAME)=UPPER(%s)
        """, (DepartmentName,))

        if stmt.fetchone()["CNT"] > 0:

            con.rollback()

            return {
                "status": 1,
                "message": "Name Already Exists"
            }

        # --------------------------------------------------
        # INSERT MASTER
        # --------------------------------------------------

        sql = """
            INSERT INTO GP_EMP_DEPARTMENT_MASTER
            (
                DM_DEPARTMENT_ID,
                DM_DEPARTMENT_NAME,
                DM_FLAG_STATUS,
                DM_SEND_FLAG,
                DM_CREATED_DATE,
                DM_CREATED_USER_CODE
            )
            VALUES
            (
                %s,
                %s,
                0,
                0,
                NOW(),
                %s
            )
        """

        count += stmt.execute(
            sql,
            (
                DepartmentId,
                DepartmentName,
                UserCode
            )
        )

        # --------------------------------------------------
        # GET NEXT REF ID
        # --------------------------------------------------

        stmt.execute("""
            SELECT IFNULL(MAX(HR_REF_ID),0)+1 AS MAXID
            FROM GP_VIEW_HISTORY
        """)

        RefId = stmt.fetchone()["MAXID"]

        ip_add = request.client.host

        # --------------------------------------------------
        # INSERT VIEW HISTORY
        # --------------------------------------------------

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
                %s,
                %s,
                '01',
                '04',
                %s,
                NOW(),
                %s,
                1
            )
        """

        count += stmt.execute(
            sql,
            (
                RefId,
                DepartmentId,
                ip_add,
                UserCode
            )
        )

        # --------------------------------------------------
        # INSERT HISTORY
        # --------------------------------------------------

        sql = """
            INSERT INTO GP_EMP_DEPARTMENT_MASTER_HIS
            (
                EDM_DEPARTMENT_ID,
                EDM_DEPARTMENT_NAME,
                EDM_FLAG_STATUS,
                EDM_SEND_FLAG,
                EDM_CREATED_DATE,
                EDM_CREATED_USER_CODE,
                EDM_REF_ID,
                EDM_IP_ADD
            )
            VALUES
            (
                %s,
                %s,
                0,
                0,
                NOW(),
                %s,
                %s,
                %s
            )
        """

        count += stmt.execute(
            sql,
            (
                DepartmentId,
                DepartmentName,
                UserCode,
                RefId,
                ip_add
            )
        )

        # --------------------------------------------------
        # COMMIT
        # --------------------------------------------------

        if count == 3:

            con.commit()

            return {
                "status": 0,
                "message": "Added Successfully",
                "department_id": DepartmentId
            }

        else:

            con.rollback()

            return {
                "status": 1,
                "message": "Insertion Failed"
            }

    except Exception as e:

        if con:
            con.rollback()

        logger.exception("Error in add_department")

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
# PUT – UPDATE
# ============================================================

@router.put("/department")
def update_department(req: DepartmentUpdate, request: Request):

    con = None
    stmt = None

    try:
        con = get_connection(PAYROLL_DB_CONFIG)
        stmt = con.cursor()
        con.autocommit(False)

        count = 0

        DepartmentId = req.department_id.strip().upper()
        DepartmentName = req.department_name.strip()
        UserCode = req.user_code.strip()

        # --------------------------------------------------
        # DUPLICATE NAME CHECK
        # --------------------------------------------------

        stmt.execute("""
            SELECT COUNT(*) AS CNT
            FROM GP_EMP_DEPARTMENT_MASTER
            WHERE UPPER(DM_DEPARTMENT_NAME)=%s
            AND DM_DEPARTMENT_ID<>%s
        """, (DepartmentName.upper(), DepartmentId))

        duplicate = stmt.fetchone()["CNT"]

        if duplicate > 0:
            con.rollback()
            return {
                "status": 1,
                "message": "Name Already Exists"
            }

        # --------------------------------------------------
        # UPDATE MASTER
        # --------------------------------------------------

        sql = """
            UPDATE GP_EMP_DEPARTMENT_MASTER
            SET
                DM_DEPARTMENT_NAME=%s,
                DM_FLAG_STATUS=1,
                DM_SEND_FLAG=0,
                DM_MODIFIED_DATE=NOW(),
                DM_MODIFIED_USER_CODE=%s
            WHERE DM_DEPARTMENT_ID=%s
        """

        count += stmt.execute(
            sql,
            (
                DepartmentName,
                UserCode,
                DepartmentId
            )
        )

        # --------------------------------------------------
        # GET NEXT REF ID
        # --------------------------------------------------

        stmt.execute("""
            SELECT IFNULL(MAX(HR_REF_ID),0)+1 AS MAXID
            FROM GP_VIEW_HISTORY
        """)

        RefId = stmt.fetchone()["MAXID"]

        ip_add = request.client.host

        # --------------------------------------------------
        # INSERT VIEW HISTORY
        # --------------------------------------------------

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
                %s,
                %s,
                '01',
                '04',
                %s,
                NOW(),
                %s,
                2
            )
        """

        count += stmt.execute(
            sql,
            (
                RefId,
                DepartmentId,
                ip_add,
                UserCode
            )
        )

        # --------------------------------------------------
        # INSERT HISTORY
        # --------------------------------------------------

        sql = """
            INSERT INTO GP_EMP_DEPARTMENT_MASTER_HIS
            (
                EDM_DEPARTMENT_ID,
                EDM_DEPARTMENT_NAME,
                EDM_FLAG_STATUS,
                EDM_SEND_FLAG,
                EDM_CREATED_DATE,
                EDM_CREATED_USER_CODE,
                EDM_REF_ID,
                EDM_IP_ADD
            )
            VALUES
            (
                %s,
                %s,
                1,
                0,
                NOW(),
                %s,
                %s,
                %s
            )
        """

        count += stmt.execute(
            sql,
            (
                DepartmentId,
                DepartmentName,
                UserCode,
                RefId,
                ip_add
            )
        )

        # --------------------------------------------------
        # COMMIT
        # --------------------------------------------------

        if count == 3:

            con.commit()

            return {
                "status": 0,
                "message": "Successfully Updated"
            }

        else:

            con.rollback()

            return {
                "status": 1,
                "message": "Updation Failed"
            }

    except Exception as e:

        if con:
            con.rollback()

        logger.exception("Error in update_department")

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
# DELETE
# ============================================================

@router.delete("/department")
def delete_department(req: DepartmentDelete, request: Request):

    con = None
    stmt = None

    try:
        con = get_connection(PAYROLL_DB_CONFIG)
        stmt = con.cursor()
        con.autocommit(False)

        count = 0

        DepartmentId = req.department_id.strip().upper()
        UserCode = req.user_code.strip()

        # --------------------------------------------------
        # CHECK CHILD RECORD
        # --------------------------------------------------

        stmt.execute("""
            SELECT COUNT(*) AS CNT
            FROM GP_EMPLOYEE_MASTER
            WHERE EM_DEPARTMENT=%s
        """, (DepartmentId,))

        child_count = stmt.fetchone()["CNT"]

        if child_count > 0:

            con.rollback()

            return {
                "status": 1,
                "message": "Child Record Found"
            }

        # --------------------------------------------------
        # GET DEPARTMENT NAME
        # --------------------------------------------------

        stmt.execute("""
            SELECT DM_DEPARTMENT_NAME
            FROM GP_EMP_DEPARTMENT_MASTER
            WHERE DM_DEPARTMENT_ID=%s
        """, (DepartmentId,))

        row = stmt.fetchone()

        if not row:

            con.rollback()

            return {
                "status": 1,
                "message": "Department Not Found"
            }

        DepartmentName = row["DM_DEPARTMENT_NAME"]

        # --------------------------------------------------
        # SOFT DELETE MASTER
        # --------------------------------------------------

        sql = """
            UPDATE GP_EMP_DEPARTMENT_MASTER
            SET
                DM_MODIFIED_USER_CODE=%s,
                DM_MODIFIED_DATE=NOW(),
                DM_FLAG_STATUS=2,
                DM_SEND_FLAG=0
            WHERE DM_DEPARTMENT_ID=%s
        """

        count += stmt.execute(
            sql,
            (
                UserCode,
                DepartmentId
            )
        )

        # --------------------------------------------------
        # GET NEXT REF ID
        # --------------------------------------------------

        stmt.execute("""
            SELECT IFNULL(MAX(HR_REF_ID),0)+1 AS MAXID
            FROM GP_VIEW_HISTORY
        """)

        RefId = stmt.fetchone()["MAXID"]

        ip_add = request.client.host

        # --------------------------------------------------
        # INSERT VIEW HISTORY
        # --------------------------------------------------

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
                %s,
                %s,
                '01',
                '04',
                %s,
                NOW(),
                %s,
                3
            )
        """

        count += stmt.execute(
            sql,
            (
                RefId,
                DepartmentId,
                ip_add,
                UserCode
            )
        )

        # --------------------------------------------------
        # INSERT HISTORY
        # --------------------------------------------------

        sql = """
            INSERT INTO GP_EMP_DEPARTMENT_MASTER_HIS
            (
                EDM_DEPARTMENT_ID,
                EDM_DEPARTMENT_NAME,
                EDM_FLAG_STATUS,
                EDM_SEND_FLAG,
                EDM_CREATED_DATE,
                EDM_CREATED_USER_CODE,
                EDM_REF_ID,
                EDM_IP_ADD
            )
            VALUES
            (
                %s,
                %s,
                2,
                0,
                NOW(),
                %s,
                %s,
                %s
            )
        """

        count += stmt.execute(
            sql,
            (
                DepartmentId,
                DepartmentName,
                UserCode,
                RefId,
                ip_add
            )
        )

        # --------------------------------------------------
        # COMMIT
        # --------------------------------------------------

        if count == 3:

            con.commit()

            return {
                "status": 0,
                "message": "Deleted Successfully"
            }

        else:

            con.rollback()

            return {
                "status": 1,
                "message": "Deletion Failed"
            }

    except Exception as e:

        if con:
            con.rollback()

        logger.exception("Error in delete_department")

        return {
            "status": 1,
            "message": str(e)
        }

    finally:

        if stmt:
            stmt.close()

        if con:
            con.close()
