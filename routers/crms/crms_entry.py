# import os
# import re
# import traceback
# import uuid
# from datetime import datetime
# from typing import Optional, List
# import pymysql.cursors
# from fastapi import APIRouter, HTTPException, Form, File, UploadFile, Request
# from fastapi.responses import RedirectResponse
# from logger import get_logger
# from pydantic import BaseModel
# from datetime import datetime, date
# from database import get_connection

# logger = get_logger("new_client_request_api")

# router = APIRouter()

# # ==============================
# # 🔹 CONFIG (Match JSP defaults)
# # ==============================
# Client_Id = "27"
# ProjectId = "27"
# CliendId = "FLURYS"
# MAX_FILE_SIZE = 3000000  # 3MB
# MAX_REQDEC_LENGTH = 3000
# UPLOAD_FOLDER = os.path.join(os.getcwd(), "attachment")
# SMTP_HOST = "172.17.72.36"

# # Ensure upload directory exists
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# # ==============================
# # 🔹 HELPER FUNCTIONS (Exact JSP Logic)
# # ==============================

# def escape_sql_string(value: str) -> str:
#     """Replicate JSP: replace single quote with double single quote"""
#     if value is None:
#         return ""
#     return value.replace("'", "''")


# def format_ref_date() -> tuple:
#     """
#     Replicate JSP DateQuery:
#     - REF_DATE: ddmmyyyyHHmmss
#     - MAIL_DATE: dd-mm-yyyy HH:MM:SS
#     - MAIL_TIME: HH:MM:SS
#     """
#     now = datetime.now()
#     ref_date = now.strftime("%d%m%Y%H%M%S")
#     mail_date = now.strftime("%d-%m-%Y %H:%M:%S")
#     mail_time = now.strftime("%H:%M:%S")
#     return ref_date, mail_date, mail_time


# def get_client_date() -> str:
#     """Replicate JSP: CURDATE() -> YYYY-MM-DD"""
#     return datetime.now().strftime("%Y-%m-%d")


# def convert_month_to_num(month_abbr: str) -> str:
#     """Convert MON to MM (JSP logic)"""
#     months = {
#         "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
#         "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
#         "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
#     }
#     return months.get(month_abbr.upper(), "01")


# def convert_r_date_to_sql(r_date: str) -> str:
#     """
#     Convert DD-MON-YYYY to YYYY-MM-DD (JSP logic)
#     Input: "01-JAN-2026" -> Output: "2026-01-01"
#     """
#     if not r_date or "-" not in r_date:
#         return datetime.now().strftime("%Y-%m-%d")
    
#     parts = r_date.split("-")
#     if len(parts) == 3:
#         day = parts[0].strip()
#         month = convert_month_to_num(parts[1].strip())
#         year = parts[2].strip()
#         return f"{year}-{month}-{day}"
#     return datetime.now().strftime("%Y-%m-%d")


# def get_file_extension(filename: str) -> str:
#     """Extract file extension like JSP StringTokenizer"""
#     if not filename or "." not in filename:
#         return ""
#     return filename.split(".")[-1]


# def generate_filename(ref_no: str, file_index: int, original_filename: str) -> str:
#     """Generate filename: RefNo_01.Extension (exact JSP logic)"""
#     extension = get_file_extension(original_filename)
#     return f"{ref_no}_{file_index:02d}.{extension}"


# async def save_uploaded_file(file: UploadFile, target_filename: str, directory: str) -> str:
#     """Save file with renamed filename (replicate JSP store logic)"""
#     file_path = os.path.join(directory, target_filename)
#     with open(file_path, "wb") as buffer:
#         content = await file.read()
#         buffer.write(content)
#     return target_filename


# def get_priority_display(priority: str) -> str:
#     """Convert priority code to display text (JSP logic)"""
#     if priority == "L":
#         return "Normal"
#     elif priority == "H":
#         return "High"
#     return "-"


# # ==============================
# # 🔹 REQUEST MODEL
# # ==============================
# class NewClientRequest(BaseModel):
#     p_message: str
#     radiobutton: str
#     priority: str
#     refno: str
#     subject: str
#     todo1: str = "0"
#     todo2: str = "0"
#     todo3: str = "0"
#     reqFrom: Optional[str] = None
#     cboSingleDate: Optional[str] = None
#     replication: str = "N"


# # ==============================
# # 🔹 MAIN ENDPOINT (Exact JSP Logic Replica)
# # ==============================
# @router.post("/newClientRequestResp")
# async def new_client_request_resp(
#     request: Request,
#     # Form fields
#     p_message: str = Form(...),
#     radiobutton: str = Form(...),
#     priority: str = Form(...),
#     refno: str = Form(...),
#     subject: str = Form(...),
#     todo1: str = Form("0"),
#     todo2: str = Form("0"),
#     todo3: str = Form("0"),
#     reqFrom: Optional[str] = Form(None),
#     cboSingleDate: Optional[str] = Form(None),
#     replication: str = Form("N"),
#     # File uploads
#     datafile1: Optional[UploadFile] = File(None),
#     datafile2: Optional[UploadFile] = File(None),
#     datafile3: Optional[UploadFile] = File(None),
# ):
#     logger.debug("new_client_request_resp started")
    
#     # ==============================
#     # 🔹 INITIALIZE VARIABLES (Match JSP)
#     # ==============================
#     Reqdec = p_message.strip()
#     Reqdeclength = len(Reqdec)
#     Reqdec = escape_sql_string(Reqdec)
#     Req_Type = radiobutton
#     Ref_No = refno
#     subject_escaped = escape_sql_string(subject)
#     todo_1 = todo1
#     todo_2 = todo2
#     todo_3 = todo3
    
#     # Get email from session or default
#     session = request.session if hasattr(request, "session") else {}
#     email = session.get("email", "-")
#     if reqFrom:
#         username = reqFrom
#     else:
#         username = "-"
    
#     # Date handling
#     if cboSingleDate:
#         R_Date = cboSingleDate
#     else:
#         R_Date, C_Date, M_Time = format_ref_date()
    
#     S_Date = get_client_date()
    
#     # ==============================
#     # 🔹 FILE SIZE CHECK (Exact JSP Logic)
#     # ==============================
#     fileSize = 0
#     fileSize2 = 0
#     fileSize3 = 0
    
#     if datafile1 and datafile1.filename:
#         fileSize = len(await datafile1.read())
#         await datafile1.seek(0)
    
#     if datafile2 and datafile2.filename:
#         fileSize2 = len(await datafile2.read())
#         await datafile2.seek(0)
    
#     if datafile3 and datafile3.filename:
#         fileSize3 = len(await datafile3.read())
#         await datafile3.seek(0)
    
#     totalfileSize = fileSize + fileSize2 + fileSize3
#     CheckFileSize = 1 if totalfileSize > MAX_FILE_SIZE else 0
    
#     # ==============================
#     # 🔹 VALIDATION (Exact JSP Logic)
#     # ==============================
#     if Reqdeclength > MAX_REQDEC_LENGTH:
#         descMsg = "Exceeds limit hence enter your comments in attachment"
#         return RedirectResponse(url=f"/newClientReqEntry.jsp?descMsg={descMsg}", status_code=302)
    
#     if CheckFileSize == 1:
#         MsgFileSize = "Mail sending Failed, File Should be below 3 MB"
#         return RedirectResponse(url=f"/ChangeReqView.jsp?msg={MsgFileSize}", status_code=302)
    
#     # ==============================
#     # 🔹 DATABASE CONNECTION
#     # ==============================
#     con = None
#     repliCon = None
#     stmt = None
#     stmt2 = None
#     stmtrepli = None

#     try:
#         con = get_connection()
#         con.autocommit(False)
#         stmt = con.cursor(pymysql.cursors.DictCursor)
#         stmt2 = con.cursor(pymysql.cursors.DictCursor)
        
#         # Replication connection (if enabled)
#         if replication == "Y":
#             logger.warning("Replication requested but secondary DB not configured. Using primary DB only.")
#             repliCon = con  # Placeholder - in production, connect to replica DB
#             repliCon.autocommit(False)
#             stmtrepli = repliCon.cursor(pymysql.cursors.DictCursor)
        
#         # ==============================
#         # 🔹 REQ ID GENERATION (Exact JSP Logic) - UNCONDITIONAL (MOVED OUTSIDE if replication)
#         # ==============================
#         maxIdQuery = "SELECT IFNULL(MAX(RD_REQUEST_DATE), CURDATE()) as RD_REQUEST_DATE FROM CR_REQUEST_ENTRY_DETAILS"
#         stmt.execute(maxIdQuery)
#         result = stmt.fetchone()
#         maxReqIdQuery = result["RD_REQUEST_DATE"] if result and result["RD_REQUEST_DATE"] else datetime.now()

#         # Convert to date for comparison (handle both date and datetime objects from DB)
#         if isinstance(maxReqIdQuery, datetime):
#             max_date_obj = maxReqIdQuery.date()
#         elif isinstance(maxReqIdQuery, date):
#             max_date_obj = maxReqIdQuery
#         else:
#             try:
#                 max_date_obj = datetime.strptime(str(maxReqIdQuery), "%Y-%m-%d").date()
#             except:
#                 max_date_obj = datetime.now().date()

#         current_date = datetime.now().date()
#         reqIdChange = (current_date - max_date_obj).days

#         if reqIdChange >= 1:
#             ReqId = "1"
#         else:
#             sqlQuery = """
#                 SELECT IFNULL(MAX(RD_REQ_ID), 0) + 1 AS MAXID 
#                 FROM CR_REQUEST_ENTRY_DETAILS 
#                 WHERE RD_REQUEST_DATE = (
#                     SELECT IFNULL(MAX(RD_REQUEST_DATE), CURDATE()) 
#                     FROM CR_REQUEST_ENTRY_DETAILS
#                 )
#             """
#             stmt.execute(sqlQuery)
#             result = stmt.fetchone()
#             ReqId = str(result["MAXID"]).strip() if result and result["MAXID"] else "1"
        
#         # ==============================
#         # 🔹 REF NO GENERATION (Exact JSP Logic)
#         # ==============================
#         R_Date_formatted, C_Date, M_Time = format_ref_date()
#         RefNo = f"{R_Date_formatted}-{ProjectId}-{ReqId}"
        
    
        
#         # ==============================
#         # 🔹 FILE UPLOAD HANDLING (Exact JSP Logic)
#         # ==============================
#         filename1 = "A"
#         filename2 = "B"
#         filename3 = "C"
        
#         # File 1
#         if todo_1 != "0" and datafile1 and datafile1.filename:
#             original_filename = datafile1.filename
#             SetFileName1 = generate_filename(RefNo, 1, original_filename)
#             await save_uploaded_file(datafile1, SetFileName1, UPLOAD_FOLDER)
#             filename1 = SetFileName1
        
#         # File 2
#         if todo_2 != "0" and datafile2 and datafile2.filename:
#             original_filename = datafile2.filename
#             SetFileName2 = generate_filename(RefNo, 2, original_filename)
#             await save_uploaded_file(datafile2, SetFileName2, UPLOAD_FOLDER)
#             filename2 = SetFileName2
        
#         # File 3
#         if todo_3 != "0" and datafile3 and datafile3.filename:
#             original_filename = datafile3.filename
#             SetFileName3 = generate_filename(RefNo, 3, original_filename)
#             await save_uploaded_file(datafile3, SetFileName3, UPLOAD_FOLDER)
#             filename3 = SetFileName3
        
#         # Build FilePath string (exact JSP comma-separated logic)
#         FilePath = ""
#         if filename1 != "A":
#             FilePath += filename1
#         if filename2 != "B":
#             if FilePath:
#                 FilePath += ","
#             FilePath += filename2
#         if filename3 != "C":
#             if FilePath:
#                 FilePath += ","
#             FilePath += filename3
        
#         # Build Attachname for email (exact JSP <br> logic)
#         Attachname = ""
#         if filename1 != "A":
#             Attachname += filename1
#         if filename2 != "B":
#             Attachname += "<br>" + filename2
#         if filename3 != "C":
#             Attachname += "<br>" + filename3
        
#         # ==============================
#         # 🔹 INSERT INTO CR_STATUS_DETAILS (Exact JSP Logic)
#         # ==============================
#         teamIdQuery = "SELECT TM_TEAM_ID FROM CR_TEAM_MASTER"
#         stmt.execute(teamIdQuery)
#         team_rows = stmt.fetchall()
        
#         for team_row in team_rows:
#             teamId1 = team_row["TM_TEAM_ID"]
#             StatusQuery = """
#                 INSERT INTO CR_STATUS_DETAILS(SD_REF_NO, SD_TEAM_ID, SD_STATUS) 
#                 VALUES (%s, %s, 'U')
#             """
#             stmt2.execute(StatusQuery, (RefNo, teamId1))
#             if replication == "Y" and stmtrepli:
#                 stmtrepli.execute(StatusQuery, (RefNo, teamId1))
        
#         # ==============================
#         # 🔹 DATE CONVERSION (Exact JSP Logic)
#         # ==============================
#         # Convert R_Date from DD-MON-YYYY to YYYY-MM-DD for SQL insert
#         R_Date_sql = convert_r_date_to_sql(R_Date)
        
#         # ==============================
#         # 🔹 INSERT INTO CR_REQUEST_ENTRY_DETAILS (Exact JSP Logic)
#         # ==============================
#         ClientReq = """
#             INSERT INTO CR_REQUEST_ENTRY_DETAILS(
#                 RD_REQUEST_NO, RD_CLIENT_ID, RD_USER_NAME, RD_REQUEST_DATE,
#                 RD_REQUEST_TYPE, RD_REQUEST_DESC, RD_FILE_ATTACHED,
#                 RD_REQUEST_STATUS, RD_SUBJECT, RD_REQ_ID,
#                 RD_REQUEST_VIEW_STATUS, RD_DISCUSSION_STATUS,
#                 RD_AUDIT_STATUS, RD_CLIENT_MAIL_ID, RD_PRIORITY_STATUS
#             ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'O', %s, %s, 'U', 'N', 'N', %s, %s)
#         """
        
#         params = (
#             RefNo, Client_Id, username, R_Date_sql,
#             Req_Type, Reqdec, FilePath,
#             subject_escaped, ReqId,
#             email, priority
#         )
        
#         cnt = stmt2.execute(ClientReq, params)
        
#         cloudcnt = 0
#         if replication == "Y" and stmtrepli:
#             cloudcnt = stmtrepli.execute(ClientReq, params)
        
#         # ==============================
#         # 🔹 PRIORITY DISPLAY (Exact JSP Logic)
#         # ==============================
#         prior = get_priority_display(priority)
        
#         # ==============================
#         # 🔹 EMAIL TEMPLATES (Exact JSP HTML Logic)
#         # ==============================
#         fromEmail = email
#         fromEmail1 = "-"
#         if fromEmail != "-" and "@" in fromEmail:
#             splitMail = fromEmail.rindex("@")
#             fromEmail1 = fromEmail[:splitMail]
        
#         # Email 1: To internal team
#         Message = (
#             "<table width=100%>"
#             "<tr><td align=left>Dear Sir/Madam, </td></tr>"
#             "<tr><td width=28% align=right style=padding-left:80px></td><td align=right><b>Ref.No:</B>" + RefNo + "&nbsp;&nbsp;&nbsp;</td></tr>"
#             "<tr><td align=left style=padding-left:80px>Client</td><td>:" + CliendId + "</td></tr>"
#             "<tr><td align=left style=padding-left:80px>Priority</td><td>:" + prior + "</td></tr>"
#             "<tr><td align=left style=padding-left:80px>Subject</td><td>:" + subject + "   </td></tr>"
#             "<tr><td align=left style=padding-left:80px></td><td></td></tr>"
#             "<tr><td align=left style=padding-left:80px></td><td></td></tr>"
#             "<tr valign=top><td align=left style=padding-left:80px>Description</td><td>:" + Reqdec + " </td></tr>"
#             "<tr valign=top><td align=left style=padding-left:80px>Attached Files</td><td>:" + Attachname + "</td></tr>"
#             "<tr><td align=left>With Regards,</td></tr>"
#             "<tr><td align=left>" + fromEmail1 + "</td></tr>"
#             "<tr><td align=left></td></tr>"
#             "</table>"
#         )
        
#         # Email 2: Auto-reply to client
#         Message2 = (
#             "<table border=0 width=600>"
#             "<tr><td align=left></td><td>&nbsp;</td><td>&nbsp;</td></tr>"
#             "<tr><td align=left width=25></td><td>&nbsp;</td><td align=right><B></B></td></tr>"
#             "<tr><td align=left colspan=3 >This Automailer is to acknowledge that your request<b> " + subject + "</b> submitted on <b>" + S_Date + "</b> at <b>" + M_Time + "</b> " +
#             "has been registered in our system and the reference number is <b>" + RefNo + "</b>. A breif description of the request is given below. </td></tr>"
#             "<tr valign=top><td align=left>Request Description</td><td valign=top>:" + Reqdec + "</td></tr>"
#             "<tr valign=top><td align=left>Attached Files</td><td>:" + Attachname + "</td></tr>"
#             "<tr><td align=left style=padding-left:100px></td><td></td></tr>"
#             "<tr><td align=left style=padding-left:100px></td><td></td></tr>"
#             "<tr><td align=left style=padding-left:100px></td><td></td></tr>"
#             "<tr><td align=left style=padding-left:100px></td><td></td></tr>"
#             "<tr><td align=left style=padding-left:100px></td><td></td></tr>"
#             "<tr><td align=left colspan=3>We will internally discuss the feasibility of your request and get back to you within one working day.</td></tr>"
#             "<tr><td align=left style=padding-left:100px></td><td></td></tr>"
#             "<tr><td align=left style=padding-left:100px></td><td></td></tr>"
#             "<tr><td align=left style=padding-left:100px></td><td></td></tr>"
#             "<tr><td align=left style=padding-left:100px></td><td></td></tr>"
#             "<tr><td align=left></td></tr>"
#             "<tr><td align=left colspan=3></td></tr>"
#             "<tr><td align=left colspan=3></td></tr>"
#             "<tr><td align=left></td></tr>"
#             "<tr><td align=left></td></tr>"
#             "<tr><td align=left colspan=3>PS:This is an auto-generated mail.Please do not reply.</td></tr>"
#             "</table>"
#         )
        
#         # ==============================
#         # 🔹 INSERT INTO CR_CLIENT_MAIL_DETAILS (Exact JSP Logic)
#         # ==============================
#         maildetailQuery = """
#             INSERT INTO CR_CLIENT_MAIL_DETAILS(CMD_REF_NO, CMD_MAIL_CONTENT) 
#             VALUES (%s, %s)
#         """
#         # stmt2.execute(maildetailQuery, (RefNo, Message2))
#         # if replication == "Y" and stmtrepli:
#         #     stmtrepli.execute(maildetailQuery, (RefNo, Message2))
        
#         # ==============================
#         # 🔹 COMMIT / ROLLBACK (Exact JSP Logic)
#         # ==============================
#         if replication == "Y":
#             con.commit()
#             con.autocommit(True)
#             if repliCon and repliCon != con:
#                 repliCon.commit()
#                 repliCon.autocommit(True)
#         else:
#             con.commit()
#             con.autocommit(True)
        
#         msg = "Successfully Added"
#         logger.info(f"Request processed successfully: RefNo={RefNo}")
        
#         return RedirectResponse(url=f"/newClientReqEntry.jsp?msg={msg}", status_code=302)
        
#     except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         logger.error(traceback.format_exc())
        
#         if con:
#             con.rollback()
#             con.autocommit(True)
#         if replication == "Y" and repliCon and repliCon != con:
#             repliCon.rollback()
#             repliCon.autocommit(True)
        
#         msg = "Failed"
#         return RedirectResponse(url=f"/newClientReqEntry.jsp?msg={msg}", status_code=302)
        
#     finally:
#         if stmt2:
#             stmt2.close()
#         if stmt:
#             stmt.close()
#         if con:
#             con.close()
#         if stmtrepli and replication == "Y" and stmtrepli != stmt:
#             stmtrepli.close()
#         if repliCon and replication == "Y" and repliCon != con:
#             repliCon.close()




import os
import re
import traceback
from datetime import datetime, date
from typing import Optional, List

import pymysql.cursors
from fastapi import APIRouter, Form, File, UploadFile, Request
from fastapi.responses import JSONResponse  # 🔹 IMPORT JSONResponse
from logger import get_logger

from database import get_connection

logger = get_logger("new_client_request_api")

router = APIRouter()

# ==============================
# 🔹 CONFIG
# ==============================
Client_Id = "27"
ProjectId = "27"
CliendId = "FLURYS"
MAX_FILE_SIZE = 3000000  # 3MB
MAX_REQDEC_LENGTH = 1000 # Matched React maxLength
UPLOAD_FOLDER = os.path.join(os.getcwd(), "attachment")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==============================
# 🔹 HELPER FUNCTIONS
# ==============================

def escape_sql_string(value: str) -> str:
    if value is None:
        return ""
    return value.replace("'", "''")

def format_ref_date() -> tuple:
    now = datetime.now()
    ref_date = now.strftime("%d%m%Y%H%M%S")
    mail_date = now.strftime("%d-%m-%Y %H:%M:%S")
    mail_time = now.strftime("%H:%M:%S")
    return ref_date, mail_date, mail_time

def convert_month_to_num(month_abbr: str) -> str:
    months = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
        "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
        "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
    }
    return months.get(month_abbr.upper(), "01")

def convert_r_date_to_sql(r_date: str) -> str:
    if not r_date or "-" not in r_date:
        return datetime.now().strftime("%Y-%m-%d")
    parts = r_date.split("-")
    if len(parts) == 3:
        day = parts[0].strip()
        month = convert_month_to_num(parts[1].strip())
        year = parts[2].strip()
        return f"{year}-{month}-{day}"
    return datetime.now().strftime("%Y-%m-%d")

def get_file_extension(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.split(".")[-1]

def generate_filename(ref_no: str, file_index: int, original_filename: str) -> str:
    extension = get_file_extension(original_filename)
    return f"{ref_no}_{file_index:02d}.{extension}"

async def save_uploaded_file(file: UploadFile, target_filename: str, directory: str) -> str:
    file_path = os.path.join(directory, target_filename)
    content = await file.read()
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    return target_filename

# 🔹 UPDATED: Accepts 'N' (Normal) from React and 'L' (Legacy)
def get_priority_display(priority: str) -> str:
    if priority in ("L", "N"):
        return "Normal"
    elif priority == "H":
        return "High"
    return "-"

# ==============================
# 🔹 MAIN ENDPOINT
# ==============================

@router.post("/newClientRequestResp")
async def new_client_request_resp(
    request: Request,
    p_message: str = Form(...),
    radiobutton: str = Form(...),
    priority: str = Form(...),
    refno: str = Form(...),
    subject: str = Form(...),
    todo1: str = Form("0"),
    todo2: str = Form("0"),
    todo3: str = Form("0"),
    reqFrom: Optional[str] = Form(None),
    cboSingleDate: Optional[str] = Form(None),
    replication: str = Form("N"),
    datafile1: Optional[UploadFile] = File(None),
    datafile2: Optional[UploadFile] = File(None),
    datafile3: Optional[UploadFile] = File(None),
):
    logger.debug("new_client_request_resp started")
    
    # Init Variables
    Reqdec = p_message.strip()
    Reqdeclength = len(Reqdec)
    Reqdec = escape_sql_string(Reqdec)
    Req_Type = radiobutton
    Ref_No = refno
    subject_escaped = escape_sql_string(subject)
    todo_1, todo_2, todo_3 = todo1, todo2, todo3
    
    # Email & User
    email = request.query_params.get("email", "-")
    username = reqFrom if reqFrom else "-"
    
    # Date
    R_Date = cboSingleDate if cboSingleDate else datetime.now().strftime("%d-%m-%Y")
    S_Date = datetime.now().strftime("%Y-%m-%d")

    # File Size Check
    fileSize = 0
    fileSize2 = 0
    fileSize3 = 0
    
    if datafile1 and datafile1.filename:
        fileSize = len(await datafile1.read())
        await datafile1.seek(0)
    if datafile2 and datafile2.filename:
        fileSize2 = len(await datafile2.read())
        await datafile2.seek(0)
    if datafile3 and datafile3.filename:
        fileSize3 = len(await datafile3.read())
        await datafile3.seek(0)
    
    totalfileSize = fileSize + fileSize2 + fileSize3
    CheckFileSize = 1 if totalfileSize > MAX_FILE_SIZE else 0
    
    # 🔹 VALIDATION ERRORS -> Return JSON (Frontend handles toast)
    if Reqdeclength > MAX_REQDEC_LENGTH:
        return JSONResponse(content={"status": 1, "message": "Exceeds limit hence enter your comments in attachment"})
    
    if CheckFileSize == 1:
        return JSONResponse(content={"status": 1, "message": "Mail sending Failed, File Should be below 3 MB"})

    # DB Connection
    con = None
    stmt = None
    stmt2 = None
    repliCon = None
    stmtrepli = None
    
    try:
        con = get_connection()
        con.autocommit(False)
        stmt = con.cursor(pymysql.cursors.DictCursor)
        stmt2 = con.cursor(pymysql.cursors.DictCursor)
        
        if replication == "Y":
            repliCon = con 
            repliCon.autocommit(False)
            stmtrepli = repliCon.cursor(pymysql.cursors.DictCursor)

        # ReqId Logic
        maxIdQuery = "SELECT IFNULL(MAX(RD_REQUEST_DATE), CURDATE()) as RD_REQUEST_DATE FROM CR_REQUEST_ENTRY_DETAILS"
        stmt.execute(maxIdQuery)
        result = stmt.fetchone()
        maxReqIdQuery = result["RD_REQUEST_DATE"] if result and result["RD_REQUEST_DATE"] else datetime.now()

        if isinstance(maxReqIdQuery, datetime):
            max_date_obj = maxReqIdQuery.date()
        elif isinstance(maxReqIdQuery, date):
            max_date_obj = maxReqIdQuery
        else:
            max_date_obj = datetime.now().date()

        reqIdChange = (datetime.now().date() - max_date_obj).days

        if reqIdChange >= 1:
            ReqId = "1"
        else:
            sqlQuery = "SELECT IFNULL(MAX(RD_REQ_ID), 0) + 1 AS MAXID FROM CR_REQUEST_ENTRY_DETAILS WHERE RD_REQUEST_DATE = (SELECT IFNULL(MAX(RD_REQUEST_DATE), CURDATE()) FROM CR_REQUEST_ENTRY_DETAILS)"
            stmt.execute(sqlQuery)
            result = stmt.fetchone()
            ReqId = str(result["MAXID"]).strip() if result and result["MAXID"] else "1"

        # RefNo Generation
        R_Date_formatted, _, _ = format_ref_date()
        RefNo = f"{R_Date_formatted}-{ProjectId}-{ReqId}"
        
        # File Upload
        filename1, filename2, filename3 = "A", "B", "C"
        
        if todo_1 != "0" and datafile1 and datafile1.filename:
            filename1 = await save_uploaded_file(datafile1, generate_filename(RefNo, 1, datafile1.filename), UPLOAD_FOLDER)
        if todo_2 != "0" and datafile2 and datafile2.filename:
            filename2 = await save_uploaded_file(datafile2, generate_filename(RefNo, 2, datafile2.filename), UPLOAD_FOLDER)
        if todo_3 != "0" and datafile3 and datafile3.filename:
            filename3 = await save_uploaded_file(datafile3, generate_filename(RefNo, 3, datafile3.filename), UPLOAD_FOLDER)
        
        # FilePath Construction
        FilePath = ""
        if filename1 != "A": FilePath += filename1
        if filename2 != "B": FilePath += ("," if FilePath else "") + filename2
        if filename3 != "C": FilePath += ("," if FilePath else "") + filename3
        
        Attachname = ""
        if filename1 != "A": Attachname += filename1
        if filename2 != "B": Attachname += "<br>" + filename2
        if filename3 != "C": Attachname += "<br>" + filename3
        
        # Insert Status
        teamIdQuery = "SELECT TM_TEAM_ID FROM CR_TEAM_MASTER"
        stmt.execute(teamIdQuery)
        for team_row in stmt.fetchall():
            StatusQuery = "INSERT INTO CR_STATUS_DETAILS(SD_REF_NO, SD_TEAM_ID, SD_STATUS) VALUES (%s, %s, 'U')"
            stmt2.execute(StatusQuery, (RefNo, team_row["TM_TEAM_ID"]))
            if replication == "Y" and stmtrepli:
                stmtrepli.execute(StatusQuery, (RefNo, team_row["TM_TEAM_ID"]))
        
        R_Date_sql = convert_r_date_to_sql(R_Date)
        
        # Insert Main Request
        ClientReq = """
            INSERT INTO CR_REQUEST_ENTRY_DETAILS(
                RD_REQUEST_NO, RD_CLIENT_ID, RD_USER_NAME, RD_REQUEST_DATE,
                RD_REQUEST_TYPE, RD_REQUEST_DESC, RD_FILE_ATTACHED,
                RD_REQUEST_STATUS, RD_SUBJECT, RD_REQ_ID,
                RD_REQUEST_VIEW_STATUS, RD_DISCUSSION_STATUS,
                RD_AUDIT_STATUS, RD_CLIENT_MAIL_ID, RD_PRIORITY_STATUS
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'O', %s, %s, 'U', 'N', 'N', %s, %s)
        """
        
        params = (RefNo, Client_Id, username, R_Date_sql, Req_Type, Reqdec, FilePath, subject_escaped, ReqId, email, priority)
        cnt = stmt2.execute(ClientReq, params)
        
        if replication == "Y" and stmtrepli:
            stmtrepli.execute(ClientReq, params)
            
        # Commit
        con.commit()
        if replication == "Y" and repliCon:
            repliCon.commit()
        
        # 🔹 SUCCESS RESPONSE -> Return JSON (Frontend handles toast)
        logger.info(f"Request processed successfully: RefNo={RefNo}")
        return JSONResponse(content={"status": 0, "message": "Successfully Added", "refNo": RefNo})

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        if con:
            con.rollback()
        if replication == "Y" and repliCon:
            repliCon.rollback()
        # 🔹 ERROR RESPONSE -> Return JSON
        return JSONResponse(content={"status": 1, "message": "Failed"}, status_code=500)
    finally:
        if stmt2: stmt2.close()
        if stmt: stmt.close()
        if con: con.close()
        if stmtrepli and replication == "Y": stmtrepli.close()
        if repliCon and replication == "Y": repliCon.close()