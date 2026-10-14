# aug 04
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse
import math
from pydantic import BaseModel
from typing import Optional, List
import traceback

from database import get_connection
from logger import get_logger

from fastapi import APIRouter, HTTPException, Body
from config import PAYROLL_DB_CONFIG

router = APIRouter()

logger = get_logger("designation_api_payroll")


# --- Pydantic Schemas ---
# class DesignationCreate(BaseModel):
#     dep_id: str
#     dep_name: str
#     user_code: str = "1"

class DesignationCreate(BaseModel):
    dep_name: str
    user_code: str = "1"

class DesignationUpdate(BaseModel):
    dep_id: str
    dep_name: str
    user_code: str = "1"

class DesignationResponse(BaseModel):
    id: str
    name: str

class DesignationListResponse(BaseModel):
    data: List[DesignationResponse]
    total_count: int
    total_pages: int
    current_page: int
    limit: int

@router.get("/designations")
def get_designations(
    dept_name: Optional[str] = Query(
        None,
        description="Filter by Designation Name (partial)"
    )
):
    """
    Returns all designations.
    Latest created designation is displayed first.
    """

    conn = None
    cursor = None

    try:
        conn = get_connection(PAYROLL_DB_CONFIG)
        cursor = conn.cursor()

        # --------------------------------------------------
        # WHERE CONDITION
        # --------------------------------------------------

        where = "WHERE DSM_FLAG_STATUS <> 2"
        params = []

        if dept_name:
            where += " AND UPPER(DSM_DESIGNATION_NAME) LIKE %s"
            params.append(f"%{dept_name.upper()}%")

        # --------------------------------------------------
        # FETCH DATA
        # --------------------------------------------------

        sql = f"""
            SELECT
                DSM_DESIGNATION_ID,
                DSM_DESIGNATION_NAME
            FROM GP_EMP_DESIGNATION_MASTER
            {where}
            ORDER BY CAST(DSM_DESIGNATION_ID AS UNSIGNED) DESC
        """

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        designation_list = []

        for idx, row in enumerate(rows, start=1):
            designation_list.append({
                "sno": idx,
                "designation_id": row["DSM_DESIGNATION_ID"],
                "designation_name": row["DSM_DESIGNATION_NAME"]
            })

        return {
            "status": 0,
            "message": "Success",
            "total_records": len(designation_list),
            "data": designation_list
        }

    except Exception as e:
        logger.error(f"GET /designations Error: {str(e)}")
        return {
            "status": 1,
            "message": str(e)
        }

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

@router.get("/designations/{designation_id}", response_model=DesignationResponse)
def get_designation(designation_id: str):
    try:
        logger.debug(f"GET /designations/{designation_id} Request")

        connection = get_connection(PAYROLL_DB_CONFIG)
        cursor = connection.cursor()

        sql = "SELECT DSM_DESIGNATION_ID, DSM_DESIGNATION_NAME FROM GP_EMP_DESIGNATION_MASTER WHERE DSM_FLAG_STATUS <> 2 AND DSM_DESIGNATION_ID = %s"
        logger.debug(f"SQL: {sql}")
        logger.debug(f"Params: [{designation_id}]")
        cursor.execute(sql, [designation_id])
        record = cursor.fetchone()

        if not record:
            logger.debug("Designation not found")
            cursor.close()
            connection.close()
            raise HTTPException(status_code=404, detail="Designation not found")

        response = DesignationResponse(id=str(record['DSM_DESIGNATION_ID']), name=record['DSM_DESIGNATION_NAME'])
        logger.debug(f"Response: {response}")

        cursor.close()
        connection.close()

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /designations/{designation_id} Error:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/designations")
def create_designation(req: DesignationCreate, request: Request):

    connection = None
    cursor = None

    try:

        connection = get_connection(PAYROLL_DB_CONFIG)
        cursor = connection.cursor()
        connection.autocommit(False)

        ip_add = request.client.host if request.client else "127.0.0.1"

        # --------------------------------------------------
        # AUTO GENERATE DESIGNATION ID
        # --------------------------------------------------

        cursor.execute("""
            SELECT
                IFNULL(MAX(CAST(DSM_DESIGNATION_ID AS UNSIGNED)),0)+1 AS NEXT_ID
            FROM GP_EMP_DESIGNATION_MASTER
        """)

        designation_id = str(cursor.fetchone()["NEXT_ID"])

        # --------------------------------------------------
        # DUPLICATE NAME CHECK
        # --------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS CNT
            FROM GP_EMP_DESIGNATION_MASTER
            WHERE UPPER(DSM_DESIGNATION_NAME)=UPPER(%s)
            AND DSM_FLAG_STATUS <> 2
        """, (req.dep_name.strip(),))

        if cursor.fetchone()["CNT"] > 0:

            connection.rollback()

            return {
                "status": 1,
                "message": "Name Already Exists"
            }

        # --------------------------------------------------
        # INSERT MASTER
        # --------------------------------------------------

        cursor.execute("""
            INSERT INTO GP_EMP_DESIGNATION_MASTER
            (
                DSM_DESIGNATION_ID,
                DSM_DESIGNATION_NAME,
                DSM_FLAG_STATUS,
                DSM_SEND_FLAG,
                DSM_CREATED_DATE,
                DSM_CREATED_USER_CODE
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
        """, (
            designation_id,
            req.dep_name.strip(),
            req.user_code
        ))

        # --------------------------------------------------
        # GET NEXT REF ID
        # --------------------------------------------------

        cursor.execute("""
            SELECT IFNULL(MAX(HR_REF_ID),0)+1 AS MAXID
            FROM GP_VIEW_HISTORY
        """)

        ref_id = cursor.fetchone()["MAXID"]

        # --------------------------------------------------
        # INSERT VIEW HISTORY
        # --------------------------------------------------

        cursor.execute("""
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
                '05',
                %s,
                NOW(),
                %s,
                1
            )
        """, (
            ref_id,
            designation_id,
            ip_add,
            req.user_code
        ))

        # --------------------------------------------------
        # INSERT HISTORY
        # --------------------------------------------------

        cursor.execute("""
            INSERT INTO GP_EMP_DESIGNATION_MASTER_HIS
            (
                EDM_DESIGNATION_ID,
                EDM_DESIGNATION_NAME,
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
        """, (
            designation_id,
            req.dep_name.strip(),
            req.user_code,
            ref_id,
            ip_add
        ))

        connection.commit()

        return {
            "status": 0,
            "message": "Successfully Added",
            "designation_id": designation_id
        }

    except Exception as e:

        if connection:
            connection.rollback()

        logger.exception("POST /designations Error")

        return {
            "status": 1,
            "message": str(e)
        }

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()

@router.put("/designations")
def update_designation(req: DesignationUpdate, request: Request):
    try:
        logger.debug(f"PUT /designations Request: {req}")

        designation_id = req.dep_id
        ip_add = request.client.host if request.client else "127.0.0.1"
        logger.debug(f"Client IP: {ip_add}")

        connection = get_connection(PAYROLL_DB_CONFIG)
        cursor = connection.cursor()

        # Check if name exists for another ID
        check_sql = "SELECT COUNT(*) AS CNT FROM GP_EMP_DESIGNATION_MASTER WHERE UPPER(DSM_DESIGNATION_NAME) = %s AND DSM_DESIGNATION_ID != %s"
        cursor.execute(check_sql, [req.dep_name.upper().strip(), designation_id])
        count_name = cursor.fetchone()['CNT']
        logger.debug(f"Duplicate name count: {count_name}")

        if count_name > 0:
            logger.debug("Name already exists for another ID")
            cursor.close()
            connection.close()
            return JSONResponse(status_code=400, content={"status": 1, "msg": "Name Already Exists"})

        # Update Master
        update_master = """
            UPDATE GP_EMP_DESIGNATION_MASTER 
            SET DSM_DESIGNATION_NAME = %s, DSM_SEND_FLAG = 0, DSM_FLAG_STATUS = 1, DSM_MODIFIED_DATE = NOW(), DSM_MODIFIED_USER_CODE = %s
            WHERE DSM_DESIGNATION_ID = %s AND DSM_FLAG_STATUS < 2
        """
        logger.debug(f"Update SQL: {update_master}")
        affected_rows = cursor.execute(update_master, [req.dep_name, req.user_code, designation_id])
        logger.debug(f"Affected rows: {affected_rows}")

        if affected_rows == 0:
            logger.debug("Record not found or already deleted")
            cursor.close()
            connection.close()
            return JSONResponse(status_code=404, content={"status": 1, "msg": "Record not found or already deleted"})

        # Get new Ref ID for History
        cursor.execute("SELECT IFNULL(MAX(HR_REF_ID),0)+1 AS MAXID FROM GP_VIEW_HISTORY")
        ref_id = cursor.fetchone()['MAXID']
        logger.debug(f"Generated ref_id: {ref_id}")

        # Insert into View History (Status 2 for Edit)
        insert_view_history = """
            INSERT INTO GP_VIEW_HISTORY
            (HR_REF_ID, HR_ID, HR_MODULE, HR_MASTER, HR_IP_ADDRESS, HR_CREATED_DATE, HR_CREATED_USER_CODE, HR_STATUS)
            VALUES (%s, %s, '01', '05', %s, NOW(), %s, 2)
        """
        cursor.execute(insert_view_history, [ref_id, designation_id, ip_add, req.user_code])
        logger.debug("View history inserted")

        # Insert into Master His (Status 1 for Edit)
        insert_master_his = """
            INSERT INTO GP_EMP_DESIGNATION_MASTER_HIS
            (EDM_DESIGNATION_ID, EDM_DESIGNATION_NAME, EDM_FLAG_STATUS, EDM_SEND_FLAG, EDM_CREATED_DATE, EDM_CREATED_USER_CODE, EDM_REF_ID, EDM_IP_ADD)
            VALUES (%s, %s, 1, 0, NOW(), %s, %s, %s)
        """
        cursor.execute(insert_master_his, [designation_id, req.dep_name, req.user_code, ref_id, ip_add])
        logger.debug("Master history inserted")

        connection.commit()
        logger.debug("Successfully committed")

        cursor.close()
        connection.close()

        return {"status": 0, "msg": "Successfully Updated"}

    except Exception as e:
        logger.error(f"PUT /designations Error:\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"status": 1, "msg": "Updation Failed", "error": str(e)})


@router.delete("/designations/{designation_id}")
def delete_designation(designation_id: str, request: Request, user_code: str = Query("1")):
    try:
        logger.debug(f"DELETE /designations/{designation_id} Request: user_code={user_code}")

        ip_add = request.client.host if request.client else "127.0.0.1"
        logger.debug(f"Client IP: {ip_add}")

        connection = get_connection(PAYROLL_DB_CONFIG)
        cursor = connection.cursor()

        # Check for Child Record in Employee Master
        child_check = "SELECT COUNT(*) AS CNT FROM GP_EMPLOYEE_MASTER WHERE EM_DESIGNATION = %s"
        cursor.execute(child_check, [designation_id])
        count_name = cursor.fetchone()['CNT']
        logger.debug(f"Child record count: {count_name}")

        if count_name > 0:
            logger.debug("Child record found, cannot delete")
            cursor.close()
            connection.close()
            return JSONResponse(status_code=400, content={"status": 1, "msg": "Child Record Found"})

        # Get Name for history table
        get_name = "SELECT DSM_DESIGNATION_NAME FROM GP_EMP_DESIGNATION_MASTER WHERE DSM_DESIGNATION_ID = %s"
        cursor.execute(get_name, [designation_id])
        name_record = cursor.fetchone()
        dep_name = name_record['DSM_DESIGNATION_NAME'] if name_record else ""
        logger.debug(f"Designation name: {dep_name}")

        # Soft Delete in Master
        delete_master = """
            UPDATE GP_EMP_DESIGNATION_MASTER 
            SET DSM_MODIFIED_USER_CODE = %s, DSM_MODIFIED_DATE = NOW(), DSM_FLAG_STATUS = 2, DSM_SEND_FLAG = 0 
            WHERE DSM_FLAG_STATUS < 2 AND DSM_DESIGNATION_ID = %s
        """
        affected_rows = cursor.execute(delete_master, [user_code, designation_id])
        logger.debug(f"Affected rows: {affected_rows}")

        if affected_rows == 0:
            logger.debug("Record not found or already deleted")
            cursor.close()
            connection.close()
            return JSONResponse(status_code=404, content={"status": 1, "msg": "Record not found or already deleted"})

        # Get new Ref ID for History
        cursor.execute("SELECT IFNULL(MAX(HR_REF_ID),0)+1 AS MAXID FROM GP_VIEW_HISTORY")
        ref_id = cursor.fetchone()['MAXID']
        logger.debug(f"Generated ref_id: {ref_id}")

        # Insert into View History (Status 3 for Delete)
        insert_view_history = """
            INSERT INTO GP_VIEW_HISTORY
            (HR_REF_ID, HR_ID, HR_MODULE, HR_MASTER, HR_IP_ADDRESS, HR_CREATED_DATE, HR_CREATED_USER_CODE, HR_STATUS)
            VALUES (%s, %s, '01', '05', %s, NOW(), %s, 3)
        """
        cursor.execute(insert_view_history, [ref_id, designation_id, ip_add, user_code])
        logger.debug("View history inserted")

        # Insert into Master His (Status 2 for Delete)
        insert_master_his = """
            INSERT INTO GP_EMP_DESIGNATION_MASTER_HIS
            (EDM_DESIGNATION_ID, EDM_DESIGNATION_NAME, EDM_FLAG_STATUS, EDM_SEND_FLAG, EDM_CREATED_DATE, EDM_CREATED_USER_CODE, EDM_REF_ID, EDM_IP_ADD)
            VALUES (%s, %s, 2, 0, NOW(), %s, %s, %s)
        """
        cursor.execute(insert_master_his, [designation_id, dep_name, user_code, ref_id, ip_add])
        logger.debug("Master history inserted")

        connection.commit()
        logger.debug("Successfully committed")

        cursor.close()
        connection.close()

        return {"status": 0, "msg": "Deleted Successfully"}

    except Exception as e:
        logger.error(f"DELETE /designations Error:\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"status": 1, "msg": "Deletion Failed", "error": str(e)})
