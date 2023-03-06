import requests
import urllib3
import time
from functools import wraps
from datetime import datetime
from datetime import date
from flask import Flask, session, render_template, request, redirect, url_for
from flask_cors import CORS
import os
from urllib.error import HTTPError
from flask_login import login_required
import logging
import elementpath
from xml.etree import ElementTree
import xml.etree.ElementTree as ET
import mysql.connector
import hashlib

db = mysql.connector.connect(
  host="localhost",
  user="root",
  password="1234",
  database="soar"
)
cursor=db.cursor(dictionary=True)


app = Flask(__name__)
app.secret_key = b'\x8fo\xd3yvp3FYZ\x93\xa3\x07\x82QC'
CORS(app)

#### Warning cikmasin diye ##########
urllib3.disable_warnings()
#####################################
now = datetime.now()
#####################################

##### QRadar baglanti################
qradar_auth_key = "xxxxxxxxxxxxxxx"
QRadar_headers = {
    'sec': qradar_auth_key,
    'content-type': "application/json",
    }
#####################################

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            return redirect(url_for('home' , code=302))
        return f(*args, **kwargs)
    return decorated_function

def md5(entry_password):
    return hashlib.md5(entry_password.encode()).hexdigest()  

def user():
    if session:
        sql = "SELECT user_name from users WHERE user_name = %s"
        cursor.execute(sql, (session['user_name'],))
        users=cursor.fetchall()
        return users
    else:
        return None

def get_whitelist(check):
    sql = "SELECT id from whitelist WHERE ipaddress = %s"
    cursor.execute(sql, (check,))
    ipaddr = cursor.fetchone()
    return ipaddr


app.jinja_env.globals.update(user=user)

@app.route("/")
def home():
    return render_template('index.html')


@app.route("/login", methods=["GET", "POST"])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
    error = ''
    if request.method == 'POST':
        if request.form['email'] == '':
            error='Please Enter Your Email.'
        elif request.form['password'] == '':
            error='Please Enter Your Password.'
        else:
            sql = "SELECT * from users WHERE user_email = %s && user_password = %s"
            cursor.execute(sql, (request.form['email'], md5(request.form['password']),))
            user = cursor.fetchone()
            if user:
               session['user_id'] = user['user_id']
               session['user_name'] = user['user_name']
               return redirect(url_for('home'))
               #return redirect(url_for('home'))
            else:
                error='Credentials Not Found!'
    return render_template('login.html' ,error=error)

@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route("/offense_block", methods=["GET", "POST"])
@login_required
def block_offense():
    if request.method == "POST":
        if request.form.get("search") == 'Block':
            ######## Offense ID Alıyoruz ######
            offense_id = request.form.get("offense_id")
            if offense_id == '':
                error_msg = "Please Enter Offense ID."
                return render_template("offense_block.html", error_msg=error_msg)
            
            #####################################
            if offense_id == '':
                error="Please Enter Offense ID"
                return render_template("offense_block.html", error=error)
            
            ###### AQL Query ####################
            query = {
                "query_expression": "select sourceip from events where INOFFENSE("+str(offense_id)+") ORDER BY starttime asc last 3 hours",
            }
            ####################################

            try:
              st_code = requests.post('https://x.x.x.x/api/ariel/searches',
                                      params=query, headers=QRadar_headers, verify=False, auth=None, timeout=5)
              stat_code = st_code.status_code
              response = requests.post('https://x.x.x.x/api/ariel/searches',
                                   params=query, headers=QRadar_headers, verify=False, auth=None, timeout=5).json()
              searchid = response["search_id"]
              time.sleep(10)
            except (requests.exceptions.ConnectTimeout, UnboundLocalError, KeyError, HTTPError, TypeError, RuntimeError) as error:
            #except Exception as e:
                # creating/opening a file
                f = open("log_file.txt", "a")    
                # writing in the file
                f.write("\n"+"####################################"+"\n")
                f.write(str(now) + "\n")
                f.write(str(error))
                f.write("\n"+"####################################"+"\n")
                # closing the file
                f.close()
                return render_template('offense_block.html', error=error)
            try:
              req = requests.get("https://x.x.x.x/api/ariel/searches/" +
                                 searchid+"/results", headers=QRadar_headers, verify=False, timeout=5).json()
              result_offense = req["events"]
            except (requests.exceptions.ConnectTimeout, UnboundLocalError, KeyError, HTTPError, TypeError, RuntimeError) as error:
            #except Exception as e:
                print(error)
                # creating/opening a file
                f = open("log_file.txt", "a")    
                # writing in the file
                f.write("\n"+"####################################")
                f.write(str(now) + "\n")
                f.write(str(error))
                f.write("####################################")
                # closing the file
                f.close()
                return render_template('offense_block.html', error=error)
            ip_list = open("iplist.txt", "w")
            
            #### DB de bu ip whitelist içinde mi?##########
            sql = "SELECT ipaddress FROM whitelist ORDER BY id DESC"
            cursor.execute(sql)
            iplists= cursor.fetchall()
            error=""
            wlist=[]
            for i in result_offense:
                for ip in iplists:
                    if ip['ipaddress'] == i["sourceip"]:
                        #return render_template("offense_block.html", error=ip['ipaddress'])
                        #exit()
                        if ip['ipaddress'] not in wlist:
                            wlist.append(ip['ipaddress'])
                        break
                    else:
                        ip_list.write(i["sourceip"]+"\n")

            ################################################
            ip_list.close()

            ip_file= open("iplist.txt", "r")
            ip_file_check=ip_file.read().replace("\n"," ")
            if ip_file_check =='':
                return render_template("offense_block.html", error=wlist)
            ip_file.close()
            
            os.system("block/block_push.sh")  
            os.system("python3 /root/soar/qradar_entegration/send_mail_report.py")
            time.sleep(2)
            
            try:  
                mytree = ET.parse('block/block_response.xml')
                myroot = mytree.getroot()
                a=myroot.attrib
                b=a["status"]
                if b == "success":
                    return render_template("offense_block.html", result_offense=result_offense, stat_code=stat_code, searchid=searchid, offense_id=offense_id, error=wlist)
                else:
                    error='Offense Blocked Fail, Call Admin'
                    return render_template("offense_block.html", error=error, result_offense=result_offense, stat_code=stat_code, searchid=searchid, offense_id=offense_id)
            except ET.ParseError:
                    error='Error, Call Admin!'
                    return render_template("offense_block.html", error=error, result_offense=result_offense, stat_code=stat_code, searchid=searchid, offense_id=offense_id)
        else:
            return render_template("offense_block.html")
    else:
        return render_template("offense_block.html")
    




@app.route("/block_unblock", methods=["GET", "POST"])
@login_required
def block_unblock():
    if request.method == "POST":
        if request.form.get("block") == 'Block IPs':
            block = request.form.get("block_ip")

            if block=='':
                error="Please Enter IP Address."
                return render_template("block-unblock.html", error=error)

            os.system("echo %s > iplist.txt" % (block))
            os.system("block/block_push.sh")
            time.sleep(2)
            if get_whitelist(request.form['block_ip']):
                error = request.form['block_ip'] + " IP Address Already Exist in Whitelist."
                return render_template("block-unblock.html", error=error)
            
            try:
                mytree = ET.parse('block/block_response.xml')    
                myroot = mytree.getroot()
                a=myroot.attrib
                b=a["status"]
                if b == "success":
                    success='IP Blocked Success.'
                    os.system("python3 send_mail_report.py")
                    return render_template("block-unblock.html", success=success)
                else:
                    error='IP Blocked Fail, Please Call Admin!'
                    return render_template("block-unblock.html", error=error)
            except ET.ParseError:
                  error='Error, Call Admin!'
                  return render_template("block-unblock.html", error=error)
        elif request.form.get("unblock") == 'Unblock IPs':
            unblock = request.form.get("block_ip")

            if unblock=='':
                error="Please Enter IP Address."
                return render_template("block-unblock.html", error=error)

            os.system("echo %s > iplist.txt" % (unblock))
            os.system("unblock/unblock_push.sh")
            time.sleep(2)

            if get_whitelist(request.form['block_ip']):
                error = request.form['block_ip'] + " IP Address Already Exist in Whitelist."
                return render_template("block-unblock.html", error=error)
            
            os.system("/root/soar/qradar_entegration/check_ip/check_ip.sh")
            block_ip_list = open("/root/soar/qradar_entegration/check_ip/list_ip.txt","r")

            for i in block_ip_list:
                if unblock != i.replace("\n",""):
                    error= request.form['block_ip'] + " IP Address Not Founded in Blocked List"
                    return render_template("block-unblock.html", error=error)
            block_ip_list.close()
            
            try:
                mytree = ET.parse('unblock/unblock_response.xml') 
                myroot = mytree.getroot()
                a=myroot.attrib
                b=a["status"]
                if b == "success":
                    success='IP Unblocked Success'
                    return render_template("block-unblock.html", success=success)
                else:
                    error="IP Unblocked Fail"
                    return render_template("block-unblock.html", error=error)
            except ET.ParseError:
                  error='Error, Call Admin!'
                  return render_template("block-unblock.html", error=error)
        else:
            return render_template("block-unblock.html")
    else:
        return render_template("block-unblock.html")








@app.route("/ip_list" , methods=["GET", "POST"])
@login_required
def ip_list():
    if request.method == "POST":
        if request.form.get("list") == 'Check IP':
            list_ip = request.form.get("list_ip")


            if list_ip =='':
                error="Please Enter IP Address"
                return render_template("ip_list.html", error=error)

            os.system("/root/soar/qradar_entegration/check_ip/check_ip.sh")
            os.system("cat /root/soar/qradar_entegration/check_ip/list_ip.txt |grep "+ str(list_ip) + "> /root/soar/qradar_entegration/check_ip/iplist.txt")
            time.sleep(1)
            f= open("/root/soar/qradar_entegration/check_ip/iplist.txt" ,"r")
            a=f.readline()
            check=a.replace("\n","")
            print(check)
            if str(check) == str(list_ip):
                checks = str(list_ip) + " IP Address Already Blocked"
                return render_template("ip_list.html", checks=checks)
            else:
                checks = str(list_ip) + " IP Address Not Found"
                return render_template("ip_list.html", checks=checks)
        elif request.form.get("show") == 'Show IP List':
            os.system("/root/soar/qradar_entegration/check_ip/check_ip.sh")
            ipler=[]
            c= open("/root/soar/qradar_entegration/check_ip/list_ip.txt" ,"r")
            for i in c:
              ipler.append(i)
            return render_template("ip_list.html", len=len(ipler), ipler=ipler)
        else:
            return render_template("ip_list.html")
    else:
        return render_template("ip_list.html")


@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    if request.method == "POST":
        if request.form.get('delete_ip')=="Delete IP":
            pass
    return render_template("index.html")
 


@app.route("/white_list" , methods=["GET", "POST"])
@login_required
def white_list():
    success=""
    error=""

    if request.method == "POST":
        if request.form.get("show_list"):
            sql = "SELECT * FROM whitelist ORDER BY id DESC"
            cursor.execute(sql)
            iplists= cursor.fetchall()
            if iplists:
                return render_template("white_list.html", iplists=iplists)
            else:
                error="Not Found Any Result."
                return render_template('white_list.html', error=error)
        elif request.form.get("delete_ip"):
            
            
            if request.form['add_ip'] == '':
                error="Please Enter IP Address."
                return render_template("white_list.html", error=error)
            else:
                sql = "DELETE FROM whitelist WHERE ipaddress = %s"
                cursor.execute(sql, (request.form['add_ip'],))
                db.commit()
                if cursor.rowcount:
                        success=request.form['add_ip']+" Deleted IP Adress."
                        return render_template("white_list.html", success=success)
                else:
                    error=request.form['add_ip']+" Not Found in Whitelist."
                    return render_template("white_list.html", error=error)
        elif request.form.get("add_list"):
            sql = "SELECT * FROM whitelist ORDER BY id DESC"
            cursor.execute(sql)
            res=cursor.fetchall()
            if request.form['add_ip'] == '':
                error="Please Enter IP Address."
                return render_template("white_list.html", error=error)
            else:
                for i in res:
                    if str(i['ipaddress']) == request.form['add_ip']:
                        error=request.form['add_ip'] +" IP Address Already Exist."
                        return render_template("white_list.html", error=error)
                today = date.today()
                current_date = today.strftime("%d.%m.%Y")
                sql = "INSERT INTO whitelist SET ipaddress = %s, add_date=%s, current_user_name=%s, comment=%s"
                cursor.execute(sql, (request.form['add_ip'], current_date, session['user_name'], request.form['comment'],))
                db.commit()
                if cursor.rowcount:
                    success= request.form['add_ip']+ " IP Address Added in Whitelist."
                    return render_template("white_list.html", success=success)
                else:
                    error=request.form['add_ip']+" Did not Added Whitelist. Please Call Admin!"
                    return render_template("white_list.html", error=error)
        else:
            return render_template('white_list.html')
    else:
        return render_template("white_list.html")
        







########### Error Handle #########
@app.errorhandler(KeyError)
def page_not_found(e):
    return render_template('404.html', e=e), 404

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', e=e), 404

@app.errorhandler(HTTPError)
def page_not_found(e):
    return render_template('404.html', e=e), 404
    



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
