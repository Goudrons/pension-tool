from flask import Flask, request, render_template_string, redirect, url_for, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
from datetime import date, datetime
import calendar

app = Flask(__name__)

# Brute-Force Schutz
from collections import defaultdict
_paerchen_id1 = ""
_paerchen_id2 = ""
import time
login_attempts = defaultdict(list)
MAX_ATTEMPTS = 5
LOCKOUT_TIME = 900  # 15 Minuten

def is_locked_out(ip):
    now = time.time()
    attempts = [t for t in login_attempts[ip] if now - t < LOCKOUT_TIME]
    login_attempts[ip] = attempts
    return len(attempts) >= MAX_ATTEMPTS

def record_attempt(ip):
    login_attempts[ip].append(time.time())

def clear_attempts(ip):
    login_attempts[ip] = []

app.permanent_session_lifetime = __import__('datetime').timedelta(minutes=60)

@app.context_processor
def inject_now():
    from datetime import datetime
    return {"now": datetime.now().strftime("%d.%m.%Y")}
app.secret_key = "local"
import os, sys, platform

def get_app_dir():
    system = platform.system()
    if system == "Darwin":
        app_dir = os.path.expanduser("~/Library/Application Support/PensionTool")
    elif system == "Windows":
        app_dir = os.path.join(os.environ.get("APPDATA", ""), "PensionTool")
    else:
        app_dir = os.path.expanduser("~/.pensiontool")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

DB_PATH = os.path.join(get_app_dir(), "pension.db")

DEFAULTS = {
    "name": "Standard Szenario",

    "birth_date": "1979-01-01",
    "pension_date": "2045-01-01",
    "target_years": 0,
    "expenses": 0,
    "ahv": 0,
    "ahv_incomes_json": "{}",


    "pk_capital_today_manual": 0,
    "pk_capital": 0,
    "pk_payout_tax_rate": 0,
    "pk_rate": 0,
    "pk_mode": "rente",
    "pk_capital_share": 50,

    "pk2_capital_today_manual": 0,
    "pk2_capital": 0,
    "pk2_payout_tax_rate": 0,
    "pk2_rate": 0,
    "pk2_mode": "rente",
    "pk2_capital_share": 50,

    "pillar3a_1": 0,
    "pillar3a_2": 0,
    "pillar3a_3": 0,
    "pillar3a_4": 0,
    "pillar3a_5": 0,
    "saving_3a_5": 0,
    "saving_3a_frequency_5": "monthly",
    "pillar3a_return_rate": 0,
    "pillar3a_payout_tax_rate": 0,

    "pillar3b": 0,
    "saving_3b": 0,
    "pillar3b_return_rate": 0,

    "investments": 0,
    "saving_investments": 0,
    "investments_return_rate": 0,

    "savings_account": 0,
    "saving_savings_account": 0,
    "savings_account_return_rate": 0,

    "real_estate_value": 0,
    "mortgage": 0,
    "other_debt": 0,

    "real_estate_growth_rate": 0,
    "mortgage_amortization_yearly": 0,
    "sell_property_at_retirement": 0,
    "paerchen_id1": "",
    "paerchen_id2": "",
    "notes": "",
}

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Sora:wght@700;800&display=swap');
:root{--bg:#f4f6f9;--panel:#ffffff;--border:#e2e8f0;--text:#14213d;--muted:#5a6a85;--blue:#1a6b5a;--green:#1a6b5a;--red:#dc2626;--primary:#1a6b5a;--primary-dark:#134d42;--primary-light:#e8f5f1;--accent:#c8f56a;--surface:#ffffff;--shadow:0 8px 30px rgba(20,33,61,.10)}
*{box-sizing:border-box}
body{margin:0;font-family:'Inter',Arial,sans-serif;background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased}
.wrap{max-width:1320px;margin:0 auto;padding:28px}
.header{display:block;margin-bottom:0;background:radial-gradient(ellipse 70% 55% at 95% 15%,rgba(200,245,106,.22),transparent),radial-gradient(ellipse 60% 60% at 5% 90%,rgba(26,107,90,.18),transparent),linear-gradient(150deg,#0f5244 0%,#1a6b5a 40%,#1f7a67 100%);padding:24px 28px 0;margin-left:-28px;margin-right:-28px;margin-top:-28px}
h1{margin:0 0 8px;font-size:34px;letter-spacing:-.03em;font-family:'Sora',Arial,sans-serif;font-weight:800;color:#fff}
.subtitle{color:rgba(255,255,255,.8);line-height:1.45}
.card{background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:18px;box-shadow:var(--shadow)}
.card.green-bg{background:radial-gradient(ellipse 70% 55% at 95% 15%,rgba(200,245,106,.22),transparent),radial-gradient(ellipse 60% 60% at 5% 90%,rgba(26,107,90,.18),transparent),linear-gradient(150deg,#0f5244 0%,#1a6b5a 40%,#1f7a67 100%)!important;border:none!important;padding:36px 18px 18px 18px!important;display:flex;flex-direction:column;gap:18px}
.card-title{font-size:16px;font-weight:bold;margin-bottom:4px;color:var(--text)}
.card-subtitle{color:var(--muted);font-size:13px;margin-bottom:16px;line-height:1.4}
.layout{display:grid;grid-template-columns:340px 1fr;gap:20px;align-items:start}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}
.field{background:#f8fafc;border:1px solid var(--border);border-radius:14px;padding:13px}
label{display:block;font-size:12px;color:var(--muted);margin-bottom:7px;line-height:1.35}
input,select,textarea{width:100%;padding:11px;border-radius:10px;border:1px solid var(--border);background:#fff;color:var(--text);font-size:15px}
button,.btn{display:inline-block;padding:12px 16px;border:0;border-radius:12px;background:var(--primary);color:white;font-size:15px;cursor:pointer;text-decoration:none;font-weight:bold}
.btn.gray,button.gray{background:#374151}.btn.red{background:#dc2626}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px;position:sticky;bottom:16px;background:rgba(244,246,249,.92);backdrop-filter:blur(8px);border:1px solid var(--border);padding:12px;border-radius:16px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:18px}
.kpi-hero{background:radial-gradient(ellipse 70% 55% at 95% 15%,rgba(200,245,106,.22),transparent),radial-gradient(ellipse 60% 60% at 5% 90%,rgba(26,107,90,.18),transparent),linear-gradient(150deg,#0f5244 0%,#1a6b5a 40%,#1f7a67 100%);margin:-28px -28px 24px -28px;padding:24px 28px 28px;}.kpi-hero .section-divider:before,.kpi-hero .section-divider:after{background:rgba(255,255,255,.3)}.kpi-hero .section-divider span{color:rgba(255,255,255,.85)}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:18px;box-shadow:var(--shadow)}
.kpi.main{grid-column:span 1;padding:24px;border-color:var(--border)}
.kpi.sub{grid-column:span 2}
.kpi-label{color:var(--muted);font-size:13px;margin-bottom:8px}.kpi-value{font-size:28px;font-weight:bold;letter-spacing:-.03em;animation:fadeInUp .4s ease;color:var(--text)}
@keyframes fadeInUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.kpi.main .kpi-value{font-size:42px}
@media(max-width:980px){.kpis{grid-template-columns:1fr}.kpi.main,.kpi.sub{grid-column:auto}}
.ok{color:var(--green)}.bad{color:var(--red)}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:12px;border-bottom:1px solid var(--border)}th{color:var(--muted);font-size:12px;background:#f1f5f9}.num{text-align:right;white-space:nowrap}
img{width:100%;border-radius:14px;background:white;margin-top:10px}
.scenario-item{background:#f8fafc;border:1px solid var(--border);border-radius:14px;padding:13px;margin-bottom:10px}
.scenario-name{font-weight:bold;margin-bottom:8px;color:var(--text)}.scenario-meta{color:var(--muted);font-size:12px;line-height:1.5;margin-bottom:10px}
.scenario-actions{display:flex;gap:8px}.scenario-actions .btn{padding:7px 10px;font-size:12px;border-radius:9px}
.topnav{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:14px;position:sticky;top:0;z-index:100;background:rgba(255,255,255,.88);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--border);padding:10px 0;margin-left:-28px;margin-right:-28px;padding-left:28px;padding-right:28px}
.loginbox{max-width:420px;margin:90px auto}
@media(max-width:980px){.layout{grid-template-columns:1fr}.header{flex-direction:column}}

input[type=number]{
  appearance:textfield;
}
input[type=number]::-webkit-outer-spin-button,
input[type=number]::-webkit-inner-spin-button{
  -webkit-appearance:none;
  margin:0;
}


/* Mobile Optimierung */
@media(max-width:768px){
  body{
    overflow-x:hidden;
  }

  .wrap{
    padding:14px;
    max-width:100%;
  }

  .header{
    flex-direction:column;
    gap:14px;
    margin-bottom:16px;
  }

  h1{
    font-size:26px;
    line-height:1.15;
  }

  .subtitle{
    font-size:14px;
  }

  .topnav{
    width:100%;
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:8px;
  }

  .topnav .btn{
    width:100%;
    text-align:center;
    padding:12px 10px;
    font-size:14px;
  }

  .layout{
    display:block;
  }

  aside.card{
    margin-bottom:16px;
  }

  .card{
    border-radius:16px;
    padding:14px;
  }

  .grid{
    grid-template-columns:1fr;
    gap:10px;
  }

  .field{
    padding:12px;
  }

  label{
    font-size:13px;
  }

  input, select{
    min-height:46px;
    font-size:16px;
  }

  button, .btn{
    min-height:44px;
    font-size:15px;
  }

  .actions{
    position:static;
    display:grid;
    grid-template-columns:1fr;
    gap:10px;
    margin-top:16px;
  }

  .actions button,
  .actions .btn{
    width:100%;
    text-align:center;
  }

  .kpis{
    grid-template-columns:1fr;
    gap:10px;
  }

  .kpi,
  .kpi.main,
  .kpi.sub{
    grid-column:auto;
    padding:16px;
  }

  .kpi.main .kpi-value{
    font-size:34px;
  }

  .kpi-value{
    font-size:26px;
    word-break:break-word;
  }

  .scenario-actions{
    display:grid;
    grid-template-columns:1fr 1fr;
  }

  table{
    min-width:720px;
  }

  .card:has(table){
    overflow-x:auto;
    -webkit-overflow-scrolling:touch;
  }

  th, td{
    padding:10px;
    font-size:13px;
  }

  .num{
    white-space:nowrap;
  }
}

@media(max-width:520px){
  .topnav{
    grid-template-columns:1fr;
  }

  h1{
    font-size:24px;
  }

  .kpi.main .kpi-value{
    font-size:30px;
  }

  .kpi-value{
    font-size:24px;
  }
}


.print-title{display:none}




/* Premium Design Layer */
body{
  background:
    radial-gradient(circle at top left,rgba(26,107,90,.08),transparent 32%),
    radial-gradient(circle at top right,rgba(200,245,106,.08),transparent 28%),
    linear-gradient(180deg,rgba(244,246,249,.97),rgba(241,245,249,.99) 65%);
}

.header h1{
  display:flex;
  align-items:baseline;
  gap:12px;
  flex-wrap:wrap;
}

.topnav{
  padding:10px 28px;
  border:none;
  border-radius:0;
  border-bottom:1px solid var(--border);
  background:rgba(255,255,255,.92);
  backdrop-filter:blur(14px);
}

.navgroup{
  display:flex;
  gap:8px;
  align-items:center;
  flex-wrap:wrap;
  justify-content:center;
}

.topnav .navgroup:last-child{
  margin-left:0;
  justify-content:flex-start;
}

.navgroup span{
  color:var(--muted);
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:.08em;
  font-weight:bold;
  margin-right:2px;
}

button,.btn{
  transition:transform .15s ease, box-shadow .15s ease, background .15s ease;
}

button:hover,.btn:hover{
  transform:translateY(-1px);
  box-shadow:0 10px 24px #0004;
}

.card{
  background:var(--surface);
  border-color:var(--border);
}

.card-title{
  display:flex;
  align-items:center;
  gap:10px;
  font-size:17px;
  letter-spacing:-.01em;
}

.card-title:before{
  content:"";
  width:7px;
  height:22px;
  border-radius:99px;
  background:linear-gradient(180deg,var(--primary),var(--primary-dark));
  display:inline-block;
}

.kpi{
  position:relative;
  overflow:hidden;
  border-color:var(--primary);
}

.kpi:before{
  content:"";
  position:absolute;
  inset:0;
  background:linear-gradient(135deg,rgba(26,107,90,.06),transparent 45%);
  pointer-events:none;
}

.kpi.main{
  border-color:var(--primary);
  box-shadow:0 18px 50px rgba(26,107,90,.15);
}

.kpi-label{
  text-transform:uppercase;
  letter-spacing:.06em;
  font-size:11px;
}

.kpi-value{
  position:relative;
}

.field{
  transition:border-color .15s ease, background .15s ease;
}

.field:focus-within{
  border-color:var(--primary);
  background:#f0faf6;
}

input:focus,select:focus,textarea:focus{
  outline:none;
  border-color:var(--primary);
  box-shadow:0 0 0 3px rgba(26,107,90,.18);
}

.scenario-item{
  transition:transform .15s ease,border-color .15s ease,background .15s ease;
}

.scenario-item:hover{
  transform:translateY(-1px);
  border-color:var(--primary);
  background:#f0faf6;
}

.scenario-name{
  font-size:15px;
}

table tr:nth-child(even) td{
  background:rgba(244,246,249,.6);
}

table tr:hover td{
  background:rgba(226,232,240,.6);
}

th{
  position:sticky;
  top:0;
  z-index:1;
}

.num{
  font-variant-numeric:tabular-nums;
}

.print-title{
  border-bottom:2px solid #111;
  padding-bottom:10px;
}

@media(max-width:900px){
  .topnav{
    display:block;
    margin:0 auto;
  }

  .navgroup{
    display:grid;
    grid-template-columns:1fr 1fr;
    margin-bottom:10px;
  }

  .navgroup span{
    grid-column:1/-1;
  }

  .navgroup:last-child{
    margin-bottom:0;
  }

  .kpis{
    grid-template-columns:1fr 1fr;
  }

  .kpi.main,.kpi.sub{
    grid-column:auto;
  }

  .kpi.main .kpi-value{
    font-size:30px;
  }
}

@media(max-width:560px){
  .kpis{
    grid-template-columns:1fr;
  }
}




.section-divider{
  display:flex;
  align-items:center;
  gap:12px;
  margin:24px 0 14px;
}
.section-divider:before,
.section-divider:after{
  content:"";
  height:2px;
  flex:1;
  background:var(--primary);
}
.section-divider span{
  color:var(--muted);
  font-size:12px;
  letter-spacing:.08em;
  text-transform:uppercase;
  font-weight:700;
  white-space:nowrap;
}




/* Clean PDF Output */
.print-summary{display:none}




/* Final UI Polish */
.field{
  border-radius:18px!important;
  padding:14px!important;
}

input,select,textarea{
  border-radius:14px!important;
  min-height:44px;
}

.card{
  margin-bottom:22px;
}

.grid{
  gap:16px!important;
}

.kpi{
  border-radius:22px!important;
}

.kpi-label:before{
  content:"● ";
  color:#22c55e;
}

.kpi.main .kpi-label:before{
  color:var(--primary);
}

.card-title{
  margin-bottom:14px;
}

table{
  font-size:13px!important;
}

th,td{
  padding:9px 10px!important;
}

.card ul{
  margin:8px 0 0 18px;
  padding:0;
  line-height:1.65;
}

.card li{
  margin-bottom:5px;
}

.card h3{
  margin:16px 0 6px;
  color:#e5e7eb;
  font-size:15px;
}

.card p{
  color:var(--muted);
  line-height:1.55;
}

.badge{
  display:inline-block;
  padding:5px 9px;
  border:1px solid var(--border);
  border-radius:999px;
  background:rgba(244,246,249,.92);
  color:var(--muted);
  font-size:11px;
  font-weight:700;
  letter-spacing:.04em;
  text-transform:uppercase;
}

.header .subtitle{
  line-height:1.45;
}

@media(max-width:900px){
  .card{
    margin-bottom:16px;
  }

  th,td{
    padding:8px!important;
  }
}


/* UX Erweiterungen */
.scenario-item.active{
  border-color:var(--primary)!important;
  background:#f0faf6!important;
  box-shadow:0 0 0 1px rgba(26,107,90,.25),0 14px 32px rgba(26,107,90,.12);
}

.scenario-item.active .scenario-name:after{
  content:" aktiv";
  margin-left:8px;
  font-size:10px;
  text-transform:uppercase;
  color:var(--primary);
  border:1px solid rgba(26,107,90,.4);
  border-radius:999px;
  padding:3px 7px;
}

.kpi .ok,
.ok{
  text-shadow:none;
}

.bad{
  text-shadow:0 0 18px #ef444444;
}

input[type=text],
input[type=date],
input[type=password],
select,
textarea{
  font-variant-numeric:tabular-nums;
}

table{
  border-radius:14px;
  overflow:hidden;
}

table tr:last-child td,
table tr:last-child th{
  border-bottom:0;
}


.mt{margin-top:18px}
.mb{margin-bottom:18px}
@media print{
  @page{margin:12mm}
  body{background:white!important;color:#111!important;font-family:Arial,sans-serif!important;font-size:11px!important}
  .no-print,.topnav,.actions,.scenario-bar,.section-divider,.footer-version,aside{display:none!important}
  form .card{display:none!important}
  form .grid{display:none!important}
  form .actions{display:none!important}
  .wrap{max-width:none!important;padding:0!important}
  .layout{display:block!important}
  main{width:100%!important}
  .header{display:none!important}
  .print-title{display:block!important;border-bottom:3px solid #111!important;padding-bottom:10px!important;margin-bottom:16px!important}
  .print-title h1{color:#111!important;font-size:28px!important;margin:0 0 4px!important;font-weight:900!important}
  .print-title div{color:#333!important;font-size:13px!important}
  .kpis{display:grid!important;grid-template-columns:repeat(4,1fr)!important;gap:10px!important;margin-bottom:16px!important}
  .kpi{background:white!important;border:2px solid #ddd!important;border-radius:10px!important;padding:14px!important;box-shadow:none!important;break-inside:avoid!important;display:block!important}
  .kpi:before{display:none!important}
  .kpi.main{grid-column:span 1!important;box-shadow:none!important;border-color:#999!important}
  .kpi.sub{grid-column:span 2!important}
  .kpi-label{color:#555!important;font-size:9px!important;text-transform:uppercase!important;letter-spacing:.06em!important;margin-bottom:6px!important;display:block!important}
  .kpi-label:before{display:none!important}
  .kpi-value{color:#111!important;font-size:22px!important;font-weight:900!important;display:block!important}
  .kpi.main .kpi-value{font-size:28px!important}
  .ok{color:#166534!important;text-shadow:none!important}
  .bad{color:#991b1b!important;text-shadow:none!important}
  .card{background:white!important;color:#111!important;border:1px solid #ddd!important;border-radius:10px!important;box-shadow:none!important;padding:14px!important;break-inside:avoid!important;margin-bottom:12px!important}
  .card:hover{transform:none!important;box-shadow:none!important}
  .card-title{color:#111!important;font-size:15px!important;font-weight:900!important;margin-bottom:8px!important}
  .card-title:before{display:none!important}
  .card-subtitle{color:#555!important;font-size:11px!important}
  table{width:100%!important;border-collapse:collapse!important;font-size:10px!important;min-width:0!important;border-radius:0!important}
  th{background:#f1f5f9!important;color:#111!important;border-bottom:2px solid #111!important;padding:6px 8px!important;font-weight:900!important;position:static!important}
  td{color:#111!important;padding:5px 8px!important;border-bottom:1px solid #ddd!important}
  tr:nth-child(even) td{background:#fafafa!important}
  tr:hover td{background:inherit!important}
  tr:last-child td{border-top:2px solid #111!important;font-weight:900!important;background:white!important}
  .num{text-align:right!important;white-space:nowrap!important}
  .card:has(table){overflow-x:visible!important}
  button{display:none!important}
}
.tooltip-wrap{position:relative;display:inline-block}
.tooltip-icon{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;border:1.5px solid #64748b;color:#64748b;font-size:10px;font-weight:700;cursor:help;margin-left:6px;flex-shrink:0;vertical-align:middle;transition:.15s}
.tooltip-icon:hover{border-color:var(--primary);color:var(--primary)}
.tooltip-box{display:none;position:absolute;top:calc(100% + 6px);left:50%;transform:translateX(-50%);background:var(--primary-dark);border:1px solid var(--primary);border-radius:10px;padding:8px 12px;font-size:12px;color:#fff;white-space:nowrap;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,.4);pointer-events:none;line-height:1.5;min-width:200px;max-width:300px;white-space:normal}
.tooltip-box:before{content:"";position:absolute;bottom:100%;left:50%;transform:translateX(-50%);border:6px solid transparent;border-bottom-color:#134d42}
.tooltip-wrap:hover .tooltip-box{display:block}
.field label{display:flex;align-items:center}
.footer-version{
  max-width:1320px;
  margin:18px auto 32px;
  padding:0 28px;
  color:var(--muted);
  font-size:12px;
  text-align:right;
}




/* Plausi Feldwarnungen */
.field.warn{
  border:2px solid #ef4444!important;
  box-shadow:0 0 0 1px #ef444455,0 0 18px #ef444422!important;
}


.compare-better{color:#22c55e;font-weight:800}
.compare-worse{color:#ef4444;font-weight:800}
.compare-neutral{color:var(--muted);font-weight:700}


/* PDF Report Clean */



/* Premium Polish */
body{
  background:var(--bg)!important;
}

.card{
  background:var(--surface)!important;
  border:1px solid var(--border)!important;
  box-shadow:var(--shadow)!important;
  transition:.18s ease;
}

.card:hover{
  transform:translateY(-1px);
  box-shadow:
    0 16px 40px rgba(0,0,0,.42),
    0 0 0 1px rgba(96,165,250,.06)!important;
}

.btn{
  border-radius:14px!important;
  font-weight:700!important;
  transition:.16s ease!important;
  box-shadow:0 6px 16px rgba(0,0,0,.25);
}

.btn:hover{
  transform:translateY(-1px);
  box-shadow:0 10px 24px rgba(0,0,0,.34);
}

.field{
  background:rgba(244,246,249,.95)!important;
  border:1px solid rgba(148,163,184,.14)!important;
  transition:.16s ease!important;
}

.field:hover{
  border-color:rgba(96,165,250,.18)!important;
}

input,select,textarea{
  background:#fff!important;
  border:1px solid var(--border)!important;
  transition:.14s ease!important;
}

input:focus,select:focus,textarea:focus{
  border-color:var(--primary)!important;
  box-shadow:
    0 0 0 1px rgba(26,107,90,.2),
    0 0 22px rgba(26,107,90,.08)!important;
}

.kpi{
  background:var(--surface)!important;
  border:1px solid var(--border)!important;
  box-shadow:0 8px 30px rgba(20,33,61,.08)!important;
}

.kpi-value{
  letter-spacing:-.03em;
}

.header{
  margin-bottom:22px!important;
}

table{
  overflow:hidden;
  border-radius:14px!important;
}

th{
  background:rgba(244,246,249,.98)!important;
}


/* AHV Polish */
.ahv-gap{
  border-color:#f97316!important;
  box-shadow:0 0 0 1px #f9731655,0 10px 28px #f9731622!important;
}

table th{
  position:sticky;
  top:0;
  z-index:2;
}

table td,table th{
  padding-top:7px!important;
  padding-bottom:7px!important;
}




/* iPhone Date Alignment */
input[type="date"]{
  min-height:52px!important;
  height:52px!important;
  display:flex!important;
  align-items:center!important;
  line-height:52px!important;
  padding-top:0!important;
  padding-bottom:0!important;
  -webkit-appearance:none!important;
}

input[type="date"]::-webkit-date-and-time-value{
  text-align:left;
  min-height:52px;
  line-height:52px!important;
}

input[readonly]{
  display:flex;
  align-items:center;
}

</style>
"""

SHARED_JS = '<script>\ndocument.addEventListener("DOMContentLoaded", function () {\n  function isMoneyField(input) {\n    const name = input.name || "";\n    return [\n      "expenses","ahv",\n      "pk_capital","pk2_capital",\n      "pk_capital_share","pk2_capital_share",\n      "pillar3a_1","pillar3a_2","pillar3a_3","pillar3a_4","pillar3a_5",\n      "saving_3a_5",\n      "pillar3b","saving_3b",\n      "investments","saving_investments",\n      "pk_capital_today_manual","pk2_capital_today_manual",\n      "savings_account","real_estate_value","mortgage","partner_ahv"\n    ].includes(name) || name.startsWith("income_");\n  }\n\n  function cleanNumber(value) {\n    return String(value || "").replace(/\'/g, "").replace(/\\s/g, "").replace(",", ".");\n  }\n\n  function formatMoney(input) {\n    let raw = cleanNumber(input.value);\n    if (raw === "" || isNaN(Number(raw))) return;\n    let num = Math.round(Number(raw));\n    input.value = num.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, "\'");\n  }\n\n  document.querySelectorAll("input[type=\'text\']").forEach(function (input) {\n    if (!isMoneyField(input)) return;\n    formatMoney(input);\n    input.addEventListener("blur", function () { formatMoney(input); });\n    input.addEventListener("focus", function () { input.value = cleanNumber(input.value); });\n  });\n\n  document.querySelectorAll("form").forEach(function (form) {\n    form.addEventListener("submit", function () {\n      form.querySelectorAll("input[type=\'text\']").forEach(function (input) {\n        if (isMoneyField(input)) input.value = cleanNumber(input.value);\n      });\n    });\n  });\n});\n</script>'

LOGIN_HTML = """
<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"><link rel="icon" type="image/png" href="/favicon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Swiss Pension Tool">
<link rel="apple-touch-icon" href="/favicon.png">
<title>Login</title>""" + STYLE + """</head>
<body><div class="wrap"><div class="loginbox card">
<div style="text-align:center;margin-bottom:20px"><img src="/favicon.png" style="width:80px;height:80px;border-radius:18px;background:none"></div>
<h1>Schweizer Pension Tool</h1><div class="card-subtitle">Login — Deine Pension wartet. Leider auch das Alter. 😅</div>
{% if error %}<div style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);border-radius:10px;padding:10px 14px;color:#fca5a5;font-size:13px;margin-bottom:16px">⚠ {{ error }}</div>{% endif %}
<form method="post">
<div class="field"><label>Benutzername</label><input name="username" autofocus></div><br>
<div class="field"><label>Passwort</label><input name="password" type="password"></div>
<button type="submit" class="mt" style="width:100%">Los geht's 🚀</button>
</form>
</div></div><div class="footer-version">Version 3.0 · Weil die AHV alleine nicht reicht · Stand {{ now }}</div>

""" + SHARED_JS + """

</body></html>
"""

USERS_HTML = """
<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"><link rel="icon" type="image/png" href="/favicon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Swiss Pension Tool">
<link rel="apple-touch-icon" href="/favicon.png">
<title>Benutzer</title>""" + STYLE + """</head>
<body>
{% if request.args.get("tour") %}
<div id="tour-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:99999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)">
  <div style="background:#fff;border:1px solid var(--border);border-radius:24px;padding:32px;max-width:480px;width:90%;box-shadow:0 32px 80px rgba(20,33,61,.15)">
    <div style="font-size:40px;text-align:center;margin-bottom:16px">👋</div>
    <h2 style="text-align:center;margin:0 0 8px;font-size:22px">Willkommen beim Schweizer Pension Tool! 🇨🇭</h2>
    <p style="color:#94a3b8;text-align:center;margin:0 0 24px;line-height:1.6">Du bist einen Schritt weiter als 80% der Schweizer — die meisten verdrängen das Thema! 💪</p>
    <div style="display:flex;flex-direction:column;gap:12px;margin-bottom:24px">
      <div style="display:flex;gap:12px;align-items:flex-start;background:#f1f5f9;border-radius:12px;padding:12px">
        <span style="font-size:20px">1️⃣</span>
        <div><b>AHV-Rente berechnen</b><br><span style="color:#94a3b8;font-size:13px">Klicke oben auf "AHV-Rechner" und trage deine Einkommenshistorie ein.</span></div>
      </div>
      <div style="display:flex;gap:12px;align-items:flex-start;background:#f1f5f9;border-radius:12px;padding:12px">
        <span style="font-size:20px">2️⃣</span>
        <div><b>Daten eintragen</b><br><span style="color:#94a3b8;font-size:13px">PK-Ausweis, Säule 3a, Investitionen und Wunschrente erfassen.</span></div>
      </div>
      <div style="display:flex;gap:12px;align-items:flex-start;background:#f1f5f9;border-radius:12px;padding:12px">
        <span style="font-size:20px">3️⃣</span>
        <div><b>Szenarien vergleichen</b><br><span style="color:#94a3b8;font-size:13px">Verschiedene Varianten speichern und mit "Kopieren" neue Szenarien erstellen.</span></div>
      </div>
    </div>
    <button onclick="document.getElementById('tour-overlay').style.display='none'" style="width:100%;background:linear-gradient(135deg,#2563eb,#0ea5e9);border:0;border-radius:14px;color:white;font-size:16px;font-weight:700;padding:14px;cursor:pointer">Los geht's! 🚀</button>
  </div>
</div>
{% endif %}
<div class="wrap">
<div class="header"><div><h1>Benutzer (die Crew 👥)</h1><div class="subtitle">Nur Admin-ID 1 darf Benutzer verwalten.</div></div>
<div class="topnav"><a class="btn gray" href="/{% if scenario_id %}?id={{ scenario_id }}{% endif %}">Zurück</a></div></div>

<div class="card">
<form method="post">
<div class="grid">
<div class="field"><label>Neuer Benutzername</label><input name="username"></div>
<div class="field"><label>Passwort</label><input name="password" type="password"></div>
</div>
<button type="submit" class="mt">Benutzer erstellen</button>
</form>
</div>

<div class="card" class="mt">
<div class="card-title">Vorhandene Benutzer</div>
<table>
<tr><th>Benutzer</th><th>Rolle</th><th>Zuletzt online</th><th>Aktion</th></tr>
{% for u in users %}
<tr>

<td>{{ u.username }}</td>
<td>{% if u.id == 1 %}Admin{% else %}Benutzer{% endif %}</td>
        <td>{% if u.last_seen %}{{ u.last_seen }}{% else %}Noch nie{% endif %}</td>
<td>
{% if u.id != 1 %}
<a class="btn red" style="padding:7px 10px;font-size:12px" href="/users?delete={{ u.id }}" onclick="return confirm('Benutzer wirklich löschen? Szenarien dieses Benutzers werden ebenfalls gelöscht.')">Löschen</a>
{% else %}
-
{% endif %}
</td>
</tr>
{% endfor %}
</table>
</div>
</div><div class="footer-version">Version 3.0 · Weil die AHV alleine nicht reicht · Stand {{ now }}</div>
""" + SHARED_JS + """

</body></html>
"""

HTML = """
<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"><link rel="icon" type="image/png" href="/favicon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Swiss Pension Tool">
<link rel="apple-touch-icon" href="/favicon.png">
<title>Schweizer Pension Tool</title>""" + STYLE + """</head>
<body>
{% if request.args.get("tour") %}
<div id="tour-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:99999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)">
  <div style="background:#fff;border:1px solid var(--border);border-radius:24px;padding:32px;max-width:480px;width:90%;box-shadow:0 32px 80px rgba(20,33,61,.15)">
    <div style="font-size:48px;text-align:center;margin-bottom:16px">👋</div>
    <h2 style="text-align:center;margin:0 0 8px;font-size:22px">Willkommen beim Schweizer Pension Tool! 🇨🇭</h2>
    <p style="color:#94a3b8;text-align:center;margin:0 0 24px;line-height:1.6">Du bist einen Schritt weiter als 80% der Schweizer — die meisten verdrängen das Thema! 💪</p>
    <div style="display:flex;flex-direction:column;gap:12px;margin-bottom:24px">
      <div style="display:flex;gap:12px;align-items:flex-start;background:#f1f5f9;border-radius:12px;padding:12px">
        <span style="font-size:20px">1️⃣</span>
        <div><b>AHV-Rente berechnen</b><br><span style="color:#94a3b8;font-size:13px">Klicke oben auf "AHV-Rechner" und trage deine Einkommenshistorie ein.</span></div>
      </div>
      <div style="display:flex;gap:12px;align-items:flex-start;background:#f1f5f9;border-radius:12px;padding:12px">
        <span style="font-size:20px">2️⃣</span>
        <div><b>Daten eintragen</b><br><span style="color:#94a3b8;font-size:13px">PK-Ausweis, Säule 3a, Investitionen und Wunschrente erfassen.</span></div>
      </div>
      <div style="display:flex;gap:12px;align-items:flex-start;background:#f1f5f9;border-radius:12px;padding:12px">
        <span style="font-size:20px">3️⃣</span>
        <div><b>Szenarien vergleichen</b><br><span style="color:#94a3b8;font-size:13px">Verschiedene Varianten speichern und mit "Kopieren" neue Szenarien erstellen.</span></div>
      </div>
    </div>
    <button onclick="document.getElementById('tour-overlay').style.display='none'" style="width:100%;background:linear-gradient(135deg,#2563eb,#0ea5e9);border:0;border-radius:14px;color:white;font-size:16px;font-weight:700;padding:14px;cursor:pointer">Los geht's! 🚀</button>
  </div>
</div>
{% endif %}
<div class="wrap">
<div class="header">
  <div style="display:flex;align-items:center;gap:14px"><img src="/favicon.png" style="width:48px;height:48px;border-radius:12px;background:none"><h1 style="color:#fff">Schweizer Pension Tool <span class="subtitle" style="font-size:18px;color:rgba(255,255,255,.8)">Schweizer Pension Tool</span></h1></div>
  <div class="topnav">
  <div class="navgroup"><span>Tools</span><a class="btn gray" href="/help{% if data.id %}?id={{ data.id }}{% endif %}">Hilfe</a><a class="btn gray" href="/paerchen{% if data.id %}?id={{ data.id }}{% endif %}">Pärchen</a><a class="btn gray" href="/ahv{% if data.id %}?id={{ data.id }}{% endif %}">AHV-Rechner</a><a class="btn gray" target="_blank" rel="noopener" href="https://www.vermoegenszentrum.ch/rechner/steuern-beim-bezug-von-pensionskassen-und-saeule-3a-guthaben-berechnen">Kapitalsteuer</a></div></div>
</div>
{% if request.args.get("saved") %}<div style="text-align:center;padding:10px;margin-bottom:12px;background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.2);border-radius:12px;font-size:14px;color:#86efac">💾 Szenario gespeichert — sicherer als deine PK!</div>{% endif %}
{% if not result and not data.id %}
<div class="card" style="text-align:center;padding:40px;margin-bottom:18px;border-color:rgba(96,165,250,.2)">
  <div style="font-size:48px;margin-bottom:16px">🇨🇭</div>
  <h2 style="margin:0 0 8px;font-size:22px">🍾 Prost auf deine Zukunft!</h2>
  <p style="color:#94a3b8;margin:0 0 8px;max-width:440px;margin-left:auto;margin-right:auto;line-height:1.6">Jemand der seine Pension nicht dem Zufall überlässt. Trage deine Daten ein und finde heraus ob du mit 65 Champagner oder Leitungswasser trinkst.</p>
  <p style="color:#64748b;font-size:12px;margin:0 0 24px">PS: Die AHV alleine reicht übrigens nicht. Nur so als Hinweis. 😬</p>
  <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
    <a class="btn gray" href="/ahv">AHV-Rechner starten</a>
    <a class="btn" href="/?new=1">Neues Szenario</a>
  </div>
</div>
{% endif %}
{% if result %}
<div class="print-title">
  <h1>Schweizer Pension Tool</h1>
  <div>Szenario: {{ data.name }} · Pension: {{ result.pension_date_formatted if result.pension_date_formatted else data.pension_date }}</div>
</div>

<div class="kpi-hero"><div class="section-divider">
  <span>Ergebnis Dashboard (die Wahrheit)</span>
</div>


<div class="kpis">

  <div class="kpi main" style="border-color:#22c55e;box-shadow:0 18px 50px rgba(34,197,94,.15)">
    <div class="kpi-label">Total Rente pro Monat</div>
    <div class="kpi-value ok">{{ result.total_available_month }}</div>
  </div>

  <div class="kpi main" style="{% if result.monthly_gap <= 0 %}border-color:#22c55e;box-shadow:0 18px 50px rgba(34,197,94,.15){% else %}border-color:#ef4444;box-shadow:0 18px 50px rgba(239,68,68,.15){% endif %}">
    <div class="kpi-label">Vergleich zu Wunschrente</div>
    <div class="kpi-value {% if result.monthly_gap <= 0 %}ok{% else %}bad{% endif %}">{{ result.monthly_gap_text }}</div>
  </div>

  <div class="kpi main">
    <div class="kpi-label">AHV + PK-Rente pro Monat</div>
    <div class="kpi-value">{{ result.fixed_income_month }}</div>
  </div>

  <div class="kpi main">
    <div class="kpi-label">Aus Kapital pro Monat</div>
    <div class="kpi-value">{{ result.capital_monthly_income }}</div>
  </div>

  <div class="kpi sub">
    <div class="kpi-label">Vorsorgevermögen bei Pension nach Steuern</div>
    <div class="kpi-value">{{ result.total_at_retirement }}</div>
  </div>

  <div class="kpi sub">
    <div class="kpi-label">Nettovermögen bei Pension (ohne Vorsorge)</div>
    <div class="kpi-value">{{ result.net_worth_retirement }}</div>
  </div>

</div>
</div>


{% if result.fun_message %}
<div style="text-align:center;padding:14px;margin-bottom:18px;background:rgba(255,255,255,.9);border:1px solid var(--border);border-radius:14px;font-size:15px;color:var(--text)">
  {{ result.fun_message }} <span style="color:var(--muted);font-size:12px">· Noch {{ result.days_to_pension }} Tage bis zur Freiheit!</span>
</div>
{% endif %}

<div class="card green-bg">
<div class="card" class="mb">
  <div class="card-title">Vorsorgevermögen bei Pension (das grosse Geld, hoffentlich 💰)</div>

  <table>
    <colgroup><col style="width:28%"><col style="width:14%"><col style="width:14%"><col style="width:14%"><col style="width:14%"><col style="width:16%"></colgroup>
    <tr>
      <th>Position</th>
      <th class="num">Heute</th>
      <th class="num">Veränderung</th>
      <th class="num">Bei Pension</th>
      <th class="num">Steuern</th>
      <th class="num">Nach Steuern</th>
    </tr>

    <tr>
      <td>Pensionskasse</td>
      <td class="num">{{ result.pk_capital_today_manual }}</td>
      <td class="num">{{ result.pk_growth }}</td>
      <td class="num">{{ result.pk_pension }}</td>
      <td class="num">{{ result.pk_tax }}</td>
      <td class="num">{{ result.pk_net }}</td>
    </tr>

    <tr>
      <td>Kader-Pensionskasse</td>
      <td class="num">{{ result.pk2_capital_today_manual }}</td>
      <td class="num">{{ result.pk2_growth }}</td>
      <td class="num">{{ result.pk2_pension }}</td>
      <td class="num">{{ result.pk2_tax }}</td>
      <td class="num">{{ result.pk2_net }}</td>
    </tr>

    <tr>
      <td>Säule 3a</td>
      <td class="num">{{ result.pillar3a_today }}</td>
      <td class="num">{{ result.pillar3a_growth }}</td>
      <td class="num">{{ result.pillar3a_pension_gross }}</td>
      <td class="num">{{ result.tax_3a }}</td>
      <td class="num">{{ result.pillar3a_net }}</td>
    </tr>

    <tr>
      <td>Säule 3b</td>
      <td class="num">{{ result.pillar3b_today }}</td>
      <td class="num">{{ result.pillar3b_growth }}</td>
      <td class="num">{{ result.pillar3b_pension_gross }}</td>
      <td class="num">0</td>
      <td class="num">{{ result.pillar3b_pension_gross }}</td>
    </tr>

    <tr>
      <td><b>Total</b></td>
      <td class="num"><b>{{ result.total_pension_assets }}</b></td>
      <td class="num"><b>{{ result.total_pension_growth }}</b></td>
      <td class="num"><b>{{ result.total_pension_assets_pension }}</b></td>
      <td class="num"><b>{{ result.total_tax }}</b></td>
      <td class="num"><b>{{ result.breakdown_total_net }}</b></td>
    </tr>
  </table>
</div>



<div class="card" class="mb">
  <div class="card-title">Vermögen bei Pension ohne Vorsorge (auch nicht schlecht 🏠)</div>

  <table>
    <tr>
      <th>Position</th>
      <th class="num">Heute</th>
      <th class="num">Veränderung</th>
      <th class="num">Bei Pension</th>
    </tr>

    <tr>
      <td>Immobilienwert</td>
      <td class="num">{{ result.real_estate_value }}</td>
      <td class="num">{{ result.real_estate_gain }}</td>
      <td class="num">{{ result.real_estate_future }}</td>
    </tr>

    <tr>
      <td>Hypothek</td>
      <td class="num">- {{ result.mortgage }}</td>
      <td class="num">{{ result.mortgage_change }}</td>
      <td class="num">- {{ result.mortgage_future }}</td>
    </tr>

    <tr>
      <td><b>Immobilien-Eigenkapital</b></td>
      <td class="num"><b>{{ result.real_estate_equity }}</b></td>
      <td class="num"><b>{{ result.equity_gain }}</b></td>
      <td class="num"><b>{{ result.real_estate_equity_future }}</b></td>
    </tr>

    <tr>
      <td>Depots / Investitionen</td>
      <td class="num">{{ result.investments_today }}</td>
      <td class="num">{{ result.investments_gain }}</td>
      <td class="num">{{ result.investments_pension }}</td>
    </tr>

    <tr>
      <td>Sparkonto</td>
      <td class="num">{{ result.savings_account_today }}</td>
      <td class="num">{{ result.savings_account_gain }}</td>
      <td class="num">{{ result.savings_account_pension }}</td>
    </tr>

    <tr>
      <td><b>Nettovermögen</b></td>
      <td class="num"><b>{{ result.net_worth_today }}</b></td>
      <td class="num"><b>{{ result.net_worth_gain }}</b></td>
      <td class="num"><b>{{ result.net_worth_retirement }}</b></td>
    </tr>
  </table>
</div>


</div>

{% if result.warnings %}
<div class="card" style="margin-bottom:18px;border-color:#ef4444;background:rgba(127,29,29,.15)">
  <div class="card-title" style="color:#fca5a5">⚠ Plausibilitätsprüfung</div>
  {% for w in result.warnings %}
    <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px;padding:8px 12px;background:rgba(239,68,68,.1);border-radius:10px;border:1px solid rgba(239,68,68,.2)">
      <span style="color:#ef4444;font-size:16px;line-height:1.4">●</span>
      <span style="color:#fca5a5;font-size:13px;line-height:1.5">{{ w }}</span>
    </div>
  {% endfor %}
</div>
{% endif %}
{% endif %}

<div class="layout">
<aside class="card">
  <div class="card-title">Meine Szenarien (Traumwelten)</div>
  <div class="card-subtitle">Speichern, laden, vergleichen — oder bereuen.</div>
  {% if scenarios %}
    {% for s in scenarios %}
    <div class="scenario-item {% if data.id == s.id %}active{% endif %}">
      <form method="post" action="/rename/{{ s.id }}" style="margin-bottom:6px">
        <input name="name" type="text" value="{{ s.name }}" style="font-weight:700;font-size:14px;padding:6px 10px;min-height:0;border-radius:8px" onblur="this.form.submit()">
      </form>
      <div class="scenario-meta">Geburt: {{ format_date_ch(s.birth_date) }}<br>Pension: {{ format_date_ch(s.pension_date) }}<br>PK: {{ s.pk_mode|capitalize }}</div>

      <div class="scenario-actions">
        <a class="btn gray" href="/?id={{ s.id }}">Laden</a>
        <a class="btn gray" href="/duplicate/{{ s.id }}">Kopieren</a>
        <a class="btn red" href="/delete/{{ s.id }}" onclick="return confirm('Szenario löschen? Das ist wie AHV-Beitragsjahre verschenken! 😱')">Löschen</a>
      </div>
    </div>
    {% endfor %}
  {% else %}
    <div class="card-subtitle">Noch keine Szenarien gespeichert.</div>
  {% endif %}
</aside>

<main>
<form method="post">
<input type="hidden" name="scenario_id" value="{{ data.id if data.id else '' }}">

<div class="card">
<div class="card-title">1. Grunddaten (das langweilige aber wichtige Zeug)</div>
<div style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);border-radius:10px;padding:10px 14px;color:#fca5a5;font-size:13px;font-weight:700;margin-bottom:14px">⚠ Alle Vermögenswerte per 01.01.{{ now.split('.')[2] }} erfassen!</div>
<div class="grid">
<div class="field"><label>Szenario Name<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Name für dieses Szenario, z.B. Rente 100% oder Kapital 50%.</span></span></label><input name="name" type="text" value="{{ data.name }}"></div>
<div class="field {% if result and result.warning_fields.birth_date %}warn{% endif %}"><label>Geburtsdatum<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Dein Geburtsdatum. Bestimmt das Pensionierungsdatum (Ende Monat nach 65. Geburtstag).</span></span></label><input name="birth_date" type="date" value="{{ data.birth_date }}"></div>
<div class="field"><label>Datum der Pension</label><input type="text" value="{{ format_date_ch(data.pension_date) }}" disabled></div>
<div class="field {% if result and result.warning_fields.target_years %}warn{% endif %}"><label>Kapital soll reichen für Jahre ab Pension<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Wie viele Jahre soll das Kapital reichen? Z.B. 20 Jahre = bis Alter 85.</span></span></label><input name="target_years" type="text" inputmode="decimal" value="{{ input_value(data.target_years) }}"></div>
<div class="field {% if result and (result.warning_fields.expenses or result.warning_fields.expenses_high) %}warn{% endif %}"><label>Wunschrente (träumen ist erlaubt)<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Gewünschter monatlicher Nettobetrag im Rentenalter in CHF.</span></span></label><input name="expenses" type="text" inputmode="decimal" value="{{ input_value(data.expenses) }}"></div>
<div class="field {% if result and result.warning_fields.ahv %}warn{% endif %}"><label>AHV/Monat (inkl. 13. Rente)<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Voraussichtliche AHV-Monatsrente inkl. 13. Rente (Jahresrente / 12). Empfehlung: AHV-Rechner verwenden.</span></span></label><input name="ahv" type="text" inputmode="decimal" value="{{ input_value(data.ahv) }}"></div>
</div></div>

<div class="card" class="mt"><div class="card-title">2. Pensionskasse (dein grösster Freund oder Feind)</div>
<div class="grid">
<div class="field"><label>Altersguthaben heute<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Aktueller Stand deines PK-Altersguthabens gemäss letztem PK-Ausweis. Stand 01.01. des aktuellen Jahres.</span></span></label><input name="pk_capital_today_manual" type="text" inputmode="decimal" value="{{ input_value(data.pk_capital_today_manual) }}"></div>
<div class="field {% if result and result.warning_fields.pk_capital %}warn{% endif %}"><label>Altersguthaben bei Pension<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Voraussichtliches PK-Altersguthaben bei Pensionierung gemäss PK-Ausweis Hochrechnung.</span></span></label><input name="pk_capital" type="text" inputmode="decimal" value="{{ input_value(data.pk_capital) }}"></div>
<div class="field {% if result and result.warning_fields.pk_rate %}warn{% endif %}"><label>Umwandlungssatz %<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Prozentsatz zur Umrechnung des Kapitals in Jahresrente. Gemäss PK-Reglement. Gesetzliches Minimum: 6.8%.</span></span></label><input name="pk_rate" type="text" inputmode="decimal" step="0.1" value="{{ percent2_value(data.pk_rate) }}"></div>
<div class="field {% if result and result.warning_fields.payout_tax_rate %}warn{% endif %}"><label>Kapitalbezugssteuer %<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Steuer auf PK-Kapitalbezug. Kantonsabhängig. Richtwert: 5-15%.</span></span></label><input name="pk_payout_tax_rate" type="text" inputmode="decimal" step="0.1" value="{{ percent_value(data.pk_payout_tax_rate) }}"></div>
<div class="field"><label>Variante<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Rente = monatliche Rente lebenslang. Kapital = Einmalauszahlung minus Steuern. Mischvariante = beides.</span></span></label><select name="pk_mode"><option value="rente" {% if data.pk_mode == "rente" %}selected{% endif %}>Als monatliche Rente</option><option value="kapital" {% if data.pk_mode == "kapital" %}selected{% endif %}>Als Kapital auszahlen</option><option value="misch" {% if data.pk_mode == "misch" %}selected{% endif %}>Mischvariante</option></select></div>
<div class="field"><label>Kapitalbezug bei Mischvariante %<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Anteil des PK-Kapitals als Einmalbetrag. Rest wird als Monatsrente ausbezahlt.</span></span></label><input name="pk_capital_share" type="text" inputmode="decimal" value="{{ percent_value(data.pk_capital_share) }}"></div>

</div></div>

<div class="card" class="mt"><div class="card-title">3. Kader-Pensionskasse (für die Privilegierten 🎩)</div>
<div class="grid">
<div class="field"><label>Kader Altersguthaben heute<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Aktueller Stand des Kader-PK Altersguthabens. Nur ausfüllen wenn vorhanden.</span></span></label><input name="pk2_capital_today_manual" type="text" inputmode="decimal" value="{{ input_value(data.pk2_capital_today_manual) }}"></div>
<div class="field"><label>Kader Altersguthaben bei Pension<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Voraussichtliches Kader-PK Altersguthaben bei Pensionierung.</span></span></label><input name="pk2_capital" type="text" inputmode="decimal" value="{{ input_value(data.pk2_capital) }}"></div>
<div class="field {% if result and result.warning_fields.pk2_rate %}warn{% endif %}"><label>Kader Umwandlungssatz %<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Umwandlungssatz der Kader-Pensionskasse gemäss Reglement.</span></span></label><input name="pk2_rate" type="text" inputmode="decimal" value="{{ percent2_value(data.pk2_rate) }}"></div>
<div class="field"><label>Kader Kapitalbezugssteuer %<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Steuer auf Kapitalbezug der Kader-PK. Kantonsabhängig.</span></span></label><input name="pk2_payout_tax_rate" type="text" inputmode="decimal" value="{{ percent_value(data.pk2_payout_tax_rate) }}"></div>
<div class="field"><label>Kader Variante<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Auszahlungsart der Kader-PK: Rente, Kapital oder Mischvariante.</span></span></label><select name="pk2_mode"><option value="rente" {% if data.pk2_mode == "rente" %}selected{% endif %}>Als monatliche Rente</option><option value="kapital" {% if data.pk2_mode == "kapital" %}selected{% endif %}>Als Kapital auszahlen</option><option value="misch" {% if data.pk2_mode == "misch" %}selected{% endif %}>Mischvariante</option></select></div>
<div class="field"><label>Kader Kapitalbezug bei Mischvariante %<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Kapitalanteil der Kader-PK bei Mischvariante.</span></span></label><input name="pk2_capital_share" type="text" inputmode="decimal" value="{{ percent_value(data.pk2_capital_share) }}"></div>
</div></div>

<div class="card" class="mt"><div class="card-title">4. Säule 3a (Steuern sparen und für später)</div>
<div class="grid">
<div class="field"><label>Säule 3a Konto 1 (Auszahlung {{ (data.pension_date[:4]|int) - 5 }})<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Erstes 3a-Konto, wird 5 Jahre vor Pension ausgezahlt.</span></span></label><input name="pillar3a_1" type="text" inputmode="decimal" value="{{ input_value(data.pillar3a_1) }}"></div>

<div class="field"><label>Säule 3a Konto 2 (Auszahlung {{ (data.pension_date[:4]|int) - 4 }})<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Zweites 3a-Konto, wird 4 Jahre vor Pension ausgezahlt.</span></span></label><input name="pillar3a_2" type="text" inputmode="decimal" value="{{ input_value(data.pillar3a_2) }}"></div>

<div class="field"><label>Säule 3a Konto 3 (Auszahlung {{ (data.pension_date[:4]|int) - 3 }})<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Drittes 3a-Konto, wird 3 Jahre vor Pension ausgezahlt.</span></span></label><input name="pillar3a_3" type="text" inputmode="decimal" value="{{ input_value(data.pillar3a_3) }}"></div>

<div class="field"><label>Säule 3a Konto 4 (Auszahlung {{ (data.pension_date[:4]|int) - 2 }})<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Viertes 3a-Konto, wird 2 Jahre vor Pension ausgezahlt.</span></span></label><input name="pillar3a_4" type="text" inputmode="decimal" value="{{ input_value(data.pillar3a_4) }}"></div>

<div class="field"><label>Säule 3a Konto 5 (Auszahlung {{ (data.pension_date[:4]|int) - 1 }})<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Fünftes 3a-Konto, wird 1 Jahr vor Pension ausgezahlt. Laufende Einzahlungen auf dieses Konto.</span></span></label><input name="pillar3a_5" type="text" inputmode="decimal" value="{{ input_value(data.pillar3a_5) }}"></div>
<div class="field"><label>Einzahlung 3a Konto 5<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Monatliche oder jaehrliche Einzahlung auf Konto 5. Dieses wird zuletzt ausgezahlt.</span></span></label><input name="saving_3a_5" type="text" inputmode="decimal" value="{{ input_value(data.saving_3a_5) }}"></div>
<div class="field"><label>Zahlungsart 3a Konto 5<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Monatlich = Betrag pro Monat. Jaehrlich = Betrag pro Jahr (max. CHF 7258 fuer Angestellte).</span></span></label><select name="saving_3a_frequency_5"><option value="monthly" {% if data.saving_3a_frequency_5 == "monthly" %}selected{% endif %}>monatlich</option><option value="yearly" {% if data.saving_3a_frequency_5 == "yearly" %}selected{% endif %}>jährlich</option></select></div>

<div class="field {% if result and result.warning_fields.return_3a %}warn{% endif %}"><label>3a Rendite % pro Jahr<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Erwartete jaehrliche Rendite auf das 3a-Kapital. Gemäss Ihrem Vorsorgeauftrag oder Kontoauszug.</span></span></label><input name="pillar3a_return_rate" type="text" inputmode="decimal" step="0.1" value="{{ percent_value(data.pillar3a_return_rate) }}"></div>
<div class="field"><label>Kapitalbezugssteuer %<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Steuer auf die 3a-Auszahlung. Kantonsabhängig. Richtwert: 2-5%.</span></span></label><input name="pillar3a_payout_tax_rate" type="text" inputmode="decimal" step="0.1" value="{{ percent_value(data.pillar3a_payout_tax_rate) }}"></div>
</div></div>

<div class="card" class="mt"><div class="card-title">5. Säule 3b (das freie Sparen)</div>
<div class="grid">
<div class="field"><label>Säule 3b<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Freies Vorsorgevermögen ausserhalb der gebundenen Säule 3a. Z.B. Wertschriften, Lebensversicherungen.</span></span></label><input name="pillar3b" type="text" inputmode="decimal" value="{{ input_value(data.pillar3b) }}"></div>
<div class="field"><label>Sparrate 3b/Monat<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Monatlicher Sparbetrag in die Säule 3b.</span></span></label><input name="saving_3b" type="text" inputmode="decimal" value="{{ input_value(data.saving_3b) }}"></div>
<div class="field {% if result and result.warning_fields.return_3b %}warn{% endif %}"><label>3b Rendite % pro Jahr<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Erwartete jaehrliche Rendite auf das 3b-Vermögen. Gemäss Anlagestrategie.</span></span></label><input name="pillar3b_return_rate" type="text" inputmode="decimal" step="0.1" value="{{ percent_value(data.pillar3b_return_rate) }}"></div>
</div></div>

<div class="card" class="mt"><div class="card-title">6. Investitionen/Sparen (ETF-Jünger aufgepasst 📈)</div>
<div class="grid">
<div class="field"><label>Depots / Investitionen<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Aktueller Wert deiner Wertschriften, ETF, Aktien oder Fonds. Stand 01.01. des aktuellen Jahres.</span></span></label><input name="investments" type="text" inputmode="decimal" value="{{ input_value(data.investments) }}"></div>
<div class="field"><label>Sparrate Depot / Monat<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Monatlicher Sparbetrag ins Depot.</span></span></label><input name="saving_investments" type="text" inputmode="decimal" value="{{ input_value(data.saving_investments) }}"></div>
<div class="field {% if result and result.warning_fields.return_inv %}warn{% endif %}"><label>Depot Rendite % p.a.<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Erwartete jaehrliche Rendite auf das Depot. Gemäss Anlagestrategie.</span></span></label><input name="investments_return_rate" type="text" inputmode="decimal" step="0.1" value="{{ percent_value(data.investments_return_rate) }}"></div>

<div class="field"><label>Sparkonto<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Liquide Mittel auf Spar- oder Kontokorrentkonten. Stand 01.01. des aktuellen Jahres.</span></span></label><input name="savings_account" type="text" inputmode="decimal" value="{{ input_value(data.savings_account) }}"></div>
<div class="field"><label>Sparrate Sparkonto / Monat<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Monatlicher Sparbetrag aufs Sparkonto.</span></span></label><input name="saving_savings_account" type="text" inputmode="decimal" value="{{ input_value(data.saving_savings_account) }}"></div>
<div class="field"><label>Sparkonto Rendite % p.a.<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Aktueller Zinssatz auf dem Sparkonto. Gemäss Kontoauszug.</span></span></label><input name="savings_account_return_rate" type="text" inputmode="decimal" step="0.1" value="{{ percent_value(data.savings_account_return_rate) }}"></div>

<div class="field"><label>Immobilienwert<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Aktueller Marktwert deiner Liegenschaft. Stand 01.01. des aktuellen Jahres.</span></span></label><input name="real_estate_value" type="text" inputmode="decimal" value="{{ input_value(data.real_estate_value) }}"></div>

<div class="field"><label>Hypothek<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Aktueller ausstehender Hypothekarbetrag.</span></span></label><input name="mortgage" type="text" inputmode="decimal" value="{{ input_value(data.mortgage) }}"></div>


<div class="field"><label>Immobilien-Wertsteigerung % p.a.<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Erwartete jaehrliche Wertsteigerung der Liegenschaft.</span></span></label><input name="real_estate_growth_rate" type="text" inputmode="decimal" value="{{ percent_value(data.real_estate_growth_rate) }}"></div>

<div class="field"><label>Hypotheken-Amortisation pro Jahr<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Jaehrlicher Betrag zur Rueckzahlung der Hypothek.</span></span></label><input name="mortgage_amortization_yearly" type="text" inputmode="decimal" value="{{ input_value(data.mortgage_amortization_yearly) }}"></div>

<div class="field">
<label>Immobilie bei Pension verkaufen<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Wenn aktiviert, wird der Immobilien-Nettoerloes zum Pensionszeitpunkt dem Kapital hinzugerechnet.</span></span></label>
<select name="sell_property_at_retirement">
<option value="0" {% if data.sell_property_at_retirement == 0 %}selected{% endif %}>Nein</option>
<option value="1" {% if data.sell_property_at_retirement == 1 %}selected{% endif %}>Ja</option>
</select>
</div>

</div></div>


<div class="actions">
<button type="submit" name="action" value="calculate">Berechnen</button>
<button type="submit" name="action" value="save">Speichern</button>
<a class="btn gray" href="/?new=1">Neues Szenario</a>
</div>
</form>

{% if result %}


{% endif %}
</main>
</div></div><div class="footer-version">Version 3.0 · Weil die AHV alleine nicht reicht · Stand {{ now }}</div>
""" + SHARED_JS + """

</body></html>
"""

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def parse_date(value, fallback):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return datetime.strptime(fallback, "%Y-%m-%d").date()

def years_between(start, end):
    days = (end - start).days
    return max(0, days / 365.25)

def date_at_age(birth, age):
    try:
        return birth.replace(year=birth.year + age)
    except ValueError:
        return birth.replace(year=birth.year + age, day=28)

def ordinary_pension_date(birth):
    d = date_at_age(birth, 65)
    last_day = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last_day)


def init_db():
    conn = db()
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, last_seen TEXT DEFAULT NULL, first_login INTEGER DEFAULT 1, must_change_password INTEGER DEFAULT 0)")
    try:
        conn.execute("ALTER TABLE users ADD COLUMN first_login INTEGER DEFAULT 1")
    except:
        pass
    missing_cols = {
        "savings_account": "REAL DEFAULT 0",
        "saving_savings_account": "REAL DEFAULT 0",
        "savings_account_return_rate": "REAL DEFAULT 0",
        "real_estate_value": "REAL DEFAULT 0",
        "mortgage": "REAL DEFAULT 0",
        "other_debt": "REAL DEFAULT 0",
        "real_estate_growth_rate": "REAL DEFAULT 0",
        "mortgage_amortization_yearly": "REAL DEFAULT 0",
        "sell_property_at_retirement": "REAL DEFAULT 0",
        "pk_capital_today_manual": "REAL DEFAULT 0",
        "pk2_capital_today_manual": "REAL DEFAULT 0",
        "paerchen_id1": "TEXT DEFAULT ''",
        "paerchen_id2": "TEXT DEFAULT ''",
        "notes": "TEXT DEFAULT ''",
    }
    for col, typedef in missing_cols.items():
        try:
            conn.execute(f"ALTER TABLE scenarios ADD COLUMN {col} {typedef}")
        except:
            pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0")
    except:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN last_seen TEXT DEFAULT NULL")
    except:
        pass
    conn.execute("CREATE TABLE IF NOT EXISTS scenarios (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")

    if not conn.execute("SELECT id FROM users WHERE id=1").fetchone():
        conn.execute("INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)", (1, "lokal", "desktop"))

    columns = {
        "user_id": "INTEGER DEFAULT 1",
        "birth_date": "TEXT DEFAULT '1980-01-01'",
        "pension_date": "TEXT DEFAULT '2045-01-01'",
        "target_years": "REAL DEFAULT 25",
        "expenses": "REAL DEFAULT 5500",
        "ahv": "REAL DEFAULT 0",
        "ahv_incomes_json": "TEXT DEFAULT '{}'",


        "pk_capital_today_manual": "REAL DEFAULT 0",
        "paerchen_id1": "TEXT DEFAULT ''",
        "paerchen_id2": "TEXT DEFAULT ''",
        "pk2_capital_today_manual": "REAL DEFAULT 0",
        "notes": "TEXT DEFAULT ''",
        "pk2_capital_today_manual": "REAL DEFAULT 0",
        "pk_capital": "REAL DEFAULT 0",
        "pk_payout_tax_rate": "REAL DEFAULT 8",
        "pk_rate": "REAL DEFAULT 5.2",
        "pk_mode": "TEXT DEFAULT 'rente'",
        "pk_capital_share": "REAL DEFAULT 50",

        "pk2_capital": "REAL DEFAULT 0",
        "pk2_payout_tax_rate": "REAL DEFAULT 8",
        "pk2_rate": "REAL DEFAULT 5.20",
        "pk2_mode": "TEXT DEFAULT 'rente'",
        "pk2_capital_share": "REAL DEFAULT 50",

        "pillar3a_1": "REAL DEFAULT 0",
        "pillar3a_2": "REAL DEFAULT 0",
        "pillar3a_3": "REAL DEFAULT 0",
        "pillar3a_4": "REAL DEFAULT 0",
        "pillar3a_5": "REAL DEFAULT 0",
        "saving_3a": "REAL DEFAULT 0",
        "saving_3a_5": "REAL DEFAULT 0",
        "saving_3a_frequency_5": "TEXT DEFAULT 'monthly'",
        "pillar3a_return_rate": "REAL DEFAULT 4",
        "pillar3a_payout_tax_rate": "REAL DEFAULT 8",

        "pillar3b": "REAL DEFAULT 0",
        "saving_3b": "REAL DEFAULT 0",
        "pillar3b_return_rate": "REAL DEFAULT 4",

        "investments": "REAL DEFAULT 0",
        "saving_investments": "REAL DEFAULT 0",
        "investments_return_rate": "REAL DEFAULT 5",
    }

    existing = [row["name"] for row in conn.execute("PRAGMA table_info(scenarios)").fetchall()]
    for col, typ in columns.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE scenarios ADD COLUMN {col} {typ}")

    conn.commit()
    conn.close()

def require_login():
    return True

def current_user_id():
    return 1

def is_admin():
    return True

def round_chf(value):
    return round(float(value) * 20) / 20

def chf(value):
    value = round_chf(value)
    return f"{round(value):,}".replace(",", "'")

def parse_number(value, fallback=0):
    try:
        txt = str(value).strip().replace("'", "").replace(" ", "").replace(",", ".")
        if txt == "":
            return fallback
        return float(txt)
    except Exception:
        return fallback

def format_date_ch(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d.%m.%Y")
    except:
        return value

def input_value(value):
    try:
        return str(int(round(float(value))))
    except Exception:
        return value

def percent_value(value):
    try:
        return f"{float(value):.1f}"
    except Exception:
        return value

def percent2_value(value):
    try:
        return f"{float(value):.2f}"
    except Exception:
        return value

def data_keys():
    return list(DEFAULTS.keys())

def get_scenarios():
    conn = db()
    rows = conn.execute("SELECT * FROM scenarios WHERE user_id=? ORDER BY id DESC", (current_user_id(),)).fetchall()
    conn.close()
    return rows

def get_scenario(sid):
    conn = db()
    row = conn.execute("SELECT * FROM scenarios WHERE id=? AND user_id=?", (sid, current_user_id())).fetchone()
    conn.close()
    return row

def normalize_row(row):
    data = DEFAULTS.copy()
    if row:
        r = dict(row)
        for key in data:
            if key in r and r[key] is not None:
                data[key] = r[key]
        data["id"] = r.get("id")
        birth_tmp = parse_date(data["birth_date"], DEFAULTS["birth_date"])
        data["pension_date"] = ordinary_pension_date(birth_tmp).isoformat()
    else:
        data["id"] = None
    return data

def form_data():
    data = DEFAULTS.copy()
    sid = request.form.get("scenario_id") or None
    data["id"] = int(sid) if sid else None

    existing_ahv_json = "{}"
    if sid:
        existing = get_scenario(sid)
        if existing and "ahv_incomes_json" in existing.keys():
            existing_ahv_json = existing["ahv_incomes_json"] or "{}"
    data["ahv_incomes_json"] = existing_ahv_json
    if sid:
        existing = get_scenario(sid)
        if existing:
            data["paerchen_id1"] = existing["paerchen_id1"] or ""
            data["paerchen_id2"] = existing["paerchen_id2"] or ""
    data["name"] = request.form.get("name", data["name"])
    data["birth_date"] = request.form.get("birth_date", data["birth_date"])
    birth_tmp = parse_date(data["birth_date"], DEFAULTS["birth_date"])
    data["pension_date"] = ordinary_pension_date(birth_tmp).isoformat()
    data["pk_mode"] = request.form.get("pk_mode", data["pk_mode"])
    data["pk2_mode"] = request.form.get("pk2_mode", data["pk2_mode"])

    for key in DEFAULTS:
        if key in ["name", "birth_date", "pension_date", "pk_mode", "pk2_mode", "ahv_incomes_json", "paerchen_id1", "paerchen_id2"]:
            continue
        if key.startswith("saving_3a_frequency_"):
            data[key] = request.form.get(key, data[key])
            continue
        raw_value = request.form.get(key, data[key])
        data[key] = parse_number(raw_value, data.get(key, 0))

    return data

def save_scenario(data):
    conn = db()
    fields = data_keys()
    values = [data[k] for k in fields]

    saved_id = data.get("id")

    if data.get("id"):
        existing = conn.execute(
            "SELECT name FROM scenarios WHERE id=? AND user_id=?",
            (data["id"], current_user_id())
        ).fetchone()

        if existing and existing["name"] == data["name"]:
            set_clause = ", ".join([f"{k}=?" for k in fields])
            conn.execute(
                f"UPDATE scenarios SET {set_clause} WHERE id=? AND user_id=?",
                values + [data["id"], current_user_id()]
            )
            saved_id = data["id"]
        else:
            db_fields = ", ".join(["user_id"] + fields)
            placeholders = ", ".join(["?"] * (len(fields) + 1))
            cur = conn.execute(
                f"INSERT INTO scenarios ({db_fields}) VALUES ({placeholders})",
                [current_user_id()] + values
            )
            saved_id = cur.lastrowid
    else:
        db_fields = ", ".join(["user_id"] + fields)
        placeholders = ", ".join(["?"] * (len(fields) + 1))
        cur = conn.execute(
            f"INSERT INTO scenarios ({db_fields}) VALUES ({placeholders})",
            [current_user_id()] + values
        )
        saved_id = cur.lastrowid

    conn.commit()
    conn.close()
    return saved_id

def grow(value, payment, annual_return, frequency="monthly"):
    saving = payment * 12 if frequency == "monthly" else payment
    base = value + saving
    return base + (base * annual_return)

def grow_with_frequency(value, payment, frequency, annual_return):
    return grow(value, payment, annual_return, frequency)

def calculate(data):
    birth = parse_date(data["birth_date"], DEFAULTS["birth_date"])
    pension = ordinary_pension_date(birth)
    # Alle Eingabewerte gelten per 01.01. des aktuellen Jahres
    real_today = date.today()
    today = date(real_today.year, 1, 1)

    months_to_retire = max(0, (pension.year - today.year) * 12 + (pension.month - today.month) + 1)
    years_to_retire = months_to_retire / 12
    pension_age = years_between(birth, pension)

    pk_capital = data["pk_capital"]
    pk_tax_rate = data["pk_payout_tax_rate"] / 100

    pk2_capital = data["pk2_capital"]
    pk2_tax_rate = data["pk2_payout_tax_rate"] / 100

    pillar3a_return = data["pillar3a_return_rate"] / 100
    pillar3a_tax_rate = data["pillar3a_payout_tax_rate"] / 100

    pillar3a_accounts = [
        {"name": "Säule 3a Konto 1", "value": data["pillar3a_1"], "saving": 0, "freq": "monthly", "years_before_pension": 5, "paid": False, "gross": 0, "tax": 0, "net": 0},
        {"name": "Säule 3a Konto 2", "value": data["pillar3a_2"], "saving": 0, "freq": "monthly", "years_before_pension": 4, "paid": False, "gross": 0, "tax": 0, "net": 0},
        {"name": "Säule 3a Konto 3", "value": data["pillar3a_3"], "saving": 0, "freq": "monthly", "years_before_pension": 3, "paid": False, "gross": 0, "tax": 0, "net": 0},
        {"name": "Säule 3a Konto 4", "value": data["pillar3a_4"], "saving": 0, "freq": "monthly", "years_before_pension": 2, "paid": False, "gross": 0, "tax": 0, "net": 0},
        {"name": "Säule 3a Konto 5", "value": data["pillar3a_5"], "saving": data["saving_3a_5"], "freq": data["saving_3a_frequency_5"], "years_before_pension": 1, "paid": False, "gross": 0, "tax": 0, "net": 0},
    ]

    paid_3a_capital = 0

    pillar3b = data["pillar3b"]
    pillar3b_return = data["pillar3b_return_rate"] / 100

    investments = data["investments"]
    investments_return = data["investments_return_rate"] / 100

    savings_account = data["savings_account"]
    savings_account_return = data["savings_account_return_rate"] / 100

    warnings = []

    if data["ahv"] <= 0:
        warnings.append("🤔 AHV ist 0 — hast du vergessen einzuzahlen oder lebst du von Luft?")
    elif 0 < data["ahv"] < 1260:
        warnings.append("AHV liegt unter der Minimalrente 2026 (CHF 1'260). Bitte prüfen.")

    if data["expenses"] <= 0:
        warnings.append("💭 Wunschrente ist 0 — von was willst du leben? Luft und Liebe?")

    if data["target_years"] < 10:
        warnings.append("Kapital-Zeitraum ist sehr kurz. Bitte prüfen.")
    elif data["target_years"] > 40:
        warnings.append("Kapital-Zeitraum ist sehr lang. Bitte prüfen.")

    if pk_tax_rate > 0.20 or pk2_tax_rate > 0.20:
        warnings.append("Kapitalbezugssteuer wirkt sehr hoch. Bitte prüfen.")

    if data["pk_rate"] > 7.5 or data["pk2_rate"] > 7.5:
        warnings.append("Umwandlungssatz wirkt sehr hoch. Bitte prüfen.")

    if pillar3a_tax_rate > 0.20:
        warnings.append("3a-Auszahlungssteuer wirkt sehr hoch. Bitte prüfen.")

    if data["pillar3a_return_rate"] > 8:
        warnings.append("3a-Renditeannahme wirkt sehr optimistisch. Bitte prüfen.")

    if data["pillar3b_return_rate"] > 8:
        warnings.append("3b-Renditeannahme wirkt sehr optimistisch. Bitte prüfen.")

    if data["investments_return_rate"] > 8:
        warnings.append("Rendite wirkt sehr optimistisch. Bitte prüfen.")
    if pension <= date.today():
        warnings.append("Pensionsdatum liegt in der Vergangenheit. Bitte prüfen.")
    if data["pk_capital"] > 0 and data["pk_capital_today_manual"] > data["pk_capital"]:
        warnings.append("PK-Kapital bei Pension ist kleiner als heute — negative Rendite? Bitte prüfen.")
    if data["expenses"] > 20000:
        warnings.append("✈️ Wunschrente über CHF 20'000/Monat — hast du auch einen Privatjet eingeplant?")
    if birth.year > date.today().year - 20 or birth.year < date.today().year - 80:
        warnings.append("Geburtsdatum scheint unrealistisch. Bitte prüfen.")

    full_years = months_to_retire // 12
    rest_months = months_to_retire % 12

    # Volle Jahre: alte Excel-kompatible Jahreslogik verwenden
    for year in range(full_years):
        sim_year = today.year + year

        # PK/Kader-PK werden nicht mehr hochgerechnet.
        # Eingabe ist direkt das Kapital bei Alter 65 gemäss PK-Ausweis.

        for a in pillar3a_accounts:
            if not a["paid"]:
                a["value"] = grow_with_frequency(a["value"], a["saving"], a["freq"], pillar3a_return)

                payout_year = pension.year - a["years_before_pension"]
                if sim_year == payout_year:
                    # Auszahlung am Ende des Auszahlungsjahres:
                    # Jahresrendite wurde oben bereits gerechnet.
                    a["gross"] = a["value"]
                    a["tax"] = round_chf(a["gross"] * pillar3a_tax_rate)
                    a["net"] = round_chf(a["gross"] - a["tax"])
                    a["payout_year"] = payout_year
                    paid_3a_capital += a["net"]
                    a["value"] = 0
                    a["paid"] = True

        pillar3b = grow(pillar3b, data["saving_3b"], pillar3b_return)
        investments = grow(investments, data["saving_investments"], investments_return)
        savings_account = grow(
            savings_account,
            data["saving_savings_account"],
            savings_account_return
        )

    # Restmonate bis Pension: anteilige Excel-Logik
    # Zins nur auf Anfangskapital der Restperiode, Einzahlung danach
    rest_factor = rest_months / 12

    # PK/Kader-PK bleiben unverändert, da sie direkt aus dem PK-Ausweis stammen.

    for a in pillar3a_accounts:
        if not a["paid"]:
            saving_rest = 0
            if a["freq"] == "monthly":
                saving_rest = a["saving"] * rest_months
            elif a["freq"] == "yearly":
                # Jahreszahlung nur, wenn Dezember in der Restperiode enthalten ist
                if rest_months >= 12:
                    saving_rest = a["saving"]

            base = a["value"] + saving_rest
            a["value"] = base + (base * pillar3a_return * rest_factor)

    base_3b = pillar3b + (data["saving_3b"] * rest_months)
    pillar3b = base_3b + (base_3b * pillar3b_return * rest_factor)

    base_investments = investments + (data["saving_investments"] * rest_months)
    investments = base_investments + (base_investments * investments_return * rest_factor)

    base_savings = savings_account + (data["saving_savings_account"] * rest_months)
    savings_account = base_savings + (base_savings * savings_account_return * rest_factor)

    for a in pillar3a_accounts:
        if not a["paid"]:
            a["gross"] = a["value"]
            a["tax"] = round_chf(a["gross"] * pillar3a_tax_rate)
            a["net"] = round_chf(a["gross"] - a["tax"])
            a["payout_year"] = pension.year
            paid_3a_capital += a["net"]
            a["value"] = 0
            a["paid"] = True

    pk_gross = pk_capital
    pk2_gross = pk2_capital
    pk_breakdown_gross = pk_gross
    pk2_breakdown_gross = pk2_gross
    total_3a_gross = sum(a["gross"] for a in pillar3a_accounts)
    total_3a_net = round_chf(sum(a["net"] for a in pillar3a_accounts))
    tax_3a = round_chf(sum(a["tax"] for a in pillar3a_accounts))

    pillar3b_gross = pillar3b
    investments_gross = investments
    savings_account_gross = savings_account

    pillar3b_net = round_chf(pillar3b_gross)

    capital_at_retirement = (
        total_3a_net
        + pillar3b_net
    )

    if data["pk_mode"] == "kapital":
        tax_pk = round_chf(pk_gross * pk_tax_rate)
        pk_net = round_chf(pk_gross - tax_pk)
        pk_month = 0
        pk_mode_label = "Kapital"
        pk_usable_net = pk_net
        pk_note = "Kapitalbezug, Steuer abgezogen"
        capital_at_retirement += pk_net
    elif data["pk_mode"] == "misch":
        pk_share = max(0, min(100, data.get("pk_capital_share", 50))) / 100
        pk_capital_part = pk_gross * pk_share
        pk_rent_part = pk_gross - pk_capital_part
        pk_breakdown_gross = pk_capital_part
        tax_pk = round_chf(pk_capital_part * pk_tax_rate)
        pk_net = round_chf(pk_capital_part - tax_pk)
        pk_month = (pk_rent_part * (data["pk_rate"] / 100)) / 12
        pk_mode_label = "Mischvariante"
        pk_usable_net = pk_net
        pk_note = f"Mischvariante: {round(pk_share * 100)}% Kapital, Rest Rente"
        capital_at_retirement += pk_net
    else:
        tax_pk = 0
        pk_net = 0
        pk_breakdown_gross = 0
        pk_month = (pk_gross * (data["pk_rate"] / 100)) / 12
        pk_mode_label = "Rente"
        pk_usable_net = 0
        pk_note = "Wird als Monatsrente vor Einkommenssteuer gerechnet"

    if data["pk2_mode"] == "kapital":
        tax_pk2 = round_chf(pk2_gross * pk2_tax_rate)
        pk2_net = round_chf(pk2_gross - tax_pk2)
        pk2_month = 0
        pk2_usable_net = pk2_net
        pk2_note = "Kapitalbezug, Steuer abgezogen"
        capital_at_retirement += pk2_net
    elif data["pk2_mode"] == "misch":
        pk2_share = max(0, min(100, data.get("pk2_capital_share", 50))) / 100
        pk2_capital_part = pk2_gross * pk2_share
        pk2_rent_part = pk2_gross - pk2_capital_part
        pk2_breakdown_gross = pk2_capital_part
        tax_pk2 = round_chf(pk2_capital_part * pk2_tax_rate)
        pk2_net = round_chf(pk2_capital_part - tax_pk2)
        pk2_month = (pk2_rent_part * (data["pk2_rate"] / 100)) / 12
        pk2_usable_net = pk2_net
        pk2_note = f"Mischvariante: {round(pk2_share * 100)}% Kapital, Rest Rente"
        capital_at_retirement += pk2_net
    else:
        tax_pk2 = 0
        pk2_net = 0
        pk2_breakdown_gross = 0
        pk2_month = (pk2_gross * (data["pk2_rate"] / 100)) / 12
        pk2_usable_net = 0
        pk2_note = "Wird als Monatsrente vor Einkommenssteuer gerechnet"

    total_tax = round_chf(tax_3a + tax_pk + tax_pk2)

    net_worth_today = (
        + data.get("investments", 0)
        + data.get("savings_account", 0)
        + data.get("real_estate_value", 0)
        - data.get("mortgage", 0)
        
    )

    net_worth_retirement = 0

    total_3a_today = (
        data.get("pillar3a_1",0)
        + data.get("pillar3a_2",0)
        + data.get("pillar3a_3",0)
        + data.get("pillar3a_4",0)
        + data.get("pillar3a_5",0)
    )

    total_pension_assets = (
        data.get("pk_capital_today_manual",0)
        + data.get("pk2_capital_today_manual",0)
        + total_3a_today
        + data.get("pillar3b",0)
    )

    total_pension_assets_pension = (
        pk_gross
        + pk2_gross
        + total_3a_gross
        + pillar3b_gross
    )

    real_estate_equity = (
        data.get("real_estate_value",0)
        - data.get("mortgage",0)
    )

    real_estate_future = data.get("real_estate_value", 0)
    mortgage_future = data.get("mortgage", 0)

    growth_rate = data.get("real_estate_growth_rate", 0) / 100
    amortization = data.get("mortgage_amortization_yearly", 0)

    for _ in range(int(years_to_retire)):
        real_estate_future *= (1 + growth_rate)
        mortgage_future = max(0, mortgage_future - amortization)

    real_estate_equity_future = (
        real_estate_future - mortgage_future
    )

    net_worth_retirement = (
        investments_gross
        + savings_account_gross
        + real_estate_equity_future
        
    )

    real_estate_gain = real_estate_future - data.get("real_estate_value", 0)
    mortgage_change = mortgage_future - data.get("mortgage", 0)
    equity_gain = real_estate_equity_future - real_estate_equity

    investments_gain = investments_gross - data.get("investments", 0)
    savings_account_gain = savings_account_gross - data.get("savings_account", 0)

    net_worth_gain = (
        net_worth_retirement - net_worth_today
    )

    # Gesamtvermögen bei Pension BRUTTO:
    # keine Kapitalbezugssteuern abziehen, damit es mit "Gesamtvermögen heute" vergleichbar bleibt.
    # Die Netto-/Steuerlogik für Monatsrente bleibt unten unverändert über capital_at_retirement.
    if data.get("sell_property_at_retirement", 0):
        capital_at_retirement += real_estate_equity_future

    fixed_income_month = round_chf(data["ahv"] + pk_month + pk2_month)

    target_months = max(1, int(data["target_years"] * 12))
    capital_monthly_income = round_chf(capital_at_retirement / target_months)
    total_available_month = round_chf(fixed_income_month + capital_monthly_income)

    monthly_gap = data["expenses"] - total_available_month
    monthly_gap_text = f"-{chf(monthly_gap)}" if monthly_gap > 0 else f"+{chf(abs(monthly_gap))}"

    wunschrente_pct = 0
    if data["expenses"] > 0:
        wunschrente_pct = round(
            ((total_available_month - data["expenses"]) / data["expenses"]) * 100,
            1
        )

    wunschrente_compare = f"{monthly_gap_text} ({wunschrente_pct:+.1f}%)"


    yearly_gap = max(0, (data["expenses"] - fixed_income_month) * 12)
    last_age = int(round(pension_age))
    remaining = capital_at_retirement

    if yearly_gap <= 0:
        last_age = 100
    else:
        while remaining > 0 and last_age < 100:
            remaining -= yearly_gap
            last_age += 1

    pension_breakdown = [
        {"name": "Pensionskasse", "gross": chf(pk_breakdown_gross), "tax": chf(tax_pk), "net": chf(pk_usable_net), "note": pk_note},
        {"name": "Pensionskasse Kader", "gross": chf(pk2_breakdown_gross), "tax": chf(tax_pk2), "net": chf(pk2_usable_net), "note": pk2_note},
        *[
            {
                "name": a["name"],
                "gross": chf(a["gross"]),
                "tax": chf(a["tax"]),
                "net": chf(a["net"]),
                "note": f"Auszahlung {a.get('payout_year', '')}, Steuer abgezogen"
            }
            for a in pillar3a_accounts
        ],
        {"name": "Säule 3b", "gross": chf(pillar3b_gross), "tax": chf(0), "net": chf(pillar3b_net), "note": "Keine Kapitalbezugssteuer"},
    ]

    # Leere Null-Zeilen ausblenden
    pension_breakdown = [
        row for row in pension_breakdown
        if not (row["gross"] == chf(0) and row["tax"] == chf(0) and row["net"] == chf(0))
    ]

    pk_growth = pk_gross - data.get("pk_capital",0)
    pk2_growth = pk2_gross - data.get("pk2_capital",0)
    pillar3a_growth = total_3a_gross - total_3a_today
    pillar3b_growth = pillar3b_gross - data.get("pillar3b",0)

    total_pension_growth = (
        (data.get("pk_capital",0) - data.get("pk_capital_today_manual",0))
        + (data.get("pk2_capital",0) - data.get("pk2_capital_today_manual",0))
        + pillar3a_growth
        + pillar3b_growth
    )

    pk_pension = pk_gross
    pk2_pension = pk2_gross


    return {
        "pension_age": round(pension_age, 1),
        "pension_date_formatted": pension.strftime("%d.%m.%Y"),
        "days_to_pension": max(0, (pension - date.today()).days),
        "total_at_retirement": chf(capital_at_retirement),
        "net_worth_today": chf(net_worth_today),
        "real_estate_value": chf(data.get("real_estate_value",0)),
        "mortgage": chf(data.get("mortgage",0)),
        "real_estate_equity": chf(real_estate_equity),
        "pk_capital_today_manual": chf(data.get("pk_capital_today_manual",0)),
        "pk2_capital_today_manual": chf(data.get("pk2_capital_today_manual",0)),

        "pk_growth": chf(data.get("pk_capital",0) - data.get("pk_capital_today_manual",0)),
        "pk2_growth": chf(data.get("pk2_capital",0) - data.get("pk2_capital_today_manual",0)),
        "pillar3a_growth": chf(pillar3a_growth),
        "pillar3b_growth": chf(pillar3b_growth),
        "total_pension_growth": chf(total_pension_growth),

        "pk_pension": chf(pk_pension),
        "pk_tax": chf(tax_pk),
        "pk_net": chf(pk_net),

        "pk2_tax": chf(tax_pk2),
        "pk2_net": chf(pk2_net),

        "tax_3a": chf(tax_3a),
        "pillar3a_net": chf(total_3a_net),
        "pk2_pension": chf(pk2_pension),
        "pillar3a_today": chf(total_3a_today),
        "pillar3b_today": chf(data.get("pillar3b",0)),
        "pillar3a_pension_gross": chf(total_3a_gross),
        "pillar3b_pension_gross": chf(pillar3b_gross),
        "total_pension_assets": chf(total_pension_assets),
        "total_pension_assets_pension": chf(total_pension_assets_pension),
        "investments_today": chf(data.get("investments",0)),
        "savings_account_today": chf(data.get("savings_account",0)),
        "investments_pension": chf(investments_gross),
        "savings_account_pension": chf(savings_account_gross),

        "real_estate_gain": chf(real_estate_gain),
        "mortgage_change": chf(mortgage_change),
        "equity_gain": chf(equity_gain),

        "investments_gain": chf(investments_gain),
        "savings_account_gain": chf(savings_account_gain),

        "net_worth_gain": chf(net_worth_gain),
        "net_worth_retirement": chf(net_worth_retirement),
        "real_estate_future": chf(real_estate_future),
        "mortgage_future": chf(mortgage_future),
        "real_estate_equity_future": chf(real_estate_equity_future),
        "total_tax": chf(total_tax),
        "fixed_income_month": chf(fixed_income_month),
        "capital_monthly_income": chf(capital_monthly_income),
        "total_available_month": chf(total_available_month),
        "wunschrente_compare": wunschrente_compare,
        "monthly_gap": monthly_gap,
        "monthly_gap_text": monthly_gap_text,
        "fun_message": (
            "🥳 Du kannst dir sogar einen Butler leisten!" if monthly_gap <= -2000 else
            "🎉 Perfekt! Die Pension wird grossartig!" if monthly_gap <= 0 else
            "😬 Vielleicht doch noch ein paar Jahre länger arbeiten..." if monthly_gap <= 1000 else
            "🚨 Alarm! Der Kühlschrank wird teurer als die Rente!" if monthly_gap <= 3000 else
            "😱 Vielleicht doch Lotto spielen?"
        ),
        "last_age": last_age,
        "target_age": int(round(pension_age + data["target_years"])),
        "warnings": warnings,
        "warning_fields": {
            "ahv": data["ahv"] <= 0,
            "expenses": data["expenses"] <= 0,
            "target_years": data["target_years"] < 10 or data["target_years"] > 40,
            "pk_rate": data["pk_rate"] > 7.5,
            "pk2_rate": data["pk2_rate"] > 7.5,
            "payout_tax_rate": pk_tax_rate > 0.20 or pk2_tax_rate > 0.20 or pillar3a_tax_rate > 0.20,
            "return_3a": data["pillar3a_return_rate"] > 8,
            "return_3b": data["pillar3b_return_rate"] > 8,
            "return_inv": data["investments_return_rate"] > 8,
            "pension_date": pension <= date.today(),
            "pk_capital": data["pk_capital"] > 0 and data["pk_capital_today_manual"] > data["pk_capital"],
            "expenses_high": data["expenses"] > 20000,
            "birth_date": birth.year > date.today().year - 20 or birth.year < date.today().year - 80,
        },
        "pk_mode_label": pk_mode_label,
        "breakdown": pension_breakdown,
        "breakdown_total_gross": chf(pk_breakdown_gross + pk2_breakdown_gross + total_3a_gross + pillar3b_gross),
        "breakdown_total_net": chf(pk_usable_net + pk2_usable_net + total_3a_net + pillar3b_net),
    }


HELP_HTML = """
<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"><link rel="icon" type="image/png" href="/favicon.png"><title>Hilfe</title>""" + STYLE + """</head>
<body><div class="wrap">
<div class="header">
  <div><h1>Hilfe</h1><div class="subtitle">Weil Pension komplizierter ist als gedacht 🤯</div></div>
  <div class="topnav"><a class="btn gray" href="/{% if scenario_id %}?id={{ scenario_id }}{% endif %}">Zurück</a></div>
</div>

<div class="card">
  <div class="card-title">Schnellstart — in 4 Schritten zur Pension (oder zur Erkenntnis dass es knapp wird) 🎯</div>
  <div class="card-subtitle">In 4 Schritten zur Pensionsplanung.</div>
  <ul>
    <li><b>Schritt 1 — AHV ermitteln:</b> Nutze den AHV-Rechner (oben in der Navigation) um deine voraussichtliche AHV-Rente zu berechnen. Das Ergebnis direkt mit dem Button "AHV-Rente ins Haupttool übernehmen" ins aktive Szenario übertragen.</li>
    <li><b>Schritt 2 — Vorsorgeausweise eintragen:</b> Altersguthaben und Umwandlungssatz direkt von deinem PK-Ausweis übernehmen. Säule 3a Konten einzeln erfassen.</li>
    <li><b>Schritt 3 — Vermögen und Wunschrente:</b> Depots, Sparkonto, Immobilien und gewünschte Monatsrente eintragen. Dann auf Berechnen klicken.</li>
    <li><b>Schritt 4 — Szenarien vergleichen:</b> Verschiedene Varianten (z.B. Rente vs. Kapital) als separate Szenarien speichern und vergleichen. PDF exportieren wenn das Resultat passt.</li>
  </ul>
</div>

<div class="card">
  <div class="card-title">Eingaben erklärt (ja, alle müssen ausgefüllt werden) 📝</div>
  <table>
    <colgroup><col style="width:22%"><col style="width:78%"></colgroup>
    <tr><th>Bereich</th><th>Bedeutung</th></tr>
    <tr><td>Wunschrente</td><td>Gewünschter monatlicher Nettobetrag im Rentenalter. Basis für den Vergleich.</td></tr>
    <tr><td>AHV/Monat</td><td>Voraussichtliche AHV-Rente inkl. 13. Rente: Jahresrente ÷ 12. Empfehlung: AHV-Rechner verwenden.</td></tr>
    <tr><td>Pensionskasse</td><td>Altersguthaben und Umwandlungssatz direkt gemäss aktuellem PK-Ausweis eintragen.</td></tr>
    <tr><td>Kader-Pensionskasse</td><td>Nur ausfüllen wenn eine separate Kader-PK vorhanden ist. Sonst Altersguthaben leer lassen.</td></tr>
    <tr><td>Variante</td><td>Rente = monatliche Rente. Kapital = Einmalauszahlung minus Steuern. Mischvariante = beides kombiniert.</td></tr>
    <tr><td>Säule 3a</td><td>Jedes 3a-Konto separat erfassen. Auszahlung wird automatisch auf 5 Jahre gestaffelt (Steueroptimierung). Die laufende Einzahlung wird nur auf Konto 5 gemacht — dieses wird zuletzt ausgezahlt und hat damit am längsten Zeit zum Wachsen. Der jährliche Maximalbetrag wird regelmässig angepasst — aktuellen Betrag beim Arbeitgeber oder unter <a href="https://www.raiffeisen.ch/rch/de/privatkunden/vorsorgen-absichern/maximalbetrag.html" target="_blank" rel="noopener" style="color:#60a5fa">raiffeisen.ch</a> prüfen.</td></tr>
    <tr><td>Säule 3b</td><td>Freie Vorsorge ausserhalb der Säule 3a. Keine Kapitalbezugssteuer im Tool.</td></tr>
    <tr><td>Depots / Investitionen</td><td>ETF, Aktien, Fonds oder sonstiges Depotvermögen. Keine Kapitalbezugssteuer im Tool.</td></tr>
    <tr><td>Sparkonto</td><td>Liquide Mittel auf Spar- oder Kontokorrentkonten.</td></tr>
    <tr><td>Immobilien</td><td>Aktueller Marktwert der Liegenschaft abzüglich Hypothek ergibt das Eigenkapital.</td></tr>
  </table>
</div>

<div class="card">
  <div class="card-title">Die Mathematik dahinter (keine Zauberei) 🧮</div>
  <table>
    <tr><th>Bereich</th><th>Rechenlogik</th></tr>
    <tr><td>Stichtag</td><td>Alle Vermögenswerte werden per 01. Januar des aktuellen Jahres erfasst. Die Berechnung startet ab diesem Datum.</td></tr>
    <tr><td>Pärchen-Übersicht</td><td>Zwei Szenarien zusammenrechnen — ideal für Paare. Jede Person erstellt ihr eigenes Szenario, die Pärchen-Übersicht addiert die Resultate. Erreichbar über den Button "Pärchen" in der Navigation.</td></tr>
    <tr><td>Pensionierungsdatum</td><td>Ende des Monats nach dem 65. Geburtstag (ordentliche Pension).</td></tr>
    <tr><td>Renditeberechnung</td><td>Kapital + Jahreseinzahlungen, danach Rendite auf den Gesamtbetrag (Zinseszins).</td></tr>
    <tr><td>PK Rente</td><td>Altersguthaben bei Pension × Umwandlungssatz ÷ 12 = monatliche Rente.</td></tr>
    <tr><td>PK Kapital</td><td>Altersguthaben bei Pension minus Kapitalbezugssteuer = Nettokapital.</td></tr>
    <tr><td>PK Mischvariante</td><td>Gewählter Kapitalanteil wird versteuert, verbleibender Rest als Monatsrente gerechnet.</td></tr>
    <tr><td>Säule 3a Staffelung</td><td>Konten werden einzeln über 5 Jahre ausgezahlt. Rendite läuft bis Ende Auszahlungsjahr, dann Steuerabzug.</td></tr>
    <tr><td>Aus Kapital pro Monat</td><td>Gesamtkapital nach Steuern ÷ Bezugsjahre ÷ 12. Keine Rendite auf Kapitalverzehr gerechnet.</td></tr>
    <tr><td>Nettovermögen heute</td><td>Depots + Sparkonto + Immobilien-Eigenkapital (ohne Vorsorge).</td></tr>
  </table>
</div>

<div class="card">
  <div class="card-title">AHV-Rechner (der Moment der Wahrheit) 😬</div>
  <div class="card-subtitle">Der AHV-Rechner hilft dir, deine voraussichtliche Rente auf Basis deiner Einkommenshistorie zu berechnen.</div>
  <ul>
    <li>44 Beitragsjahre werden automatisch aus dem Geburtsdatum berechnet. Das Pensionsjahr zählt nicht mit.</li>
    <li>Einkommen jahresweise eintragen. Leere Folgejahre werden mit dem letzten eingetragenen Lohn weitergeführt.</li>
    <li>Lückenjahre (Einkommen unter CHF 5'000) werden markiert und beeinflussen die Rentenberechnung.</li>
    <li>Ab 2026 wird eine 13. AHV-Rente ausbezahlt. Diese ist im Jahresbetrag bereits enthalten.</li>
    <li>Das Ergebnis direkt mit dem Button "AHV-Rente ins Haupttool übernehmen" ins aktive Szenario übertragen.</li>
    <li>Offiziellen Kontoauszug direkt bei der AHV bestellen: <a href="https://www.ahv-iv.ch/de/Formulare/Bestellung-Kontoauszug/Schweiz" target="_blank" rel="noopener" style="color:#60a5fa">ahv-iv.ch</a></li>
  </ul>
</div>

<div class="card">
  <div class="card-title">Ergebnisse verstehen (tief durchatmen) 🧘</div>
  <table>
    <tr><th>Kennzahl</th><th>Bedeutung</th></tr>
    <tr><td>Total Rente pro Monat</td><td>AHV + PK-Renten + monatlicher Kapitalverbrauch aus dem Gesamtkapital.</td></tr>
    <tr><td>Vergleich zu Wunschrente</td><td>Positiv = Überdeckung, Negativ = Lücke zur gewünschten Monatsrente.</td></tr>
    <tr><td>AHV + PK-Rente pro Monat</td><td>Fixer monatlicher Einkommensteil aus AHV und Pensionskassenrente.</td></tr>
    <tr><td>Aus Kapital pro Monat</td><td>Variabler Teil aus dem Kapitalverzehr über die gewünschte Bezugsdauer.</td></tr>
    <tr><td>Vorsorgevermögen nach Steuern</td><td>PK + Säule 3a nach Kapitalbezugssteuern. Basis für den Kapitalverbrauch.</td></tr>
    <tr><td>Nettovermögen bei Pension (ohne Vorsorge)</td><td>Depots, Sparkonto und Immobilien-Eigenkapital zum Pensionszeitpunkt.</td></tr>
  </table>
</div>

<div class="card">
  <div class="card-title">Das Kleingedruckte 🔍</div>
  <ul>
    <li>Dieses Tool ist eine Planungs- und Vergleichshilfe — keine Steuer-, Rechts- oder Finanzberatung.</li>
    <li>AHV-Renten, Umwandlungssätze und Steuerreglemente können sich ändern und variieren je nach Kanton und PK-Reglement.</li>
    <li>Verbindliche Auskunft erteilen: PK-Ausweis, AHV-Kontoauszug, kantonales Steueramt und zugelassene Finanzberater.</li>
    <li>Alle Beträge in CHF, alle Berechnungen basieren auf den eingegebenen Werten ohne Inflationsanpassung.</li>
  </ul>
</div>

</div><div class="footer-version">Version 3.0 · Weil die AHV alleine nicht reicht · Stand {{ now }}</div>
""" + SHARED_JS + """

</body></html>
"""


init_db()  # Einmalig beim Serverstart


@app.route("/help")
def help_page():
    if not require_login():
        return redirect(url_for("login"))
    scenario_id = request.args.get("id")
    return render_template_string(HELP_HTML, scenario_id=scenario_id)


AHV_DEFAULT_INCOMES = """2025=136148
2024=134800
2023=132450
2022=122500
2021=127982
2020=115550
2019=106705
2018=106200
2017=108422
2016=109927
2015=103316
2014=98071
2013=101391
2012=114422
2011=118797
2010=105277
2009=85726
2008=98379
2007=79642
2006=67713
2005=63291
2004=63660
2003=59778
2002=51311
2001=22968"""

AHV_SKALA_44 = [
    (90720, 2520), (89208, 2500), (87696, 2480), (86184, 2460),
    (84672, 2439), (83160, 2419), (81648, 2399), (80136, 2379),
    (78624, 2359), (77112, 2339), (75600, 2318), (74088, 2298),
    (72576, 2278), (71064, 2258), (69552, 2238), (68040, 2218),
    (66528, 2197), (65016, 2177), (63504, 2157), (61992, 2137),
    (60480, 2117), (58968, 2097), (57456, 2076), (55944, 2056),
    (54432, 2036), (52920, 2016), (51408, 1996), (49896, 1976),
    (48384, 1955), (46872, 1935), (45360, 1915), (43848, 1895),
    (42336, 1875), (40824, 1854), (39312, 1834), (37800, 1814),
    (36288, 1794), (34776, 1774), (33264, 1753), (31752, 1733),
    (30240, 1713), (28728, 1693), (27216, 1673), (25704, 1652),
    (24192, 1632), (22680, 1612), (21168, 1592), (19656, 1572),
    (18144, 1551), (16632, 1531), (15120, 1511), (13608, 1491),
    (12096, 1471), (10584, 1450), (9072, 1430), (7560, 1410),
    (6048, 1390), (4536, 1370), (3024, 1350), (0, 1260),
]

def ahv_years_for_birth(birth_date):
    birth = parse_date(birth_date, DEFAULTS["birth_date"])
    pension = ordinary_pension_date(birth)
    last_year = pension.year - 1
    first_year = last_year - 43
    return list(range(first_year, last_year + 1))


def calc_ahv_result(birth_date, incomes):
    birth = parse_date(birth_date, DEFAULTS["birth_date"])
    pension = ordinary_pension_date(birth)
    years = ahv_years_for_birth(birth_date)

    clean = {}
    last_income = 0
    for y in years:
        raw = str(incomes.get(y, "")).strip()
        if raw != "":
            last_income = parse_number(raw, last_income)
        clean[y] = last_income

    total_income = sum(clean.values())
    average_income = total_income / 44

    gap_years = sum(1 for value in clean.values() if value < 5000)

    pension_month_base = AHV_SKALA_44[-1][1]
    for threshold, pension_value in AHV_SKALA_44:
        if average_income >= threshold:
            pension_month_base = pension_value
            break

    pension_month = pension_month_base * max(0, 44 - gap_years) / 44

    table_rows = [(y, chf(clean[y])) for y in sorted(years, reverse=True)]
    filled_income_by_year = {y: chf(clean[y]) for y in years}

    return {
        "filled_income_by_year": filled_income_by_year,
        "pension_date": pension.strftime("%d.%m.%Y"),
        "average_income": chf(average_income),
        "gap_years": gap_years,
        "ahv_month": chf(pension_month),
        "ahv_month_raw": round(pension_month * 13 / 12),
        "ahv_year": chf(pension_month * 13),
        "pension_year": pension.year,
        "table_rows": table_rows,
    }

AHV_HTML = """
<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"><link rel="icon" type="image/png" href="/favicon.png"><title>AHV-Rechner</title>""" + STYLE + """</head>
<body><div class="wrap">
<div class="header">
  <div><h1>AHV-Rechner</h1><div class="subtitle">Spoiler: Es wird nicht viel sein. 😅</div></div>
  <div class="topnav"><a class="btn gray" href="/{% if scenario_id %}?id={{ scenario_id }}{% endif %}">Zurück</a><a class="btn gray" target="_blank" rel="noopener" href="https://www.ahv-iv.ch/de/Formulare/Bestellung-Kontoauszug/Schweiz">Kontoauszug bestellen</a><a class="btn gray" href="/ahv">Von vorne anfangen 🙈</a></div>
</div>

<div class="card" style="border-color:#2563eb">
  <div class="card-title">AHV-Hinweis</div>
  <div class="card-subtitle">Der AHV-Rechner speichert die Eingaben im aktuellen Szenario. Das Ergebnis wird bewusst nicht automatisch ins Haupttool übernommen.</div>
</div>

{% if result %}
<div class="card" style="border-color:#22c55e;margin-top:18px">
  <div class="card-title">AHV-Ergebnis (die Ernüchterung) 😬</div>
  <div class="grid">
    <div class="field"><label>Pensionierungsdatum</label><input type="text" value="{{ result.pension_date }}" readonly></div>
    <div class="field"><label>Durchschnittliches Einkommen</label><input type="text" value="{{ result.average_income }}" readonly></div>
    <div class="field"><label>Beitragslücken (aka verlorene Jahre) 🕳️</label><input type="text" value="{{ result.gap_years }}" readonly></div>
    <div class="field"><label>AHV Rente pro Monat</label><input type="text" value="{{ result.ahv_month }}" readonly></div>
    <div class="field"><label>AHV Rente pro Jahr (x13)</label><input type="text" value="{{ result.ahv_year }}" readonly></div>
  </div>
  {% if (request.form.get("married") or saved_married) and (request.form.get("partner_ahv") or saved_partner_ahv) %}
  {% set own = result.ahv_month | replace("'", "") | float %}
  {% set partner = (request.form.get("partner_ahv") or saved_partner_ahv) | replace("'", "") | float %}
  {% set total = own + partner %}
  {% set plafond = 3780 %}
  {% if total > plafond %}
  {% set own_plaf = (own * plafond / total) | round(0) | int %}
  {% set partner_plaf = (partner * plafond / total) | round(0) | int %}
  <div style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);border-radius:12px;padding:14px;margin-top:14px">
    <div style="font-size:13px;font-weight:700;color:#fca5a5;margin-bottom:10px">⚠ Plafonierung bei Verheirateten (max. CHF 3'780/Monat) — der Staat gönnt euch nicht mehr. Typisch!</div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px">
      <div style="text-align:center;background:rgba(0,0,0,.2);border-radius:8px;padding:10px">
        <div style="font-size:11px;color:#94a3b8;margin-bottom:4px">Deine Rente</div>
        <div style="font-size:18px;font-weight:900;color:#fca5a5">{{ own_plaf | int }}</div>
      </div>
      <div style="text-align:center;background:rgba(0,0,0,.2);border-radius:8px;padding:10px">
        <div style="font-size:11px;color:#94a3b8;margin-bottom:4px">Partner/in</div>
        <div style="font-size:18px;font-weight:900;color:#fca5a5">{{ partner_plaf | int }}</div>
      </div>
      <div style="text-align:center;background:rgba(0,0,0,.2);border-radius:8px;padding:10px">
        <div style="font-size:11px;color:#94a3b8;margin-bottom:4px">Total</div>
        <div style="font-size:18px;font-weight:900;color:#fca5a5">{{ plafond }}</div>
      </div>
    </div>
    <div style="font-size:12px;color:#94a3b8;margin-top:10px">Bitte plafonierte Rente manuell ins Haupttool übertragen.</div>
  </div>
  {% else %}
  <div style="background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);border-radius:12px;padding:14px;margin-top:14px">
    <div style="font-size:13px;font-weight:700;color:#86efac">✓ Keine Plafonierung — Total CHF {{ total | int }}/Monat unter dem Limit</div>
  </div>
  {% endif %}
  {% endif %}
  {% if scenario_id %}
  <form method="post" action="/ahv_transfer" style="margin-top:14px">
    <input type="hidden" name="scenario_id" value="{{ scenario_id }}">
    {% if (request.form.get("married") or saved_married) and (request.form.get("partner_ahv") or saved_partner_ahv) %}
    {% set own = result.ahv_month | replace("'", "") | float %}
    {% set partner = request.form.get("partner_ahv") | replace("'", "") | float %}
    {% set total = own + partner %}
    {% if total > 3780 %}
    <input type="hidden" name="ahv_month_raw" value="{{ (own * 3780 / total) | round(0) | int }}">
    {% else %}
    <input type="hidden" name="ahv_month_raw" value="{{ result.ahv_month_raw }}">
    {% endif %}
    {% else %}
    <input type="hidden" name="ahv_month_raw" value="{{ result.ahv_month_raw }}">
    {% endif %}
    <button type="submit" style="background:#22c55e;border:0;border-radius:12px;color:white;padding:10px 18px;font-size:14px;font-weight:700;cursor:pointer">AHV-Rente ins Haupttool übernehmen</button>
  </form>
  {% endif %}
</div>
{% endif %}

<form method="post">
<div class="card">
  <div class="card-title">Eingaben</div>
  <div class="grid">
    <div class="field"><label>Geburtsdatum<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Dein Geburtsdatum. Bestimmt das Pensionierungsdatum (Ende Monat nach 65. Geburtstag).</span></span></label><input name="birth_date" type="date" value="{{ birth_date }}"></div>
    <div class="field"><label>Verheiratet / eingetragene Partnerschaft<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Bei Verheirateten werden beide AHV-Renten proportional auf max. CHF 3'780/Monat plafoniert.</span></span></label>
      <div style="display:flex;align-items:center;gap:12px;margin-top:8px">
        <input type="checkbox" name="married" id="married" value="1" {% if request.form.get("married") or saved_married %}checked{% endif %} style="width:20px;height:20px;min-height:0;cursor:pointer" onchange="document.getElementById('partner-field').style.display=this.checked?'block':'none'">
        <label for="married" style="margin:0;font-size:14px;cursor:pointer">Ja, ich bin verheiratet</label>
      </div>
    </div>
    <div class="field" id="partner-field" style="display:{% if request.form.get('married') or saved_married %}block{% else %}none{% endif %}">
      <label>AHV-Rente Partner/in pro Monat (ohne 13. Rente)<span class="tooltip-wrap"><span class="tooltip-icon" onclick="var b=this.nextElementSibling;var was=b.style.display==='block';document.querySelectorAll('.tooltip-box').forEach(function(x){x.style.display='none'});b.style.display=was?'none':'block'">i</span><span class="tooltip-box">Monatliche AHV-Rente des Partners/der Partnerin gemäss AHV-Ausweis. Wird für die Plafonierungsberechnung verwendet.</span></span></label>
      <input name="partner_ahv" type="text" inputmode="decimal" id="partner_ahv" value="{{ request.form.get('partner_ahv', saved_partner_ahv) }}" placeholder="z.B. 2'200">
    </div>
  </div>
  <div class="card" class="mt">
    
</div>

    <table>
      <tr>
        <th colspan="3" style="font-size:18px;text-align:left;border-right:4px solid #64748b">AHV-pflichtige Einkommen</th>
        <th colspan="2" style="font-size:18px;text-align:right;padding-right:18px">Skala 44</th>
      </tr>
      <tr>
        <th>Jahr</th>
        <th class="num" style="width:180px">Lohn manuell</th>
        <th class="num" style="border-right:4px solid #64748b">Lohn gerechnet</th>
        <th class="num">Ø Einkommen</th>
        <th class="num">AHV/Monat</th>
      </tr>

      {% for row in ahv_table_rows %}
      <tr>
        <td>{{ row.year if row.year }}</td>
        <td class="num">
          {% if row.year %}
          <input name="income_{{ row.year }}" type="text" inputmode="decimal" style="max-width:160px" value="{{ input_value(row.manual) if row.manual else "" }}">
          {% endif %}
        </td>
        <td class="num" style="border-right:4px solid #64748b">{{ row.filled }}</td>
        
        <td class="num">{{ row.scale_income }}</td>
        <td class="num">{{ row.scale_pension }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  <button type="submit" class="mt">AHV berechnen</button>
</div>
</form>


</div><div class="footer-version">Version 3.0 · Weil die AHV alleine nicht reicht · Stand {{ now }}</div>
""" + SHARED_JS + """

</body></html>
"""

def save_ahv_to_scenario(scenario_id, incomes):
    if not scenario_id:
        return

    conn = db()
    conn.execute(
        "UPDATE scenarios SET ahv_incomes_json=? WHERE id=? AND user_id=?",
        (json.dumps(incomes), scenario_id, current_user_id())
    )
    conn.commit()
    conn.close()

def load_ahv_from_scenario(scenario_id):
    if not scenario_id:
        return {}

    row = get_scenario(scenario_id)
    if not row or "ahv_incomes_json" not in row.keys():
        return {}

    try:
        raw = row["ahv_incomes_json"] or "{}"
        data = json.loads(raw)
        result = {}
        for k, v in data.items():
            if str(k).startswith("__"):
                result[k] = v
            else:
                try:
                    result[int(k)] = v
                except (ValueError, TypeError):
                    pass
        return result
    except Exception:
        return {}


@app.route("/ahv", methods=["GET", "POST"])
def ahv_page():
    if not require_login():
        return redirect(url_for("login"))

    scenario_id = request.args.get("id")
    scenario = normalize_row(get_scenario(scenario_id)) if scenario_id and get_scenario(scenario_id) else None

    birth_date = scenario["birth_date"] if scenario else DEFAULTS["birth_date"]
    result = None

    if request.args.get("reset") == "1":
        save_ahv_to_scenario(scenario_id, {})

    default_incomes = load_ahv_from_scenario(scenario_id)
    saved_married = str(default_incomes.pop("__married__", ""))
    saved_partner_ahv = str(default_incomes.pop("__partner_ahv__", ""))

    if request.method == "POST":
        saved_married = request.form.get("married", "")
        saved_partner_ahv = request.form.get("partner_ahv", "")
        birth_date = request.form.get("birth_date", birth_date)
    years = ahv_years_for_birth(birth_date)
    incomes = {}
    for y in years:
        if request.method == "POST":
            incomes[y] = request.form.get(f"income_{y}", "")
        else:
            incomes[y] = default_incomes.get(y, "")

    if request.method == "POST":
        incomes["__married__"] = saved_married
        incomes["__partner_ahv__"] = saved_partner_ahv
        save_ahv_to_scenario(scenario_id, incomes)
        result = calc_ahv_result(birth_date, incomes)
    elif any(str(v).strip() for v in incomes.values()):
        result = calc_ahv_result(birth_date, incomes)

    scale_rows = [(chf(threshold), chf(pension)) for threshold, pension in AHV_SKALA_44]
    years_desc = sorted(years, reverse=True)
    max_rows = max(len(years_desc), len(scale_rows))

    ahv_table_rows = []
    for i in range(max_rows):
        y = years_desc[i] if i < len(years_desc) else None
        scale_income, scale_pension = scale_rows[i] if i < len(scale_rows) else ("", "")

        ahv_table_rows.append({
            "year": y,
            "manual": chf(parse_number(incomes.get(y, ""),0)) if incomes.get(y,"") not in ["",None] and y else "",
            "filled": result["filled_income_by_year"].get(y, "") if result and y else "",
            "scale_income": scale_income,
            "scale_pension": scale_pension,
        })

    return render_template_string(
        AHV_HTML,
        birth_date=birth_date,
        ahv_table_rows=ahv_table_rows,
        result=result,
        scenario_id=scenario_id,
        input_value=input_value,
        saved_married=saved_married,
        saved_partner_ahv=saved_partner_ahv
    )



CHANGE_PW_HTML = """
<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="icon" type="image/png" href="/favicon.png"><title>Passwort ändern</title>""" + STYLE + """</head>
<body>
<div style="min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px">
  <div style="width:100%;max-width:420px">
    <div style="text-align:center;margin-bottom:24px">
      <div style="font-size:48px;margin-bottom:12px">🔐</div>
      <h1 style="margin:0 0 8px;font-size:24px">Passwort ändern (hoffentlich was Besseres als 1234) 🔐</h1>
      <p style="color:#94a3b8;margin:0;font-size:14px;line-height:1.5">Du musst dein Initialpasswort ändern bevor du fortfahren kannst.</p>
    </div>
    <div class="card" style="padding:28px">
      {% if error %}<div style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);border-radius:10px;padding:10px 14px;color:#fca5a5;font-size:13px;margin-bottom:16px">{{ error }}</div>{% endif %}
      <form method="post">
        <div class="field" style="margin-bottom:14px">
          <label>Neues Passwort</label>
          <input name="password" type="password" id="pw-input" oninput="checkPw(this.value)" autocomplete="new-password">
          <div id="pw-strength" style="margin-top:6px;height:4px;border-radius:99px;background:#e2e8f0;overflow:hidden"><div id="pw-bar" style="height:100%;width:0%;transition:.3s;border-radius:99px"></div></div>
          <div id="pw-label" style="font-size:11px;color:#64748b;margin-top:4px"></div>
        </div>
        <div class="field" style="margin-bottom:20px">
          <label>Passwort bestätigen</label>
          <input name="confirm_password" type="password" autocomplete="new-password">
        </div>
        <div style="background:#f1f5f9;border-radius:10px;padding:12px;margin-bottom:16px;font-size:12px">
          <b style="color:#e5e7eb;display:block;margin-bottom:6px">Anforderungen:</b>
          <div id="req-len" style="color:#ef4444">✗ Mindestens 10 Zeichen</div>
          <div id="req-upper" style="color:#ef4444">✗ Mindestens ein Grossbuchstabe</div>
          <div id="req-num" style="color:#ef4444">✗ Mindestens eine Zahl</div>
          <div id="req-special" style="color:#ef4444">✗ Mindestens ein Sonderzeichen (!@#$%...)</div>
        </div>
        <button type="submit" style="width:100%;background:linear-gradient(135deg,#2563eb,#0ea5e9);border:0;border-radius:14px;color:white;font-size:16px;font-weight:700;padding:14px;cursor:pointer">Passwort speichern</button>
      </form>
    </div>
  </div>
</div>
<script>
function checkPw(val) {
  var bar = document.getElementById('pw-bar');
  var label = document.getElementById('pw-label');
  if (!bar) return;
  var score = 0;
  if (val.length >= 10) score++;
  if (val.length >= 14) score++;
  if (/[A-Z]/.test(val)) score++;
  if (/[0-9]/.test(val)) score++;
  if (/[^A-Za-z0-9]/.test(val)) score++;
  var colors = ['#ef4444','#f97316','#eab308','#22c55e','#10b981'];
  var labels = ['Sehr schwach','Schwach','Mittel','Stark','Sehr stark'];
  bar.style.width = (score * 20) + '%';
  bar.style.background = colors[Math.max(0,score-1)];
  label.textContent = val.length > 0 ? (labels[score-1] || 'Sehr stark') : '';
  label.style.color = colors[Math.max(0,score-1)];
  // Anforderungen farbig
  function setReq(id, ok) {
    var el = document.getElementById(id);
    if (!el) return;
    el.style.color = ok ? '#22c55e' : '#ef4444';
    el.textContent = (ok ? '✓' : '✗') + el.textContent.substring(1);
  }
  setReq('req-len', val.length >= 10);
  setReq('req-upper', /[A-Z]/.test(val));
  setReq('req-num', /[0-9]/.test(val));
  setReq('req-special', /[^A-Za-z0-9]/.test(val));
}
</script>
</body></html>
"""

PAERCHEN_HTML = """
<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="icon" type="image/png" href="/favicon.png"><title>Pärchen-Übersicht</title>""" + STYLE + """</head>
<body><div class="wrap">
<div class="header">
  <div><h1>Pärchen-Übersicht</h1><div class="subtitle">Doppelt hält besser — auch bei der Altersvorsorge! 👫</div></div>
  <div class="topnav"><a class="btn gray" href="/{% if scenario_id %}?id={{ scenario_id }}{% endif %}">Zurück</a></div>
</div>

<div class="card">
  <div class="card-title">Szenarien auswählen</div>
  <form method="post">
    <div class="grid">
      <div class="field"><label>Person 1</label>
        <select name="id1">
          <option value="">— auswählen —</option>
          {% for s in scenarios %}<option value="{{ s.id }}" {% if s.id|string == id1 %}selected{% endif %}>{{ s.name }}</option>{% endfor %}
        </select>
      </div>
      <div class="field"><label>Person 2</label>
        <select name="id2">
          <option value="">— auswählen —</option>
          {% for s in scenarios %}<option value="{{ s.id }}" {% if s.id|string == id2 %}selected{% endif %}>{{ s.name }}</option>{% endfor %}
        </select>
      </div>
    </div>
    <button type="submit" class="mt">Gemeinsam rechnen 🧮</button>
  </form>
</div>

{% if r1 and r2 %}
<div class="print-title" style="display:block;border-bottom:2px solid #334155;padding-bottom:10px;margin-bottom:18px">
  <h1 style="color:var(--text)">{{ name1 }} &amp; {{ name2 }}</h1>
  <div>Pärchen-Übersicht · Gemeinsame Pensionsplanung</div>
</div>

<div class="kpis">
  <div class="kpi main" style="border-color:#22c55e;box-shadow:0 18px 50px rgba(34,197,94,.15)">
    <div class="kpi-label">Total Rente pro Monat</div>
    <div class="kpi-value ok">{{ total_available_month }}</div>
  </div>
  <div class="kpi main">
    <div class="kpi-label">AHV + PK-Rente pro Monat</div>
    <div class="kpi-value">{{ total_fixed_income }}</div>
  </div>
  <div class="kpi main">
    <div class="kpi-label">Aus Kapital pro Monat</div>
    <div class="kpi-value">{{ total_capital_income }}</div>
  </div>
  <div class="kpi main">
    <div class="kpi-label">Wunschrente Total</div>
    <div class="kpi-value">{{ total_wunschrente }}</div>
  </div>
  <div class="kpi sub">
    <div class="kpi-label">Vorsorgevermögen bei Pension nach Steuern</div>
    <div class="kpi-value">{{ total_at_retirement }}</div>
  </div>
  <div class="kpi sub">
    <div class="kpi-label">Nettovermögen bei Pension (ohne Vorsorge)</div>
    <div class="kpi-value">{{ total_net_worth }}</div>
  </div>
</div>

<div class="card" style="margin-top:18px">
  <div class="card-title">Vergleich</div>
  <table>
    <colgroup><col style="width:34%"><col style="width:22%"><col style="width:22%"><col style="width:22%"></colgroup>
    <tr><th>Kennzahl</th><th class="num">{{ name1 }}</th><th class="num">{{ name2 }}</th><th class="num">Total</th></tr>
    <tr><td>AHV + PK-Rente/Monat</td><td class="num">{{ r1.fixed_income_month }}</td><td class="num">{{ r2.fixed_income_month }}</td><td class="num">{{ total_fixed_income }}</td></tr>
    <tr><td>Aus Kapital/Monat</td><td class="num">{{ r1.capital_monthly_income }}</td><td class="num">{{ r2.capital_monthly_income }}</td><td class="num">{{ total_capital_income }}</td></tr>
    <tr><td><b>Total Rente/Monat</b></td><td class="num"><b>{{ r1.total_available_month }}</b></td><td class="num"><b>{{ r2.total_available_month }}</b></td><td class="num"><b>{{ total_available_month }}</b></td></tr>
    <tr><td>Vorsorgevermögen nach Steuern</td><td class="num">{{ r1.total_at_retirement }}</td><td class="num">{{ r2.total_at_retirement }}</td><td class="num">{{ total_at_retirement }}</td></tr>
    <tr><td>Nettovermögen bei Pension</td><td class="num">{{ r1.net_worth_retirement }}</td><td class="num">{{ r2.net_worth_retirement }}</td><td class="num">{{ total_net_worth }}</td></tr>
  </table>
</div>
{% endif %}

</div><div class="footer-version">Version 3.0 · Weil die AHV alleine nicht reicht · Stand {{ now }}</div>
""" + SHARED_JS + """
<script>
function handleTooltip(e){
  var icon=e.target.closest(".tooltip-icon");
  if(icon){
    e.preventDefault();
    e.stopPropagation();
    var wrap=icon.closest(".tooltip-wrap");
    var was=wrap.classList.contains("active");
    document.querySelectorAll(".tooltip-wrap").forEach(function(w){w.classList.remove("active");});
    if(!was)wrap.classList.add("active");
  } else {
    document.querySelectorAll(".tooltip-wrap").forEach(function(w){w.classList.remove("active");});
  }
}
document.addEventListener("click",handleTooltip);
document.addEventListener("touchend",handleTooltip);
</script>
</body></html>
"""

REPORT_HTML = """
<!doctype html><html lang="de"><head><meta charset="utf-8">
<title>Schweizer Pension Tool — weil Excel zu langweilig ist</title>
<style>
@page{margin:14mm}
body{font-family:Arial,sans-serif;color:#111;margin:0;background:white;font-size:12px}
.report{max-width:980px;margin:0 auto}
.hero{background:#0f172a;color:white;border-radius:18px;padding:26px 30px;margin-bottom:18px}
.hero h1{margin:0 0 8px;font-size:30px}
.hero div{color:var(--muted);font-size:14px}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:18px}
.kpi{border:1px solid #d6dbe5;border-radius:14px;padding:13px;background:#f8fafc}
.kpi-label{font-size:9px;text-transform:uppercase;letter-spacing:.06em;color:#64748b;font-weight:800;margin-bottom:8px}
.kpi-value{font-size:20px;font-weight:900;color:#0f172a}
.section-title{font-size:18px;font-weight:900;margin:22px 0 8px;border-bottom:2px solid #111;padding-bottom:6px}
table{width:100%;border-collapse:collapse;font-size:11px}
th{background:#0f172a;color:white;text-align:left;padding:8px;font-size:10px}
td{padding:7px 8px;border-bottom:1px solid #ddd}
tr:nth-child(even) td{background:#f8fafc}
.num{text-align:right;white-space:nowrap}
.total td{font-weight:900;border-top:2px solid #111;border-bottom:2px solid #111;background:white!important}
.notes{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:10px}
.note{border:1px solid #d6dbe5;border-radius:12px;padding:12px;background:#f8fafc}
.note b{display:block;margin-bottom:5px}
.footer{margin-top:22px;color:#64748b;font-size:10px;text-align:right}

</style>
</head><body>
<div class="report">
  <div class="hero">
    <h1>Schweizer Pension Tool</h1>
    <div>Szenario: {{ data.name }} · Pension: {{ result.pension_date_formatted }} · Erstellt: {{ created }}</div>
  </div>

<div class="kpis">

  <div class="kpi main">
    <div class="kpi-label">Total Rente pro Monat</div>
    <div class="kpi-value ok">{{ result.total_available_month }}</div>
  </div>

  <div class="kpi main">
    <div class="kpi-label">Vergleich zu Wunschrente</div>
    <div class="kpi-value {% if result.monthly_gap <= 0 %}ok{% else %}bad{% endif %}">{{ result.wunschrente_compare }}</div>
  </div>

  <div class="kpi main">
    <div class="kpi-label">AHV + PK-Rente pro Monat</div>
    <div class="kpi-value">{{ result.fixed_income_month }}</div>
  </div>

  <div class="kpi main">
    <div class="kpi-label">Aus Kapital pro Monat</div>
    <div class="kpi-value">{{ result.capital_monthly_income }}</div>
  </div>

  <div class="kpi sub">
    <div class="kpi-label">Nettovermögen heute</div>
    <div class="kpi-value">{{ result.net_worth_today }}</div>
  </div>

  <div class="kpi sub">
    <div class="kpi-label">Vorsorgevermögen bei Pension nach Steuern</div>
    <div class="kpi-value">{{ result.total_at_retirement }}</div>
  </div>

</div>


  <div class="section-title">Kapitalübersicht</div>
  <table>
    <tr><th>Posten</th><th class="num">Brutto</th><th class="num">Steuer</th><th class="num">Netto</th><th>Hinweis</th></tr>
    {% for row in result.breakdown %}
    <tr><td>{{ row.name }}</td><td class="num">{{ row.gross }}</td><td class="num">{{ row.tax }}</td><td class="num">{{ row.net }}</td><td>{{ row.note }}</td></tr>
    {% endfor %}
    <tr class="total"><td>Total</td><td class="num">{{ result.breakdown_total_gross }}</td><td class="num">{{ result.total_tax }}</td><td class="num">{{ result.breakdown_total_net }}</td><td></td></tr>
  </table>

  <div class="section-title">Annahmen</div>
  <div class="notes">
    <div class="note"><b>PK</b>Werte direkt gemäss PK-Ausweis, ohne Hochrechnung.</div>
    <div class="note"><b>Säule 3a</b>Gestaffelte Auszahlung, Steuer abgezogen.</div>
    <div class="note"><b>3b / Depot / Sparkonto</b>Rendite bis zum Pensionsmonat.</div>
  </div>

  <div class="footer">Planungs- und Vergleichshilfe · keine Steuer-, Rechts- oder Finanzberatung</div>
</div>
<script>
document.title = "Swiss Pension Tool - {{ data.name }}";
window.onload = function(){ setTimeout(function(){ window.print(); }, 300); };
</script>
</body></html>
"""


@app.route("/ahv_transfer", methods=["POST"])
def ahv_transfer():
    if not require_login():
        return redirect(url_for("login"))
    scenario_id = request.form.get("scenario_id")
    ahv_month_raw = request.form.get("ahv_month_raw", "0") or "0"
    if scenario_id:
        try:
            ahv_val = float(ahv_month_raw)
        except:
            ahv_val = 0
        conn = db()
        conn.execute(
            "UPDATE scenarios SET ahv=? WHERE id=? AND user_id=?",
            (ahv_val, scenario_id, current_user_id())
        )
        conn.commit()
        conn.close()
    return redirect(url_for("home", id=scenario_id))


@app.route("/paerchen", methods=["GET", "POST"])
def paerchen():
    if not require_login():
        return redirect(url_for("login"))
    scenario_id = request.args.get("id")
    scenarios = get_scenarios()
    saved = normalize_row(get_scenario(scenario_id)) if scenario_id and get_scenario(scenario_id) else {}
    if request.method == "POST":
        id1 = request.form.get("id1", "")
        id2 = request.form.get("id2", "")
    else:
        global _paerchen_id1, _paerchen_id2
        id1 = str(saved.get("paerchen_id1", "") or _paerchen_id1)
        id2 = str(saved.get("paerchen_id2", "") or _paerchen_id2)
    r1 = r2 = None
    name1 = name2 = ""
    total_available_month = total_fixed_income = total_capital_income = ""
    total_at_retirement = total_net_worth = total_wunschrente = ""

    if request.method == "POST":
        if id1 and id2:
            _paerchen_id1 = id1
            _paerchen_id2 = id2
        else:
            pass
        if scenario_id:
            conn = db()
            conn.execute("UPDATE scenarios SET paerchen_id1=?, paerchen_id2=? WHERE id=? AND user_id=?",
                (id1, id2, scenario_id, current_user_id()))
            conn.commit()
            conn.close()
    if id1 and id2 and id1 != id2:
        row1 = get_scenario(id1)
        row2 = get_scenario(id2)
        if row1 and row2:
            d1 = normalize_row(row1)
            d2 = normalize_row(row2)
            r1 = calculate(d1)
            r2 = calculate(d2)
            name1 = d1["name"]
            name2 = d2["name"]

            def pc(v):
                try:
                    return float(str(v).replace("'","").replace(" ","").strip() or 0)
                except:
                    return 0

            total_available_month = chf(pc(r1["total_available_month"]) + pc(r2["total_available_month"]))
            total_fixed_income = chf(pc(r1["fixed_income_month"]) + pc(r2["fixed_income_month"]))
            total_capital_income = chf(pc(r1["capital_monthly_income"]) + pc(r2["capital_monthly_income"]))
            total_at_retirement = chf(pc(r1["total_at_retirement"]) + pc(r2["total_at_retirement"]))
            total_net_worth = chf(pc(r1["net_worth_retirement"]) + pc(r2["net_worth_retirement"]))
            total_wunschrente = chf(d1["expenses"] + d2["expenses"])

    return render_template_string(
        PAERCHEN_HTML,
        scenarios=scenarios,
        scenario_id=scenario_id,
        id1=id1, id2=id2,
        r1=r1, r2=r2,
        name1=name1, name2=name2,
        total_available_month=total_available_month,
        total_fixed_income=total_fixed_income,
        total_capital_income=total_capital_income,
        total_at_retirement=total_at_retirement,
        total_net_worth=total_net_worth,
        total_wunschrente=total_wunschrente,
    )


@app.route("/report")
def report():
    if not require_login():
        return redirect(url_for("login"))

    sid = request.args.get("id")
    if not sid:
        return redirect(url_for("home"))

    row = get_scenario(sid)
    if not row:
        return redirect(url_for("home"))

    data = normalize_row(row)
    result = calculate(data)
    created = datetime.now().strftime("%d.%m.%Y")

    return render_template_string(REPORT_HTML, data=data, result=result, created=created)

@app.route("/login")
def login():
    return redirect(url_for("home"))

@app.route("/change_password_forced")
def change_password_forced():
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    return redirect(url_for("home"))

ACCOUNT_HTML = """
<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"><link rel="icon" type="image/png" href="/favicon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Swiss Pension Tool">
<link rel="apple-touch-icon" href="/favicon.png">
<title>Mein Konto</title>""" + STYLE + """</head>
<body><div class="wrap">
<div class="header">
  <div><h1>Mein Konto (wer bin ich und was will ich?) 🤔</h1><div class="subtitle">Benutzername und Passwort ändern.</div></div>
  <div class="topnav"><a class="btn gray" href="/{% if scenario_id %}?id={{ scenario_id }}{% endif %}">Zurück</a></div>
</div>

{% if message %}<div class="card" class="mb"><div class="card-title">{{ message }}</div></div>{% endif %}
{% if error %}<div class="card" class="mb"><div class="card-title bad">{{ error }}</div></div>{% endif %}

<div class="card">
<form method="post">
  <div class="grid">
    <div class="field">
      <label>Benutzername</label>
      <input name="username" value="{{ username }}">
    </div>
    <div class="field">
      <label>Neues Passwort leer lassen, wenn unverändert</label>
      <input name="password" type="password" id="pw-input" oninput="checkPw(this.value)">
      <div id="pw-strength" style="margin-top:6px;height:4px;border-radius:99px;background:#e2e8f0;overflow:hidden"><div id="pw-bar" style="height:100%;width:0%;transition:.3s;border-radius:99px"></div></div>
      <div id="pw-label" style="font-size:11px;color:#64748b;margin-top:4px"></div>
    </div>
    <div style="background:#f1f5f9;border-radius:10px;padding:12px;margin-bottom:16px;font-size:12px">
      <b style="color:#e5e7eb;display:block;margin-bottom:6px">Anforderungen:</b>
      <div id="req-len" style="color:#ef4444">✗ Mindestens 10 Zeichen</div>
      <div id="req-upper" style="color:#ef4444">✗ Mindestens ein Grossbuchstabe</div>
      <div id="req-num" style="color:#ef4444">✗ Mindestens eine Zahl</div>
      <div id="req-special" style="color:#ef4444">✗ Mindestens ein Sonderzeichen (!@#$%...)</div>
    </div>
  </div>
  <button type="submit" class="mt">Speichern</button>
</form>
</div>
</div><div class="footer-version">Version 3.0 · Weil die AHV alleine nicht reicht · Stand {{ now }}</div>
""" + SHARED_JS + """
<script>
function checkPw(val) {
  var bar = document.getElementById('pw-bar');
  var label = document.getElementById('pw-label');
  if (!bar) return;
  var score = 0;
  if (val.length >= 10) score++;
  if (val.length >= 14) score++;
  if (/[A-Z]/.test(val)) score++;
  if (/[0-9]/.test(val)) score++;
  if (/[^A-Za-z0-9]/.test(val)) score++;
  var colors = ['#ef4444','#f97316','#eab308','#22c55e','#10b981'];
  var labels = ['Sehr schwach','Schwach','Mittel','Stark','Sehr stark'];
  bar.style.width = (score * 20) + '%';
  bar.style.background = colors[Math.max(0,score-1)];
  label.textContent = val.length > 0 ? (labels[score-1] || 'Sehr stark') : '';
  label.style.color = colors[Math.max(0,score-1)];
  // Anforderungen farbig
  function setReq(id, ok) {
    var el = document.getElementById(id);
    if (!el) return;
    el.style.color = ok ? '#22c55e' : '#ef4444';
    el.textContent = (ok ? '✓' : '✗') + el.textContent.substring(1);
  }
  setReq('req-len', val.length >= 10);
  setReq('req-upper', /[A-Z]/.test(val));
  setReq('req-num', /[0-9]/.test(val));
  setReq('req-special', /[^A-Za-z0-9]/.test(val));
}
</script>

</body></html>
"""

@app.route("/account", methods=["GET", "POST"])
def account():
    if not require_login():
        return redirect(url_for("login"))

    message = None
    error = None
    conn = db()
    user = conn.execute(
        "SELECT id, username FROM users WHERE id=?",
        (current_user_id(),)
    ).fetchone()


    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username:
            error = "Benutzername darf nicht leer sein."
        else:
            try:
                if password:
                    conn.execute(
                        "UPDATE users SET username=?, password_hash=? WHERE id=?",
                        (username, generate_password_hash(password), current_user_id())
                    )
                else:
                    conn.execute(
                        "UPDATE users SET username=? WHERE id=?",
                        (username, current_user_id())
                    )

                conn.commit()
                session["username"] = username
                message = "Konto aktualisiert."
                user = conn.execute(
                    "SELECT id, username FROM users WHERE id=?",
                    (current_user_id(),)
                ).fetchone()
            except sqlite3.IntegrityError:
                error = "Dieser Benutzername existiert bereits."

    conn.close()
    return render_template_string(
        ACCOUNT_HTML,
        username=user["username"] if user else "",
        message=message,
        error=error,
        scenario_id=request.args.get("id")
    )

@app.route("/users", methods=["GET", "POST"])
def users():
    if not require_login():
        return redirect(url_for("login"))
    if not is_admin():
        return redirect(url_for("home"))
    scenario_id = request.args.get("id")

    delete_user_id = request.args.get("delete")
    if delete_user_id:
        uid = int(delete_user_id)
        if uid != 1:
            conn = db()
            conn.execute("DELETE FROM scenarios WHERE user_id=?", (uid,))
            conn.execute("DELETE FROM users WHERE id=?", (uid,))
            conn.commit()
            conn.close()
        return redirect(url_for("users"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username and password:
            conn = db()
            try:
                conn.execute(
                    "INSERT INTO users (username, password_hash, must_change_password) VALUES (?, ?, 1)",
                    (username, generate_password_hash(password))
                )
                conn.commit()
            except sqlite3.IntegrityError:
                pass
            conn.close()

        return redirect(url_for("users"))

    conn = db()
    all_users = conn.execute("SELECT id, username, last_seen FROM users ORDER BY id").fetchall()
    conn.close()
    return render_template_string(USERS_HTML, users=all_users, scenario_id=scenario_id)

@app.route("/", methods=["GET", "POST"])
def home():
    if not require_login():
        return redirect(url_for("login"))

    scenarios = get_scenarios()
    result = None
    data = DEFAULTS.copy()
    birth_tmp = parse_date(data["birth_date"], DEFAULTS["birth_date"])
    data["pension_date"] = ordinary_pension_date(birth_tmp).isoformat()
    data["id"] = None

    sid = request.args.get("id")
    new_scenario = request.args.get("new")
    if not sid and not new_scenario:
        # Letztes Szenario automatisch laden
        last = next(iter(get_scenarios()), None)
        if last:
            sid = str(last["id"])
    if sid:
        row = get_scenario(sid)
        if row:
            data = normalize_row(row)
            result = calculate(data)

    if request.method == "POST":
        data = form_data()
        action = request.form.get("action")

        if action == "save":
            saved_id = save_scenario(data)
            return redirect(url_for("home", id=saved_id, saved=1))

        result = calculate(data)

    return render_template_string(
        HTML,
        data=data,
        result=result,
        scenarios=scenarios,
        username="",
        input_value=input_value,
        percent_value=percent_value,
        percent2_value=percent2_value,
        format_date_ch=format_date_ch,
        is_admin=is_admin()
    )





@app.route("/duplicate/<int:sid>")
def duplicate(sid):
    if not require_login():
        return redirect(url_for("login"))
    row = get_scenario(sid)
    if not row:
        return redirect(url_for("home"))
    data = normalize_row(row)
    data["name"] = data["name"] + " (Kopie)"
    data["id"] = None
    new_id = save_scenario(data)
    return redirect(url_for("home", id=new_id))


@app.route("/rename/<int:sid>", methods=["POST"])
def rename(sid):
    if not require_login():
        return redirect(url_for("login"))
    name = request.form.get("name", "").strip()
    if name:
        conn = db()
        conn.execute(
            "UPDATE scenarios SET name=? WHERE id=? AND user_id=?",
            (name, sid, current_user_id())
        )
        conn.commit()
        conn.close()
    return redirect(url_for("home", id=sid))


@app.route("/delete/<int:sid>")
def delete(sid):
    if not require_login():
        return redirect(url_for("login"))

    conn = db()
    conn.execute("DELETE FROM scenarios WHERE id=? AND user_id=?", (sid, current_user_id()))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))

@app.route('/favicon.png')
def favicon_png():
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return send_from_directory(base_dir, 'favicon.png', mimetype='image/png')

if __name__ == "__main__":
    init_db()

if __name__ == '__main__':
    import threading
    import webview

    def run_flask():
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    import time
    time.sleep(1.5)

    window = webview.create_window(
        "Schweizer Pension Tool",
        "http://127.0.0.1:5000",
        width=1280,
        height=900,
        resizable=True
    )
    webview.start()
