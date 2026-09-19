#!/usr/bin/env python3
"""
LEXWAYS — pipeline automatique : Claude -> (Higgsfield) -> Zapier -> Instagram

Chaîne :
  1. On lit le carrousel du jour dans content_bank.json (contenu PRÉ-VÉRIFIÉ).
  2. On compose chaque slide (mascotte + objet 3D + texte exact) à partir de assets/.
     (Higgsfield n'est PAS appelé au quotidien : la bibliothèque est réutilisable.
      Le hook higgsfield_generate() est fourni pour enrichir la bibliothèque à la demande.)
  3. On upload les PNG sur Cloudinary (upload preset non signé) -> URLs publiques.
  4. On envoie l'e-mail « CARROUSEL LEXWAYS DU JOUR » (URLs + légende) qui déclenche
     ton Zap Gmail -> Instagram (publication du carrousel).

⚠️ À exécuter là où il y a un accès internet (GitHub Actions, ou une machine).
   Ce script NE tourne PAS dans le sandbox cloud de Claude (réseau bloqué).

Secrets attendus (variables d'environnement) :
  CLOUDINARY_CLOUD          ex: hyvzd1hy
  CLOUDINARY_UPLOAD_PRESET  ex: lexways_auto  (preset NON signé)
  GMAIL_USER                elmahjoubinazik@gmail.com
  GMAIL_APP_PASSWORD        mot de passe d'application Gmail (16 caractères)
  MAIL_TO                   elmahjoubinazik@gmail.com
  HIGGSFIELD_API_KEY        (optionnel — seulement pour higgsfield_generate)
"""
import os, json, base64, smtplib, datetime, pathlib, sys
from email.mime.text import MIMEText

HERE = pathlib.Path(__file__).parent
ASSETS = HERE  # les visuels sont à la racine du dépôt (upload iPad simplifié)
INK="#0E0E12"; IVO="#F5F4F1"; IND="#3D3AE8"; INDL="#5B57F2"; GREY="#9A9AA2"; MUT="#8E8E96"
MASK="-webkit-mask-image:radial-gradient(ellipse 62% 72% at 50% 42%,#000 55%,transparent 82%);mask-image:radial-gradient(ellipse 62% 72% at 50% 42%,#000 55%,transparent 82%);"

def amap():
    return json.loads((HERE/"assets_map.json").read_text())
def b64(name):
    p = ASSETS / amap()[name]
    return "data:image/png;base64,"+base64.b64encode(p.read_bytes()).decode()
def photo_uri():
    p = ASSETS / amap().get("photo","nazik.jpg")
    return "data:image/jpeg;base64,"+base64.b64encode(p.read_bytes()).decode()

# ---------- rendu des slides (HTML -> PNG via Playwright) ----------
def logo(): return f'<div style="font-family:Arial;font-weight:900;font-size:40px;letter-spacing:1px;"><span style="color:{INDL}">L</span><span style="color:{IVO}">EXWAYS</span></div>'
def frame(inner): return f'<div style="width:1080px;height:1350px;box-sizing:border-box;background:radial-gradient(120% 90% at 75% 12%,#17171F,{INK} 62%);color:{IVO};font-family:Arial;padding:96px;position:relative;overflow:hidden;">{inner}</div>'
def head(k): return f'<div style="display:flex;justify-content:space-between;align-items:center;">{logo()}<div style="font-size:24px;letter-spacing:3px;color:{MUT};font-weight:700;">{k}</div></div>'
def obj(src): return f'<img src="{src}" style="position:absolute;top:150px;right:66px;width:360px;height:360px;object-fit:contain;">'

def render_cover(e):
    return frame(f'''<img src="{b64(e["cover"]["mascotte"])}" style="position:absolute;right:-70px;bottom:-30px;width:760px;height:760px;object-fit:contain;{MASK}">
      <div style="position:absolute;top:96px;left:96px;right:96px;">{head(e["kicker"])}</div>
      <div style="position:absolute;top:330px;left:96px;max-width:560px;">
        <div style="font-size:44px;line-height:1.25;color:#C9C9D1;font-weight:500;margin-bottom:26px;">{e["cover"]["quote"]}</div>
        <div style="font-weight:900;font-size:80px;line-height:1.0;letter-spacing:-2px;">{e["cover"]["title_html"]}</div>
      </div>
      <div style="position:absolute;bottom:96px;left:96px;color:{INDL};font-weight:800;font-size:32px;">Faites glisser →</div>''')

def render_story(e):
    s=e["story"]
    return frame(f'''{obj(b64(s["object"]))}{head("L'HISTOIRE")}
      <div style="position:absolute;top:600px;left:96px;max-width:820px;">
        <div style="font-weight:900;font-size:84px;line-height:1.0;letter-spacing:-1px;margin-bottom:28px;">{s["name"]}</div>
        <div style="font-size:42px;line-height:1.4;color:{GREY};font-weight:500;margin-bottom:28px;">{s["text"]}</div>
        <div style="display:inline-block;background:{IND};color:#fff;font-size:40px;line-height:1.3;font-weight:600;padding:20px 26px;">{s["quote"]}</div>
      </div>
      <div style="position:absolute;bottom:96px;left:96px;font-size:24px;letter-spacing:2px;color:{MUT};font-weight:700;">MISE EN SITUATION</div>''')

def render_question(q):
    punch=f'<div style="font-weight:900;font-size:120px;line-height:0.9;color:{INDL};letter-spacing:-2px;margin-bottom:24px;">{q["punch"]}</div>' if q.get("punch") else ""
    return frame(f'''{obj(b64(q["object"]))}{head(q["kicker"])}
      <div style="position:absolute;top:560px;left:96px;max-width:840px;">
        <div style="display:inline-block;background:{IND};color:#fff;font-weight:900;font-size:60px;padding:10px 30px;border-radius:60px;margin-bottom:24px;">{q["num"]}</div>
        <div style="font-weight:800;font-size:56px;line-height:1.08;margin-bottom:22px;">{q["title"]}</div>
        {punch}
        <div style="display:inline-block;background:#1A1A22;border:1px solid #2A2A32;color:{IVO};font-weight:700;font-size:36px;line-height:1.32;padding:20px 26px;max-width:840px;">{q["box"]}</div>
      </div>
      <div style="position:absolute;bottom:96px;left:96px;"><span style="background:{IND};color:#fff;font-weight:800;font-size:26px;letter-spacing:2px;padding:8px 16px;border-radius:6px;">{q["pager"]}</span></div>''')

def render_takeaway(e):
    pts="".join(f'<div style="display:flex;gap:24px;"><div style="color:{INDL};font-weight:900;font-size:38px;">{i:02d}</div><div style="font-size:40px;line-height:1.32;font-weight:500;color:#E4E2DC;">{t}</div></div>' for i,t in enumerate(e["takeaway"],1))
    return frame(f'''<img src="{b64("shield")}" style="position:absolute;top:150px;right:78px;width:320px;height:320px;object-fit:contain;">{head("À RETENIR")}
      <div style="position:absolute;top:560px;left:96px;max-width:800px;">
        <div style="font-weight:900;font-size:62px;line-height:1.02;letter-spacing:-1px;margin-bottom:40px;">Ce qu'il faut retenir</div>
        <div style="display:flex;flex-direction:column;gap:30px;">{pts}</div>
      </div>
      <div style="position:absolute;bottom:96px;left:96px;font-size:24px;letter-spacing:2px;color:{MUT};font-weight:700;">SYNTHÈSE · CAS FICTIF</div>''')

def render_contact(e):
    return frame(f'''{head("CONTACT")}
      <div style="position:absolute;top:230px;left:96px;display:flex;gap:44px;align-items:center;">
        <img src="{photo_uri()}" style="width:320px;height:420px;object-fit:cover;border-radius:22px;">
        <div><div style="font-size:34px;color:#C9C9D1;font-weight:500;margin-bottom:10px;">Parlons de votre situation.</div>
        <div style="font-weight:900;font-size:52px;line-height:1.02;">Nazik<br>EL MAHJOUBI</div>
        <div style="font-size:27px;color:{MUT};font-weight:600;line-height:1.3;margin-top:10px;">Avocate — Barreaux de<br>Genève &amp; Luxembourg</div></div>
      </div>
      <div style="position:absolute;top:760px;left:96px;display:flex;flex-direction:column;gap:20px;">
        <div style="font-size:34px;font-weight:700;"><span style="color:{INDL};">Rendez-vous ·</span> calendly.com/lexways</div>
        <div style="font-size:34px;font-weight:700;"><span style="color:#25D366;">WhatsApp ·</span> +41 78 213 86 08</div>
        <div style="font-size:34px;font-weight:700;"><span style="color:{INDL};">Web ·</span> www.lexways.ch · legaly.ch</div>
      </div>
      <div style="position:absolute;bottom:96px;left:96px;font-size:21px;color:#6E6E76;">Information générale — ne constitue pas un conseil juridique.</div>''')

def build_slides(e, outdir):
    from playwright.sync_api import sync_playwright
    outdir.mkdir(exist_ok=True)
    htmls=[("1_cover",render_cover(e)),("2_story",render_story(e))]
    for i,q in enumerate(e["questions"],1):
        htmls.append((f"{i+2}_q{i}",render_question(q)))
    htmls.append((f"{len(e['questions'])+3}_retenir",render_takeaway(e)))
    htmls.append((f"{len(e['questions'])+4}_contact",render_contact(e)))
    paths=[]
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={"width":1080,"height":1350},device_scale_factor=2)
        for name,html in htmls:
            pg.set_content(f"<!doctype html><html><head><meta charset='utf-8'></head><body style='margin:0'>{html}</body></html>")
            pg.wait_for_timeout(450); fp=str(outdir/f"{name}.png")
            pg.screenshot(path=fp,clip={"x":0,"y":0,"width":1080,"height":1350}); paths.append(fp)
        b.close()
    return paths

# ---------- upload Cloudinary ----------
def upload_cloudinary(paths):
    import requests
    cloud=os.environ["CLOUDINARY_CLOUD"]; preset=os.environ["CLOUDINARY_UPLOAD_PRESET"]
    urls=[]
    for fp in paths:
        with open(fp,"rb") as f:
            r=requests.post(f"https://api.cloudinary.com/v1_1/{cloud}/image/upload",
                            data={"upload_preset":preset}, files={"file":f}, timeout=120)
        r.raise_for_status(); urls.append(r.json()["secure_url"])
    return urls

# ---------- e-mail -> Zap -> Instagram ----------
def send_email(urls, legende):
    body="\n".join(urls)+"\n---LEGENDE---\n"+legende
    msg=MIMEText(body,"plain","utf-8")
    msg["Subject"]="CARROUSEL LEXWAYS DU JOUR"
    msg["From"]=os.environ["GMAIL_USER"]; msg["To"]=os.environ.get("MAIL_TO",os.environ["GMAIL_USER"])
    with smtplib.SMTP_SSL("smtp.gmail.com",465) as s:
        s.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"])
        s.send_message(msg)

# ---------- Higgsfield (OPTIONNEL, hors boucle quotidienne) ----------
def higgsfield_generate(prompt, out_png):
    """Génère UN visuel via l'API Higgsfield pour enrichir la bibliothèque.
    Voir docs.higgsfield.ai. Nécessite HIGGSFIELD_API_KEY. Non utilisé au quotidien."""
    import requests, time
    key=os.environ["HIGGSFIELD_API_KEY"]
    # NB: adapter l'endpoint/paramètres au modèle choisi (Soul 2) selon docs.higgsfield.ai
    raise NotImplementedError("Brancher l'endpoint Higgsfield ici si besoin de génération quotidienne.")

# ---------- sélection du carrousel du jour ----------
def pick_entry(bank, cfg):
    wd=str(datetime.date.today().weekday())  # lundi=0 ... dimanche=6
    eid=cfg.get("schedule",{}).get(wd) or cfg.get("default")
    for e in bank:
        if e["id"]==eid: return e
    return bank[0]

def main():
    bank=json.loads((HERE/"content_bank.json").read_text())
    cfg=json.loads((HERE/"config.json").read_text())
    e=pick_entry(bank,cfg)
    print("Carrousel du jour:",e["id"])
    out=HERE/"out"; paths=build_slides(e,out); print("rendu",len(paths),"slides")
    urls=upload_cloudinary(paths); print("upload OK",len(urls),"URLs")
    send_email(urls, e["legende"]); print("e-mail envoyé -> le Zap publie sur Instagram.")

if __name__=="__main__":
    main()
